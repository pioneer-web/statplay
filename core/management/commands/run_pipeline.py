from django.core.management.base import (
    BaseCommand,
)

from core.pipeline import (
    run_pipeline,
)


class Command(BaseCommand):
    help = (
        "Executa o pipeline "
        "oficial da StatPlay"
    )

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
            options.get(
                "date"
            )
        )

        self.stdout.write(
            "\n=== STATPLAY PIPELINE ==="
        )

        self.stdout.write(
            f"Data: "
            f"{result['date']}"
        )

        self.stdout.write(
            f"Jogos no escopo: "
            f"{result['events']}"
        )

        history = (
            result["history"]
        )

        self.stdout.write(
            "Histórico dos times: "
            f"{history['downloaded']} novos "
            f"| "
            f"{history['teams_ready']} prontos"
        )

        player_history = (
            result[
                "player_history"
            ]
        )

        self.stdout.write(
            "Histórico jogadores: "
            f"{player_history['processed']} novos "
            f"| "
            f"{player_history['cached']} em cache "
            f"| "
            f"{player_history['errors']} erros"
        )

        lineups = (
            result["lineups"]
        )

        self.stdout.write(
            "Escalações: "
            f"{lineups['available']} disponíveis "
            f"| "
            f"{lineups['confirmed']} confirmadas "
            f"| "
            f"{lineups['starters']} titulares"
        )

        predictions = (
            result[
                "predictions"
            ]
        )

        self.stdout.write(
            "Previsões: "
            f"{predictions['generated']} novas "
            f"| "
            f"{predictions['revised']} revisadas "
            f"| "
            f"{predictions['existing']} mantidas "
            f"| "
            f"{predictions['insufficient']} sem base"
        )

        odds = result["odds"]

        self.stdout.write(
            "Odds: "
            f"{odds['events']} jogos "
            f"| "
            f"{odds['offers']} ofertas "
            f"| "
            f"{odds['snapshots']} snapshots novos"
        )

        settlement = (
            result[
                "settlement"
            ]
        )

        self.stdout.write(
            "Liquidação: "
            f"{settlement['settled']} encerradas "
            f"| "
            f"{settlement['voided']} anuladas "
            f"| "
            f"{settlement['waiting']} aguardando"
        )
