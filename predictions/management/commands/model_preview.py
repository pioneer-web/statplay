from datetime import date

from django.core.management.base import (
    BaseCommand,
)

from predictions.stat_engine import (
    evaluate_event,
)
from sports.models import Event


class Command(BaseCommand):
    help = (
        "Prévia do motor estatístico "
        "da StatPlay"
    )

    def add_arguments(
        self,
        parser,
    ):
        parser.add_argument(
            "--date",
            required=True,
            type=str,
        )

        parser.add_argument(
            "--limit",
            type=int,
            default=10,
        )

        parser.add_argument(
            "--min-prob",
            type=float,
            default=70,
        )

    def handle(
        self,
        *args,
        **options,
    ):
        target = date.fromisoformat(
            options["date"]
        )

        events = (
            Event.objects
            .filter(
                starts_at__date=target,
                status="scheduled",
            )
            .exclude(external_id="")
            .select_related(
                "home_team",
                "away_team",
                "competition",
            )
            .order_by(
                "starts_at"
            )
        )

        shown = 0

        for event in events:
            result = evaluate_event(
                event,
                sample=10,
                min_matches=5,
            )

            if result is None:
                continue

            strong = [
                market
                for market
                in result["markets"]
                if market["probability"]
                >= options["min_prob"]
            ]

            if not strong:
                continue

            shown += 1

            self.stdout.write(
                "\n================================"
            )

            self.stdout.write(
                f"{event.competition.name}"
            )

            self.stdout.write(
                f"{event.home_team.name} "
                f"x "
                f"{event.away_team.name}"
            )

            self.stdout.write(
                f"Amostra: "
                f"{result['home_sample']} / "
                f"{result['away_sample']}"
            )

            self.stdout.write(
                f"Gols esperados: "
                f"{result['expected_home_goals']} "
                f"x "
                f"{result['expected_away_goals']}"
            )

            for market in strong:
                self.stdout.write(
                    f"{market['label']}: "
                    f"{market['probability']}% "
                    f"| odd justa "
                    f"{market['fair_odd']} "
                    f"| confiança "
                    f"{market['confidence']}%"
                )

            if (
                shown
                >= options["limit"]
            ):
                break

        if shown == 0:
            self.stdout.write(
                "Nenhum jogo com histórico "
                "suficiente para o filtro."
            )
