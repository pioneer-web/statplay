import time
from datetime import date

from django.core.management.base import (
    BaseCommand,
)

from sports.models import (
    Event,
    Player,
    PlayerMatchStats,
)
from sports.providers.sofascore import (
    SofaScoreProvider,
)
from sports.services.player_data import (
    sync_finished_event,
    sync_upcoming_lineup,
)


class Command(BaseCommand):
    help = (
        "Coleta histórico individual "
        "e escalações da StatPlay"
    )

    def add_arguments(
        self,
        parser,
    ):
        parser.add_argument(
            "--date",
            required=True,
        )

        parser.add_argument(
            "--history-limit",
            type=int,
            default=400,
        )

        parser.add_argument(
            "--delay",
            type=float,
            default=0.10,
        )

    def handle(
        self,
        *args,
        **options,
    ):
        provider = (
            SofaScoreProvider()
        )

        history = (
            Event.objects
            .filter(
                status="finished",
                team_stats__isnull=False,
            )
            .exclude(external_id="")
            .select_related(
                "home_team",
                "away_team",
            )
            .distinct()
            .order_by(
                "-starts_at"
            )[
                :options[
                    "history_limit"
                ]
            ]
        )

        processed = 0
        skipped = 0
        players_saved = 0
        errors = 0

        for index, event in enumerate(
            history,
            start=1,
        ):
            existing = (
                PlayerMatchStats.objects
                .filter(event=event)
                .count()
            )

            if existing >= 14:
                skipped += 1
                continue

            try:
                result = (
                    sync_finished_event(
                        event,
                        provider,
                    )
                )

                players_saved += (
                    result["saved"]
                )

                processed += 1

            except Exception:
                errors += 1

            if index % 50 == 0:
                self.stdout.write(
                    f"Histórico: "
                    f"{index}/"
                    f"{len(history)}"
                )

            time.sleep(
                options["delay"]
            )

        target = date.fromisoformat(
            options["date"]
        )

        upcoming = (
            Event.objects
            .filter(
                starts_at__date=target,
                status="scheduled",
            )
            .exclude(external_id="")
            .select_related(
                "home_team",
                "away_team",
            )
        )

        lineup_available = 0
        lineup_confirmed = 0
        starters = 0

        for event in upcoming:
            try:
                result = (
                    sync_upcoming_lineup(
                        event,
                        provider,
                    )
                )

                if result[
                    "available"
                ]:
                    lineup_available += 1

                if result[
                    "confirmed"
                ]:
                    lineup_confirmed += 1

                starters += (
                    result[
                        "starters"
                    ]
                )

            except Exception:
                errors += 1

            time.sleep(
                options["delay"]
            )

        self.stdout.write(
            self.style.SUCCESS(
                "\n=== STATPLAY PLAYER LAYER ==="
                f"\nEventos históricos processados: "
                f"{processed}"
                f"\nEventos reaproveitados: "
                f"{skipped}"
                f"\nRegistros jogador/partida: "
                f"{PlayerMatchStats.objects.count()}"
                f"\nJogadores únicos: "
                f"{Player.objects.count()}"
                f"\nJogos futuros com escalação: "
                f"{lineup_available}"
                f"\nEscalações confirmadas: "
                f"{lineup_confirmed}"
                f"\nTitulares capturados: "
                f"{starters}"
                f"\nErros: "
                f"{errors}"
            )
        )
