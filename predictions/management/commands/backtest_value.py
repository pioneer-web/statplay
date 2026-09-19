import time
from collections import defaultdict

from django.core.management.base import BaseCommand

from predictions.stat_engine import evaluate_event
from sports.models import Event, TeamMatchStats
from sports.providers.sofascore import SofaScoreProvider
from sports.services.competition_filter import is_professional_competition


SUPPORTED_LINES = {
    9: {
        1.5: "goals_over_1_5",
        2.5: "goals_over_2_5",
    },
    20: {
        2.5: "cards_over_2_5",
        3.5: "cards_over_3_5",
        4.5: "cards_over_4_5",
        5.5: "cards_over_5_5",
    },
    21: {
        7.5: "corners_over_7_5",
        8.5: "corners_over_8_5",
        9.5: "corners_over_9_5",
        10.5: "corners_over_10_5",
    },
}


def decimal_odd(choice):
    value = choice.get("decimalValue")

    if value is not None:
        try:
            value = float(value)

            if 1.01 <= value <= 100:
                return value
        except Exception:
            pass

    fraction = choice.get("fractionalValue")

    if not fraction:
        return None

    try:
        num, den = str(fraction).split("/")
        den = float(den)

        if den == 0:
            return None

        result = 1 + float(num) / den

        if 1.01 <= result <= 100:
            return result

    except Exception:
        return None

    return None


def extract_offers(payload):
    offers = {}

    for market in payload.get("markets", []):
        if market.get("isLive") is True:
            continue

        if market.get("suspended") is True:
            continue

        period = str(
            market.get("marketPeriod") or ""
        ).lower()

        if period and period not in (
            "full-time",
            "full time",
        ):
            continue

        market_id = market.get("marketId")

        #
        # 1X2
        #
        if market_id == 1:
            mapping = {
                "1": "home_win",
                "x": "draw",
                "2": "away_win",
            }

            for choice in market.get("choices", []):
                code = mapping.get(
                    str(
                        choice.get("name", "")
                    ).lower()
                )

                odd = decimal_odd(choice)

                if code and odd:
                    offers[code] = odd

            continue

        #
        # BTTS
        #
        if market_id == 5:
            for choice in market.get("choices", []):
                if (
                    str(
                        choice.get("name", "")
                    ).lower()
                    != "yes"
                ):
                    continue

                odd = decimal_odd(choice)

                if odd:
                    offers["btts_yes"] = odd

            continue

        #
        # Gols / cartões / escanteios
        #
        if market_id not in SUPPORTED_LINES:
            continue

        try:
            line = float(
                market.get("choiceGroup")
            )
        except (TypeError, ValueError):
            continue

        code = SUPPORTED_LINES[
            market_id
        ].get(line)

        if not code:
            continue

        for choice in market.get("choices", []):
            if (
                str(
                    choice.get("name", "")
                ).lower()
                != "over"
            ):
                continue

            odd = decimal_odd(choice)

            if odd:
                offers[code] = odd

    return offers


def result_for(event, code):
    if (
        event.home_score is None
        or event.away_score is None
    ):
        return None

    home = event.home_score
    away = event.away_score

    if code == "home_win":
        return home > away

    if code == "draw":
        return home == away

    if code == "away_win":
        return away > home

    if code == "btts_yes":
        return home > 0 and away > 0

    if code == "goals_over_1_5":
        return home + away > 1.5

    if code == "goals_over_2_5":
        return home + away > 2.5

    stats = list(
        TeamMatchStats.objects.filter(
            event=event
        )
    )

    if len(stats) != 2:
        return None

    if code.startswith("corners_over_"):
        values = [
            item.corners
            for item in stats
        ]

    elif code.startswith("cards_over_"):
        values = [
            item.cards
            for item in stats
        ]

    else:
        return None

    if any(
        value is None
        for value in values
    ):
        return None

    line = float(
        code.split("_over_")[1]
        .replace("_", ".")
    )

    return sum(values) > line


def new_bucket():
    return {
        "bets": 0,
        "wins": 0,
        "stake": 0.0,
        "profit": 0.0,
        "edge_sum": 0.0,
        "odd_sum": 0.0,
        "prob_sum": 0.0,
    }


def add_result(bucket, win, odd, probability, edge):
    bucket["bets"] += 1
    bucket["stake"] += 1
    bucket["edge_sum"] += edge
    bucket["odd_sum"] += odd
    bucket["prob_sum"] += probability

    if win:
        bucket["wins"] += 1
        bucket["profit"] += odd - 1
    else:
        bucket["profit"] -= 1


