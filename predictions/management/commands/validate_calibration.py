from collections import defaultdict

from django.core.management.base import BaseCommand

from predictions.stat_engine import evaluate_event
from sports.models import Event, TeamMatchStats
from sports.services.competition_filter import (
    is_professional_competition,
)


BANDS = [
    (60, 70, "60-69%"),
    (70, 80, "70-79%"),
    (80, 90, "80-89%"),
    (90, 101, "90%+"),
]


def band_index(probability):
    for index, (low, high, _) in enumerate(BANDS):
        if low <= probability < high:
            return index

    return None


def actual_result(event, market):
    code = market["code"]

    if (
        event.home_score is None
        or event.away_score is None
    ):
        return None

    home = event.home_score
    away = event.away_score
    goals = home + away

    if code == "home_win":
        return home > away

    if code == "draw":
        return home == away

    if code == "away_win":
        return away > home

    if code == "goals_over_1_5":
        return goals > 1.5

    if code == "goals_over_2_5":
        return goals > 2.5

    if code == "btts_yes":
        return home > 0 and away > 0

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


def fit_monotonic_calibrator(records):
    stats = [
        {
            "wins": 0,
            "total": 0,
        }
        for _ in BANDS
    ]

    for record in records:
        index = band_index(
            record["probability"]
        )

        if index is None:
            continue

        stats[index]["total"] += 1

        if record["outcome"]:
            stats[index]["wins"] += 1

    blocks = []

    for index, stat in enumerate(stats):
        total = stat["total"]
        wins = stat["wins"]

        if total:
            rate = wins / total
        else:
            low, high, _ = BANDS[index]
            rate = (
                (low + high - 1) / 2
            ) / 100

        blocks.append({
            "indices": [index],
            "wins": wins,
            "total": total,
            "rate": rate,
        })

        while (
            len(blocks) >= 2
            and blocks[-2]["rate"]
            > blocks[-1]["rate"]
        ):
            right = blocks.pop()
            left = blocks.pop()

            total = (
                left["total"]
                + right["total"]
            )

            wins = (
                left["wins"]
                + right["wins"]
            )

            if total:
                rate = wins / total
            else:
                rate = (
                    left["rate"]
                    + right["rate"]
                ) / 2

            blocks.append({
                "indices": (
                    left["indices"]
                    + right["indices"]
                ),
                "wins": wins,
                "total": total,
                "rate": rate,
            })

    mapping = {}

    for block in blocks:
        for index in block["indices"]:
            mapping[index] = (
                block["rate"] * 100
            )

    return mapping, stats


def brier(records, probability_key):
    if not records:
        return None

    total = 0

    for record in records:
        p = (
            record[probability_key]
            / 100
        )

        y = (
            1.0
            if record["outcome"]
            else 0.0
        )

        total += (p - y) ** 2

    return total / len(records)


class Command(BaseCommand):
    help = "Validação temporal da calibração"

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

        parser.add_argument(
            "--train-ratio",
            type=float,
            default=0.70,
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
            .order_by(
                "starts_at",
                "id",
            )
        )

        event_records = []

        for event in events:
            if (
                len(event_records)
                >= options["limit"]
            ):
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

            records = []

            for market in result["markets"]:
                probability = market[
                    "probability"
                ]

                if (
                    probability
                    < options["min_prob"]
                ):
                    continue

                outcome = actual_result(
                    event,
                    market,
                )

                if outcome is None:
                    continue

                records.append({
                    "market": market["code"],
                    "probability": probability,
                    "outcome": bool(outcome),
                })

            if records:
                event_records.append(
                    {
                        "date": event.starts_at,
                        "records": records,
                    }
                )

        if len(event_records) < 20:
            self.stdout.write(
                self.style.ERROR(
                    "Base histórica insuficiente."
                )
            )
            return

        split = int(
            len(event_records)
            * options["train_ratio"]
        )

        train_events = (
            event_records[:split]
        )

        test_events = (
            event_records[split:]
        )

        train_records = [
            record
            for event in train_events
            for record in event["records"]
        ]

        test_records = [
            record
            for event in test_events
            for record in event["records"]
        ]

        mapping, train_stats = (
            fit_monotonic_calibrator(
                train_records
            )
        )

        for record in test_records:
            index = band_index(
                record["probability"]
            )

            if index is None:
                record[
                    "calibrated_probability"
                ] = record["probability"]
            else:
                record[
                    "calibrated_probability"
                ] = mapping[index]

        raw_brier = brier(
            test_records,
            "probability",
        )

        calibrated_brier = brier(
            test_records,
            "calibrated_probability",
        )

        self.stdout.write(
            "\n=== STATPLAY CALIBRATION VALIDATION ==="
        )

        self.stdout.write(
            f"Jogos treino: {len(train_events)}"
        )

        self.stdout.write(
            f"Jogos teste: {len(test_events)}"
        )

        self.stdout.write(
            f"Previsões treino: "
            f"{len(train_records)}"
        )

        self.stdout.write(
            f"Previsões teste: "
            f"{len(test_records)}"
        )

        self.stdout.write(
            "\n=== CALIBRADOR APRENDIDO ==="
        )

        for index, band in enumerate(BANDS):
            stat = train_stats[index]

            self.stdout.write(
                f"{band[2]}: "
                f"{stat['wins']}/"
                f"{stat['total']} "
                f"=> "
                f"{mapping[index]:.1f}%"
            )

        self.stdout.write(
            "\n=== VALIDAÇÃO FORA DA AMOSTRA ==="
        )

        result_bands = defaultdict(
            lambda: {
                "total": 0,
                "wins": 0,
                "raw_sum": 0.0,
                "cal_sum": 0.0,
            }
        )

        for record in test_records:
            index = band_index(
                record["probability"]
            )

            if index is None:
                continue

            label = BANDS[index][2]

            result_bands[label][
                "total"
            ] += 1

            result_bands[label][
                "raw_sum"
            ] += record["probability"]

            result_bands[label][
                "cal_sum"
            ] += record[
                "calibrated_probability"
            ]

            if record["outcome"]:
                result_bands[label][
                    "wins"
                ] += 1

        for _, _, label in BANDS:
            data = result_bands[label]

            if not data["total"]:
                continue

            actual = (
                data["wins"]
                / data["total"]
                * 100
            )

            raw = (
                data["raw_sum"]
                / data["total"]
            )

            calibrated = (
                data["cal_sum"]
                / data["total"]
            )

            self.stdout.write(
                f"{label}: "
                f"{data['wins']}/"
                f"{data['total']} "
                f"| real={actual:.1f}% "
                f"| bruto={raw:.1f}% "
                f"| calibrado="
                f"{calibrated:.1f}%"
            )

        self.stdout.write(
            "\n=== BRIER SCORE ==="
        )

        self.stdout.write(
            f"Modelo bruto: "
            f"{raw_brier:.4f}"
        )

        self.stdout.write(
            f"Modelo calibrado: "
            f"{calibrated_brier:.4f}"
        )

        if (
            calibrated_brier
            < raw_brier
        ):
            self.stdout.write(
                self.style.SUCCESS(
                    "CALIBRAÇÃO MELHOROU "
                    "A PREVISÃO."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "CALIBRAÇÃO NÃO MELHOROU "
                    "FORA DA AMOSTRA."
                )
            )
