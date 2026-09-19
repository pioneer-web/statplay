from django.core.management.base import BaseCommand

from sports.models import Event
from sports.providers.sofascore import SofaScoreProvider


class Command(BaseCommand):
    help = "Testa disponibilidade de odds reais do SofaScore"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=50,
        )

    def handle(self, *args, **options):
        provider = SofaScoreProvider()

        events = (
            Event.objects
            .exclude(external_id="")
            .filter(status="scheduled")
            .select_related(
                "home_team",
                "away_team",
                "competition",
            )
            .order_by("starts_at")[
                :options["limit"]
            ]
        )

        tested = 0
        with_odds = 0
        markets_total = 0

        self.stdout.write(
            "\n=== STATPLAY ODDS AUDIT ==="
        )

        for event in events:
            tested += 1

            try:
                data = provider.get_odds(
                    event.external_id
                ) or {}

                markets = data.get(
                    "markets",
                    []
                )

                if not markets:
                    continue

                with_odds += 1
                markets_total += len(markets)

                self.stdout.write(
                    f"\n{event.home_team.name} "
                    f"x {event.away_team.name}"
                )

                self.stdout.write(
                    f"Mercados: {len(markets)}"
                )

                for market in markets[:5]:
                    name = market.get(
                        "marketName"
                    ) or market.get(
                        "name"
                    ) or "Mercado"

                    choices = market.get(
                        "choices",
                        []
                    )

                    odds = []

                    for choice in choices:
                        label = (
                            choice.get("name")
                            or choice.get("fractionalValue")
                            or "?"
                        )

                        decimal = (
                            choice.get("decimalValue")
                            or choice.get("decimal")
                            or choice.get("value")
                        )

                        odds.append(
                            f"{label}={decimal}"
                        )

                    self.stdout.write(
                        f"  {name}: "
                        + " | ".join(odds)
                    )

            except Exception as exc:
                self.stdout.write(
                    f"ERRO {event.external_id}: "
                    f"{exc}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                "\n\n=== RESUMO ODDS ==="
                f"\nJogos testados: {tested}"
                f"\nJogos com odds: {with_odds}"
                f"\nMercados encontrados: {markets_total}"
                f"\nCobertura: "
                f"{(with_odds/tested*100 if tested else 0):.1f}%"
            )
        )
