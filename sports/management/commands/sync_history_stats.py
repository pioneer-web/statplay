from django.core.management.base import BaseCommand
from django.db.models import Q

from sports.models import Sport, Team
from sports.providers.sofascore import SofaScoreProvider
from sports.services.statistics import save_event_statistics


class Command(BaseCommand):
    help = "Baixa histórico recente e estatísticas dos times"

    def add_arguments(self, parser):
        parser.add_argument(
            "--teams",
            type=int,
            default=5,
        )

        parser.add_argument(
            "--matches",
            type=int,
            default=8,
        )

    def handle(self, *args, **options):
        provider = SofaScoreProvider()

        sport, _ = Sport.objects.get_or_create(
            slug="football",
            defaults={"name": "Futebol"},
        )

        teams = (
            Team.objects
            .filter(sport=sport)
            .filter(
                Q(home_events__isnull=False)
                | Q(away_events__isnull=False)
            )
            .distinct()
            .order_by("name")[
                :options["teams"]
            ]
        )

        total_events = 0
        total_stats = 0

        for position, team in enumerate(
            teams,
            start=1,
        ):
            self.stdout.write(
                f"\n[{position}/{len(teams)}] "
                f"{team.name}"
            )

            history = provider.get_team_last_events(
                team.external_id
            )

            history = history[
                :options["matches"]
            ]

            for raw_event in history:
                status = (
                    raw_event
                    .get("status", {})
                    .get("type")
                )

                if status != "finished":
                    continue

                event, _ = provider._save_event(
                    raw_event,
                    sport,
                )

                if not event:
                    continue

                total_events += 1

                try:
                    statistics = (
                        provider.get_statistics(
                            event.external_id
                        )
                    )

                    if save_event_statistics(
                        event,
                        statistics,
                    ):
                        total_stats += 1
                        self.stdout.write(
                            f"  OK {event}"
                        )
                    else:
                        self.stdout.write(
                            f"  SEM STATS {event}"
                        )

                except Exception as exc:
                    self.stdout.write(
                        f"  ERRO {event}: {exc}"
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nFinalizado:"
                f"\nEventos históricos: {total_events}"
                f"\nPartidas com estatísticas: {total_stats}"
            )
        )