def print_bucket(stdout, name, data):
    if not data["bets"]:
        return

    hit = (
        data["wins"]
        / data["bets"]
        * 100
    )

    roi = (
        data["profit"]
        / data["stake"]
        * 100
    )

    avg_edge = (
        data["edge_sum"]
        / data["bets"]
    )

    avg_odd = (
        data["odd_sum"]
        / data["bets"]
    )

    avg_prob = (
        data["prob_sum"]
        / data["bets"]
    )

    stdout.write(
        f"{name}: "
        f"{data['wins']}/{data['bets']} "
        f"| acerto={hit:.1f}% "
        f"| odd média={avg_odd:.2f} "
        f"| P média={avg_prob:.1f}% "
        f"| edge médio={avg_edge:+.1f}pp "
        f"| lucro={data['profit']:+.2f}u "
        f"| ROI={roi:+.1f}%"
    )


class Command(BaseCommand):
    help = "Backtest de probabilidade + odds + edge"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=1500,
        )

        parser.add_argument(
            "--min-prob",
            type=float,
            default=50,
        )

        parser.add_argument(
            "--delay",
            type=float,
            default=0.10,
        )

    def handle(self, *args, **options):
        provider = SofaScoreProvider()

        events = (
            Event.objects
            .filter(status="finished")
            .exclude(external_id="")
            .select_related(
                "home_team",
                "away_team",
                "competition",
            )
            .order_by("-starts_at")
        )

        thresholds = {
            "edge >= 0pp": new_bucket(),
            "edge >= 2pp": new_bucket(),
            "edge >= 5pp": new_bucket(),
            "edge >= 10pp": new_bucket(),
        }

        market_stats = defaultdict(
            new_bucket
        )

        tested = 0
        with_model = 0
        with_odds = 0
        matched = 0
        errors = 0

        for event in events:
            if tested >= options["limit"]:
                break

            if not is_professional_competition(
                event.competition.name
            ):
                continue

            tested += 1

            model = evaluate_event(
                event,
                sample=10,
                min_matches=5,
            )

            if not model:
                continue

            with_model += 1

            model_map = {
                item["code"]: item
                for item in model["markets"]
            }

            try:
                payload = (
                    provider.get_odds(
                        event.external_id
                    )
                    or {}
                )
            except Exception:
                errors += 1
                continue

            offers = extract_offers(
                payload
            )

            if not offers:
                continue

            with_odds += 1

            for code, odd in offers.items():
                if code not in model_map:
                    continue

                probability = float(
                    model_map[code][
                        "probability"
                    ]
                )

                if (
                    probability
                    < options["min_prob"]
                ):
                    continue

                actual = result_for(
                    event,
                    code,
                )

                if actual is None:
                    continue

                implied = 100 / odd

                edge = (
                    probability
                    - implied
                )

                matched += 1

                add_result(
                    market_stats[code],
                    actual,
                    odd,
                    probability,
                    edge,
                )

                if edge >= 0:
                    add_result(
                        thresholds[
                            "edge >= 0pp"
                        ],
                        actual,
                        odd,
                        probability,
                        edge,
                    )

                if edge >= 2:
                    add_result(
                        thresholds[
                            "edge >= 2pp"
                        ],
                        actual,
                        odd,
                        probability,
                        edge,
                    )

                if edge >= 5:
                    add_result(
                        thresholds[
                            "edge >= 5pp"
                        ],
                        actual,
                        odd,
                        probability,
                        edge,
                    )

                if edge >= 10:
                    add_result(
                        thresholds[
                            "edge >= 10pp"
                        ],
                        actual,
                        odd,
                        probability,
                        edge,
                    )

            time.sleep(
                options["delay"]
            )

        self.stdout.write(
            "\n=== STATPLAY VALUE BACKTEST ==="
        )

        self.stdout.write(
            f"Jogos testados: {tested}"
        )

        self.stdout.write(
            f"Jogos com modelo: {with_model}"
        )

        self.stdout.write(
            f"Jogos com odds históricas: {with_odds}"
        )

        self.stdout.write(
            f"Previsões casadas: {matched}"
        )

        self.stdout.write(
            f"Erros de coleta: {errors}"
        )

        self.stdout.write(
            "\n=== POR EDGE ==="
        )

        for name, data in thresholds.items():
            print_bucket(
                self.stdout,
                name,
                data,
            )

        self.stdout.write(
            "\n=== POR MERCADO ==="
        )

        ordered = sorted(
            market_stats.items(),
            key=lambda item: (
                item[1]["bets"]
            ),
            reverse=True,
        )

        for code, data in ordered:
            if data["bets"] < 10:
                continue

            print_bucket(
                self.stdout,
                code,
                data,
            )

        self.stdout.write(
            "\nOBS: odds históricas retornadas "
            "pelo SofaScore; ainda não tratamos "
            "isso como prova de rentabilidade "
            "até termos snapshots próprios "
            "pré-jogo."
        )
