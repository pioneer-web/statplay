from collections import defaultdict

from django.core.management.base import BaseCommand

from predictions.stat_engine import evaluate_event
from sports.models import Event, TeamMatchStats
from sports.services.competition_filter import (
    is_professional_competition,
)


def actual_result(event, market):
    code = market["code"]

    if (
        event.home_score is None
        or event.away_score is None
    ):
        return None

    home_goals = event.home_score
    away_goals = event.away_score
    total_goals = home_goals + away_goals

    if code == "home_win":
        return home_goals > away_goals

    if code == "draw":
        return home_goals == away_goals

    if code == "away_win":
        return away_goals > home_goals

    if code == "goals_over_1_5":
        return total_goals > 1.5

    if code == "goals_over_2_5":
        return total_goals > 2.5

    if code == "btts_yes":
        return home_goals > 0 and away_goals > 0

    stats = list(
        TeamMatchStats.objects.filter(
            event=event
        )
    )

    if len(stats) != 2:
        return None

    if code.startswith("corners_over_"):
        values = [
            stat.corners
            for stat in stats
        ]

        if any(v is None for v in values):
            return None

        line = float(
            code
            .replace("corners_over_", "")
            .replace("_", ".")
        )

        return sum(values) > line

    if code.startswith("cards_over_"):
        values = [
            stat.cards
            for stat in stats
        ]

        if any(v is None for v in values):
            return None

        line = float(
            code
            .replace("cards_over_", "")
            .replace("_", ".")
        )

        return sum(values) > line

    return None


def probability_band(probability):
    if probability >= 90:
        return "90%+"

    if probability >= 80:
        return "80-89%"

    if probability >= 70:
        return "70-79%"

    if probability >= 60:
        return "60-69%"

    return "<60%"


class Command(BaseCommand):
    help = "Backtest histórico do motor StatPlay"

    def add_arguments(self, parser):
        parser.add_argument(
            "--min-prob",
            type=float,
            default=60,
        )

        parser.add_argument(
            "--limit",
            type=int,
            default=500,
        )

    def handle(self, *args, **options):
        events = (
            Event.objects
            .filter(status="finished")
            .exclude(external_id="")
            .select_related(
                "home_team",
                "away_team",
                "competition",
            )
            .order_by("starts_at")
        )

        buckets = defaultdict(
            lambda: {
                "total": 0,
                "wins": 0,
                "prob_sum": 0.0,
            }
        )

        markets = defaultdict(
            lambda: {
                "total": 0,
                "wins": 0,
                "prob_sum": 0.0,
            }
        )

        analysed_events = 0
        predictions = 0

        for event in events:
            if analysed_events >= options["limit"]:
                break

            if not is_professional_competition(
                event.competition.name
            ):
                continue

            result = evaluate_event(
                event,
                sample=10,
                min_matches=5,
            )

            if not result:
                continue

            analysed_events += 1

            for market in result["markets"]:
                probability = market["probability"]

                if probability < options["min_prob"]:
                    continue

                outcome = actual_result(
                    event,
                    market,
                )

                if outcome is None:
                    continue

                predictions += 1

                band = probability_band(
                    probability
                )

                buckets[band]["total"] += 1
                buckets[band]["prob_sum"] += probability

                markets[market["code"]]["total"] += 1
                markets[market["code"]]["prob_sum"] += probability

                if outcome:
                    buckets[band]["wins"] += 1
                    markets[market["code"]]["wins"] += 1

        self.stdout.write(
            "\n=== STATPLAY BACKTEST ==="
        )

        self.stdout.write(
            f"Jogos analisados: {analysed_events}"
        )

        self.stdout.write(
            f"Previsões avaliadas: {predictions}"
        )

        self.stdout.write(
            "\n=== CALIBRAÇÃO POR FAIXA ==="
        )

        for band in (
            "60-69%",
            "70-79%",
            "80-89%",
            "90%+",
        ):
            data = buckets[band]

            if not data["total"]:
                continue

            hit_rate = (
                data["wins"]
                / data["total"]
                * 100
            )

            avg_probability = (
                data["prob_sum"]
                / data["total"]
            )

            gap = hit_rate - avg_probability

            self.stdout.write(
                f"{band}: "
                f"{data['wins']}/{data['total']} "
                f"| acerto={hit_rate:.1f}% "
                f"| previsão média={avg_probability:.1f}% "
                f"| diferença={gap:+.1f}pp"
            )

        self.stdout.write(
            "\n=== POR MERCADO ==="
        )

        ordered = sorted(
            markets.items(),
            key=lambda item: item[1]["total"],
            reverse=True,
        )

        for code, data in ordered:
            if data["total"] < 3:
                continue

            hit_rate = (
                data["wins"]
                / data["total"]
                * 100
            )

            avg_probability = (
                data["prob_sum"]
                / data["total"]
            )

            self.stdout.write(
                f"{code}: "
                f"{data['wins']}/{data['total']} "
                f"| acerto={hit_rate:.1f}% "
                f"| previsto={avg_probability:.1f}%"
            )
