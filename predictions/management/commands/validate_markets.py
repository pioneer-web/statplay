from collections import defaultdict

from django.core.management.base import BaseCommand

from predictions.stat_engine import evaluate_event
from sports.models import Event, TeamMatchStats
from sports.services.competition_filter import is_professional_competition


def outcome(event, code):
    if event.home_score is None or event.away_score is None:
        return None

    home = event.home_score
    away = event.away_score
    total = home + away

    if code == "home_win":
        return home > away

    if code == "draw":
        return home == away

    if code == "away_win":
        return away > home

    if code == "goals_over_1_5":
        return total > 1.5

    if code == "goals_over_2_5":
        return total > 2.5

    if code == "btts_yes":
        return home > 0 and away > 0

    stats = list(
        TeamMatchStats.objects.filter(event=event)
    )

    if len(stats) != 2:
        return None

    if code.startswith("corners_over_"):
        values = [x.corners for x in stats]

        if any(v is None for v in values):
            return None

        line = float(
            code.replace("corners_over_", "").replace("_", ".")
        )

        return sum(values) > line

    if code.startswith("cards_over_"):
        values = [x.cards for x in stats]

        if any(v is None for v in values):
            return None

        line = float(
            code.replace("cards_over_", "").replace("_", ".")
        )

        return sum(values) > line

    return None


def brier(records):
    if not records:
        return None

    total = 0

    for item in records:
        p = item["probability"] / 100
        y = 1 if item["outcome"] else 0

        total += (p - y) ** 2

    return total / len(records)


class Command(BaseCommand):
    help = "Validação temporal por mercado"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=5000)
        parser.add_argument("--min-prob", type=float, default=50)

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
            .order_by("starts_at", "id")
        )

        valid_events = []

        for event in events:
            if len(valid_events) >= options["limit"]:
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

            predictions = []

            for market in result["markets"]:
                probability = market["probability"]

                if probability < options["min_prob"]:
                    continue

                result_value = outcome(
                    event,
                    market["code"],
                )

                if result_value is None:
                    continue

                predictions.append({
                    "market": market["code"],
                    "probability": probability,
                    "outcome": bool(result_value),
                })

            if predictions:
                valid_events.append(predictions)

        split = int(len(valid_events) * 0.70)

        train = valid_events[:split]
        test = valid_events[split:]

        test_markets = defaultdict(list)

        for group in test:
            for item in group:
                test_markets[item["market"]].append(item)

        self.stdout.write(
            "\n=== STATPLAY MARKET VALIDATION ==="
        )

        self.stdout.write(
            f"Jogos totais: {len(valid_events)}"
        )

        self.stdout.write(
            f"Treino: {len(train)}"
        )

        self.stdout.write(
            f"Teste fora da amostra: {len(test)}"
        )

        self.stdout.write(
            "\n=== RESULTADOS POR MERCADO ==="
        )

        ranking = []

        for code, records in test_markets.items():
            if len(records) < 20:
                continue

            wins = sum(
                1 for r in records
                if r["outcome"]
            )

            real = wins / len(records) * 100

            predicted = (
                sum(
                    r["probability"]
                    for r in records
                )
                / len(records)
            )

            error = abs(
                real - predicted
            )

            score = brier(records)

            ranking.append({
                "code": code,
                "n": len(records),
                "wins": wins,
                "real": real,
                "predicted": predicted,
                "error": error,
                "brier": score,
            })

        ranking.sort(
            key=lambda x: (
                x["brier"],
                x["error"],
            )
        )

        for item in ranking:
            if (
                item["n"] >= 100
                and item["error"] <= 3
            ):
                status = "FORTE"
            elif (
                item["n"] >= 50
                and item["error"] <= 6
            ):
                status = "OBSERVAR"
            else:
                status = "NÃO LIBERAR"

            self.stdout.write(
                f"{item['code']}: "
                f"{item['wins']}/{item['n']} "
                f"| real={item['real']:.1f}% "
                f"| previsto={item['predicted']:.1f}% "
                f"| erro={item['error']:.1f}pp "
                f"| Brier={item['brier']:.4f} "
                f"| {status}"
            )
