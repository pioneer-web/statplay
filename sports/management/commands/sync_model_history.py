from datetime import date

from django.core.management.base import (
    BaseCommand,
)
from django.db.models import Q

from sports.models import (
    Event,
    TeamMatchStats,
)
from sports.providers.sofascore import (
    SofaScoreProvider,
)
from sports.services.statistics import (
    save_event_statistics,
)


class Command(BaseCommand):
    help = (
        "Coleta histórico dos times "
        "dos jogos que serão analisados"
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
            "--teams",
            type=int,
            default=20,
        )

        parser.add_argument(
            "--matches",
            type=int,
            default=10,
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
            )
            .order_by(
                "starts_at",
                "id",
            )
        )

        teams = []
        seen = set()

        for event in events:
            for team in (
                event.home_team,
                event.away_team,
            ):
                if not team.external_id:
                    continue

                if team.id in seen:
                    continue

                seen.add(team.id)
                teams.append(team)

                if (
                    len(teams)
                    >= options["teams"]
                ):
                    break

            if (
                len(teams)
                >= options["teams"]
            ):
                break

        provider = SofaScoreProvider()

        downloaded = 0
        reused = 0
        no_stats = 0

        for index, team in enumerate(
            teams,
            start=1,
        ):
            self.stdout.write(
                f"\n[{index}/{len(teams)}] "
                f"{team.name}"
            )

            history = (
                provider
                .get_team_last_events(
                    team.external_id
                )
            )[:options["matches"]]

            for raw in history:
                if (
                    raw.get(
                        "status",
                        {},
                    ).get("type")
                    != "finished"
                ):
                    continue

                event, _ = (
                    provider._save_event(
                        raw,
                        team.sport,
                    )
                )

                if event is None:
                    continue

                if (
                    TeamMatchStats.objects
                    .filter(event=event)
                    .count()
                    == 2
                ):
                    reused += 1
                    continue

                payload = (
                    provider.get_statistics(
                        event.external_id
                    )
                )

                if save_event_statistics(
                    event,
                    payload,
                ):
                    downloaded += 1
                    self.stdout.write(
                        f"  OK {event}"
                    )
                else:
                    no_stats += 1
                    self.stdout.write(
                        f"  SEM STATS {event}"
                    )

        self.stdout.write(
            self.style.SUCCESS(
                "\nFinalizado"
                f"\nTimes: {len(teams)}"
                f"\nNovas partidas: {downloaded}"
                f"\nJá existentes: {reused}"
                f"\nSem estatísticas: {no_stats}"
            )
        )
