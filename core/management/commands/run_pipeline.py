from django.core.management.base import (
    BaseCommand,
)

from core.pipeline import run_pipeline


class Command(BaseCommand):
    help = "Executa o pipeline oficial da StatPlay"

    def add_arguments(
        self,
        parser,
    ):
        parser.add_argument(
            "--date",
            required=False,
        )

    def handle(
        self,
        *args,
        **options,
    ):
        result = run_pipeline(
            options.get("date")
        )

        self.stdout.write(
            "\n=== STATPLAY PIPELINE ==="
        )

        self.stdout.write(
            f"Data: {result['date']}"
        )

        self.stdout.write(
            f"Jogos: {result['events']}"
        )

        history = result[
            "history"
        ]

        self.stdout.write(
            "Histórico: "
            f"{history['downloaded']} novos "
            f"| {history['teams_ready']} times prontos"
        )

        predictions = result[
            "predictions"
        ]

        self.stdout.write(
            "Previsões: "
            f"{predictions['generated']} novas "
            f"| {predictions['existing']} já existentes "
            f"| {predictions['insufficient']} sem base"
        )

        odds = result["odds"]

        self.stdout.write(
            "Odds: "
            f"{odds['events']} jogos "
            f"| {odds['offers']} ofertas "
            f"| {odds['snapshots']} snapshots novos"
        )

        settlement = result[
            "settlement"
        ]

        self.stdout.write(
            "Liquidação: "
            f"{settlement['settled']} encerradas "
            f"| {settlement['voided']} anuladas "
            f"| {settlement['waiting']} aguardando"
        )
