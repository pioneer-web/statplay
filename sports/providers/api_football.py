import os
from datetime import timedelta

import requests
from django.utils import timezone

from sports.models import Sport, Competition, Team, Event


BASE_URL = "https://v3.football.api-sports.io"


class ApiFootballProvider:

    def __init__(self):
        self.api_key = os.getenv("API_FOOTBALL_KEY", "")
        self.season = int(os.getenv("API_FOOTBALL_SEASON", "2026"))

        raw_leagues = os.getenv("API_FOOTBALL_LEAGUES", "")
        self.leagues = [
            value.strip()
            for value in raw_leagues.split(",")
            if value.strip()
        ]

    @property
    def configured(self):
        return bool(self.api_key and self.leagues)

    def _get(self, endpoint, params=None):

        response = requests.get(
            f"{BASE_URL}/{endpoint}",
            headers={
                "x-apisports-key": self.api_key,
            },
            params=params or {},
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        errors = data.get("errors")

        if errors:
            raise RuntimeError(
                f"API-Football retornou erro: {errors}"
            )

        return data.get("response", [])

    def sync_upcoming(self, days=7):

        if not self.configured:
            return {
                "status": "not_configured",
                "message": "Configure API_FOOTBALL_KEY e API_FOOTBALL_LEAGUES.",
            }

        sport, _ = Sport.objects.get_or_create(
            slug="football",
            defaults={"name": "Futebol"},
        )

        date_from = timezone.localdate()

        date_to = date_from + timedelta(days=days)

        created = 0
        updated = 0

        for league_id in self.leagues:

            fixtures = self._get(
                "fixtures",
                {
                    "league": league_id,
                    "season": self.season,
                    "from": date_from.isoformat(),
                    "to": date_to.isoformat(),
                    "timezone": "America/Recife",
                },
            )

            for item in fixtures:

                fixture = item["fixture"]
                league = item["league"]
                teams = item["teams"]

                competition, _ = Competition.objects.update_or_create(
                    sport=sport,
                    external_id=str(league["id"]),
                    defaults={
                        "name": league["name"],
                        "country": league.get("country") or "",
                    },
                )

                home, _ = Team.objects.update_or_create(
                    sport=sport,
                    external_id=str(teams["home"]["id"]),
                    defaults={
                        "name": teams["home"]["name"],
                    },
                )

                away, _ = Team.objects.update_or_create(
                    sport=sport,
                    external_id=str(teams["away"]["id"]),
                    defaults={
                        "name": teams["away"]["name"],
                    },
                )

                api_status = fixture["status"]["short"]

                if api_status in {"FT", "AET", "PEN"}:
                    status = "finished"

                elif api_status in {"1H", "HT", "2H", "ET", "BT", "P"}:
                    status = "live"

                elif api_status in {"CANC", "ABD", "AWD", "WO"}:
                    status = "cancelled"

                else:
                    status = "scheduled"

                event, event_created = Event.objects.update_or_create(
                    external_id=str(fixture["id"]),
                    defaults={
                        "competition": competition,
                        "home_team": home,
                        "away_team": away,
                        "starts_at": fixture["date"],
                        "status": status,
                        "home_score": item.get("goals", {}).get("home"),
                        "away_score": item.get("goals", {}).get("away"),
                    },
                )

                if event_created:
                    created += 1
                else:
                    updated += 1

        return {
            "status": "ok",
            "created": created,
            "updated": updated,
        }
