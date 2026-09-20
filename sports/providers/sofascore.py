import os
from datetime import datetime, timedelta, timezone as dt_timezone

from curl_cffi import requests
from django.utils import timezone

from sports.models import Sport, Competition, Team, Event
from sports.services.competition_scope import is_target_competition


BASE_URL = "https://api.sofascore.com/api/v1"
WEB_BASE_URL = "https://www.sofascore.com/api/v1"


class SofaScoreProvider:
    def __init__(self):
        raw_countries = os.getenv(
            "SOFASCORE_COUNTRIES",
            "Brazil,England,Spain,Italy,Germany,France,Portugal"
        )

        self.countries = {
            value.strip().lower()
            for value in raw_countries.split(",")
            if value.strip()
        }

        self.session = requests.Session(
            impersonate="chrome"
        )

        self.headers = {
            "Origin": "https://www.sofascore.com",
            "Referer": "https://www.sofascore.com/",
        }

    def _get(self, path):
        response = self.session.get(
            f"{BASE_URL}/{path}",
            headers=self.headers,
            timeout=20,
        )

        if response.status_code == 404:
            return None

        response.raise_for_status()
        return response.json()

    def _get_web(self, path):
        response = self.session.get(
            f"{WEB_BASE_URL}/{path}",
            headers=self.headers,
            timeout=20,
        )

        if response.status_code == 404:
            return None

        response.raise_for_status()
        return response.json()

    def _get_tournament_ids(self, date):
        tournament_ids = set()
        page = 1

        while page <= 40:
            data = self._get(
                f"sport/football/"
                f"scheduled-tournaments/"
                f"{date}/page/{page}"
            )

            if not data:
                break

            scheduled = data.get(
                "scheduled",
                [],
            )

            if not scheduled:
                break

            for item in scheduled:
                tournament = item.get(
                    "tournament",
                    {},
                )

                unique = tournament.get(
                    "uniqueTournament",
                    {},
                )

                category = tournament.get(
                    "category",
                    {},
                )

                name = (
                    unique.get("name")
                    or tournament.get("name")
                    or ""
                )

                country = (
                    category.get("name")
                    or ""
                )

                if not is_target_competition(
                    name,
                    country,
                ):
                    continue

                tournament_id = (
                    unique.get("id")
                )

                if tournament_id:
                    tournament_ids.add(
                        int(tournament_id)
                    )

            if not data.get(
                "hasNextPage"
            ):
                break

            page += 1

        return sorted(
            tournament_ids
        )

    def _get_events_for_tournament(
        self,
        tournament_id,
        date,
    ):
        data = self._get(
            f"unique-tournament/"
            f"{tournament_id}/"
            f"scheduled-events/{date}"
        )

        if not data:
            return []

        return data.get("events", [])

    def _country_allowed(self, item):
        tournament = item.get("tournament", {})
        category = tournament.get("category", {})

        country = (
            category.get("name")
            or category.get("country", {}).get("name")
            or ""
        )

        if not self.countries:
            return True

        return country.lower() in self.countries

    def _status(self, item):
        status_type = (
            item.get("status", {})
            .get("type", "")
        )

        return {
            "notstarted": "scheduled",
            "inprogress": "live",
            "finished": "finished",
            "canceled": "cancelled",
            "cancelled": "cancelled",
        }.get(
            status_type,
            "scheduled",
        )

    def _save_event(self, item, sport):
        tournament = item.get("tournament", {})
        unique_tournament = tournament.get(
            "uniqueTournament",
            {}
        )

        category = tournament.get(
            "category",
            {}
        )

        home_data = item.get("homeTeam", {})
        away_data = item.get("awayTeam", {})

        if not home_data or not away_data:
            return None, False

        tournament_id = (
            unique_tournament.get("id")
            or tournament.get("id")
        )

        tournament_name = (
            unique_tournament.get("name")
            or tournament.get("name")
            or "Competição"
        )

        country = category.get("name", "")

        competition_external_id = str(
            tournament_id or ""
        )

        if competition_external_id:
            competition = (
                Competition.objects
                .filter(
                    sport=sport,
                    external_id=
                        competition_external_id,
                )
                .order_by("id")
                .first()
            )

            if competition:
                changed = False

                if (
                    competition.name
                    != tournament_name
                ):
                    competition.name = (
                        tournament_name
                    )
                    changed = True

                if (
                    competition.country
                    != country
                ):
                    competition.country = (
                        country
                    )
                    changed = True

                if changed:
                    competition.save(
                        update_fields=[
                            "name",
                            "country",
                        ]
                    )

            else:
                competition = (
                    Competition.objects
                    .create(
                        sport=sport,
                        external_id=
                            competition_external_id,
                        name=
                            tournament_name,
                        country=
                            country,
                    )
                )

        else:
            competition = (
                Competition.objects
                .filter(
                    sport=sport,
                    name=tournament_name,
                    country=country,
                )
                .order_by("id")
                .first()
            )

            if not competition:
                competition = (
                    Competition.objects
                    .create(
                        sport=sport,
                        name=
                            tournament_name,
                        country=country,
                        external_id="",
                    )
                )

        home, _ = Team.objects.update_or_create(
            sport=sport,
            external_id=str(
                home_data.get("id", "")
            ),
            defaults={
                "name": home_data.get(
                    "name",
                    "Mandante",
                )
            },
        )

        away, _ = Team.objects.update_or_create(
            sport=sport,
            external_id=str(
                away_data.get("id", "")
            ),
            defaults={
                "name": away_data.get(
                    "name",
                    "Visitante",
                )
            },
        )

        timestamp = item.get(
            "startTimestamp"
        )

        if not timestamp:
            return None, False

        starts_at = datetime.fromtimestamp(
            timestamp,
            tz=dt_timezone.utc,
        )

        home_score = item.get(
            "homeScore",
            {}
        ).get("current")

        away_score = item.get(
            "awayScore",
            {}
        ).get("current")

        event, created = (
            Event.objects.update_or_create(
                external_id=str(item["id"]),
                defaults={
                    "competition": competition,
                    "home_team": home,
                    "away_team": away,
                    "starts_at": starts_at,
                    "status": self._status(item),
                    "home_score": home_score,
                    "away_score": away_score,
                },
            )
        )

        return event, created

    def sync_date(self, date):
        sport, _ = Sport.objects.get_or_create(
            slug="football",
            defaults={"name": "Futebol"},
        )

        tournament_ids = (
            self._get_tournament_ids(date)
        )

        created = 0
        updated = 0
        ignored = 0
        events_found = 0

        seen_events = set()

        for tournament_id in tournament_ids:
            events = (
                self._get_events_for_tournament(
                    tournament_id,
                    date,
                )
            )

            for item in events:
                event_id = item.get("id")

                if not event_id:
                    continue

                if event_id in seen_events:
                    continue

                seen_events.add(event_id)
                events_found += 1

                _, was_created = (
                    self._save_event(
                        item,
                        sport,
                    )
                )

                if was_created:
                    created += 1
                else:
                    updated += 1

        return {
            "date": date,
            "tournaments": len(
                tournament_ids
            ),
            "events_found": events_found,
            "created": created,
            "updated": updated,
            "ignored": ignored,
        }

    def sync_upcoming(self, days=3):
        today = timezone.localdate()

        totals = {
            "status": "ok",
            "days": [],
            "created": 0,
            "updated": 0,
            "ignored": 0,
        }

        for offset in range(days + 1):
            day = today + timedelta(
                days=offset
            )

            result = self.sync_date(
                day.isoformat()
            )

            totals["days"].append(result)

            totals["created"] += (
                result["created"]
            )

            totals["updated"] += (
                result["updated"]
            )

            totals["ignored"] += (
                result["ignored"]
            )

        return totals

    def get_team_last_events(self, team_id, page=0):
        data = self._get_web(
            f"team/{team_id}/events/last/{page}"
        )

        if not data:
            return []

        return data.get("events", [])

    def get_statistics(self, event_id):
        """
        Estatísticas de uma partida:
        escanteios, chutes, posse, xG etc.
        """
        return self._get(
            f"event/{event_id}/statistics"
        )

    def get_odds(self, event_id):
        """
        Odds disponibilizadas pelo SofaScore
        quando existirem.
        """
        data = self._get(
            f"event/{event_id}/odds/1/all"
        )

        return data or {"markets": []}

    def get_lineups(self, event_id):
        return self._get(
            f"event/{event_id}/lineups"
        )

    def get_team_streaks(self, event_id):
        return self._get(
            f"event/{event_id}/team-streaks"
        )
