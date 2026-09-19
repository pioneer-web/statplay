import os
import unicodedata
from datetime import datetime, timedelta
from difflib import SequenceMatcher

import requests

from django.utils import timezone

from sports.models import Event
from odds.models import Bookmaker, Market, OddSnapshot


BASE_URL = "https://api.the-odds-api.com/v4"


MARKET_NAMES = {
    "h2h": ("Resultado da partida", "result"),
    "totals": ("Total de gols", "goals"),
    "btts": ("Ambas marcam", "goals"),

    "alternate_totals_corners": (
        "Total de escanteios",
        "corners",
    ),

    "alternate_team_totals_corners": (
        "Escanteios por equipe",
        "corners",
    ),

    "alternate_spreads_corners": (
        "Handicap de escanteios",
        "corners",
    ),

    "corners_1x2": (
        "Mais escanteios",
        "corners",
    ),

    "alternate_totals_cards": (
        "Total de cartões",
        "cards",
    ),
}


def normalize(value):

    value = unicodedata.normalize(
        "NFKD",
        value or "",
    )

    value = "".join(
        char
        for char in value
        if not unicodedata.combining(char)
    )

    return value.lower().replace("-", " ").strip()


class TheOddsApiProvider:

    def __init__(self):

        self.api_key = os.getenv("THE_ODDS_API_KEY", "")

        self.region = os.getenv(
            "THE_ODDS_API_REGION",
            "eu",
        )

        raw_sports = os.getenv(
            "THE_ODDS_API_SPORTS",
            "",
        )

        self.sports = [
            value.strip()
            for value in raw_sports.split(",")
            if value.strip()
        ]

    @property
    def configured(self):

        return bool(
            self.api_key
            and self.sports
        )

    def _get(self, url, params=None):

        params = params or {}

        params["apiKey"] = self.api_key

        response = requests.get(
            url,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()

    def _find_local_event(
        self,
        home,
        away,
        commence_time,
    ):

        start = datetime.fromisoformat(
            commence_time.replace("Z", "+00:00")
        )

        window_start = start - timedelta(hours=8)
        window_end = start + timedelta(hours=8)

        candidates = Event.objects.select_related(
            "home_team",
            "away_team",
        ).filter(
            starts_at__gte=window_start,
            starts_at__lte=window_end,
        )

        expected_home = normalize(home)
        expected_away = normalize(away)

        best_event = None
        best_score = 0

        for event in candidates:

            home_score = SequenceMatcher(
                None,
                expected_home,
                normalize(event.home_team.name),
            ).ratio()

            away_score = SequenceMatcher(
                None,
                expected_away,
                normalize(event.away_team.name),
            ).ratio()

            score = (home_score + away_score) / 2

            if score > best_score:
                best_score = score
                best_event = event

        if best_score >= 0.65:
            return best_event

        return None

    def sync(self):

        if not self.configured:

            return {
                "status": "not_configured",
                "message": "Configure THE_ODDS_API_KEY e THE_ODDS_API_SPORTS.",
            }

        snapshots = 0
        matched_events = 0
        unmatched_events = 0

        market_keys = ",".join(
            MARKET_NAMES.keys()
        )

        for sport_key in self.sports:

            events = self._get(
                f"{BASE_URL}/sports/{sport_key}/events",
            )

            for api_event in events:

                local_event = self._find_local_event(
                    api_event["home_team"],
                    api_event["away_team"],
                    api_event["commence_time"],
                )

                if not local_event:
                    unmatched_events += 1
                    continue

                matched_events += 1

                try:
                    odds_event = self._get(
                        (
                            f"{BASE_URL}/sports/"
                            f"{sport_key}/events/"
                            f"{api_event['id']}/odds"
                        ),
                        {
                            "regions": self.region,
                            "markets": market_keys,
                            "oddsFormat": "decimal",
                        },
                    )

                except requests.HTTPError as exc:
                    print(
                        f"Odds indisponíveis para "
                        f"{api_event['id']}: {exc}"
                    )
                    continue

                for bookmaker_data in odds_event.get(
                    "bookmakers",
                    [],
                ):

                    bookmaker, _ = Bookmaker.objects.update_or_create(
                        slug=bookmaker_data["key"],
                        defaults={
                            "name": bookmaker_data["title"],
                            "active": True,
                        },
                    )

                    for market_data in bookmaker_data.get(
                        "markets",
                        [],
                    ):

                        market_key = market_data["key"]

                        market_name, category = MARKET_NAMES.get(
                            market_key,
                            (
                                market_key,
                                "other",
                            ),
                        )

                        market, _ = Market.objects.update_or_create(
                            code=market_key,
                            defaults={
                                "name": market_name,
                                "category": category,
                            },
                        )

                        for outcome in market_data.get(
                            "outcomes",
                            [],
                        ):

                            point = outcome.get("point")

                            description = outcome.get(
                                "description"
                            )

                            selection = outcome.get(
                                "name",
                                "",
                            )

                            if description:
                                selection = (
                                    f"{description} - {selection}"
                                )

                            OddSnapshot.objects.create(
                                event=local_event,
                                bookmaker=bookmaker,
                                market=market,
                                selection=selection[:120],
                                line=point,
                                odd=outcome["price"],
                            )

                            snapshots += 1

        return {
            "status": "ok",
            "matched_events": matched_events,
            "unmatched_events": unmatched_events,
            "snapshots": snapshots,
        }
