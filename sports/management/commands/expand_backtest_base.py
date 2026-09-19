import time
from datetime import date

from django.core.management.base import BaseCommand
from django.db.models import Count

from sports.models import Competition, Event, TeamMatchStats
from sports.providers.sofascore import SofaScoreProvider
from sports.services.competition_filter import is_professional_competition
from sports.services.statistics import save_event_statistics


class Command(BaseCommand):
    help = "Expande a base histórica profissional da StatPlay"

    def add_arguments(self, parser):
        parser.add_argument("--date", required=True)
        parser.add_argument("--competitions", type=int, default=5)
        parser.add_argument("--matches", type=int, default=20)
        parser.add_argument("--pages", type=int, default=2)

    def handle(self, *args, **options):
        target = date.fromisoformat(options["date"])

        ranking = (
            Event.objects
            .filter(
                starts_at__date=target,
                status="scheduled",
            )
            .exclude(external_id="")
            .values("competition_id")
            .annotate(total=Count("id"))
            .order_by("-total")
        )

        competitions = []

        for row in ranking:
            comp = Competition.objects.get(
                id=row["competition_id"]
            )

            if not is_professional_competition(comp.name):
                continue

            competitions.append(comp)

            if len(competitions) >= options["competitions"]:
                break

        self.stdout.write("\n=== COMPETIÇÕES ===")

        for comp in competitions:
            self.stdout.write(
                f"{comp.country} | {comp.name}"
            )

        fixtures = (
            Event.objects
            .filter(
                starts_at__date=target,
                competition__in=competitions,
            )
            .select_related(
                "home_team",
                "away_team",
            )
        )

        teams = {}

        for event in fixtures:
            for team in (
                event.home_team,
                event.away_team,
            ):
                if team.external_id:
                    teams[team.id] = team

        teams = list(teams.values())

        provider = SofaScoreProvider()

        downloaded = 0
        reused = 0
        no_stats = 0
        errors = 0

        for index, team in enumerate(
            teams,
            start=1,
        ):
            self.stdout.write(
                f"[{index}/{len(teams)}] {team.name}"
            )

            history = []
            seen = set()

            for page in range(options["pages"]):
                try:
                    data = provider._get_web(
                        f"team/{team.external_id}/events/last/{page}"
                    ) or {}
                except Exception:
                    errors += 1
                    break

                for raw in data.get("events", []):
                    event_id = raw.get("id")

                    if (
                        not event_id
                        or event_id in seen
                    ):
                        continue

                    if (
                        raw.get("status", {}).get("type")
                        != "finished"
                    ):
                        continue

                    seen.add(event_id)
                    history.append(raw)

                    if len(history) >= options["matches"]:
                        break

                if len(history) >= options["matches"]:
                    break

            for raw in history:
                try:
                    event, _ = provider._save_event(
                        raw,
                        team.sport,
                    )

                    if not event:
                        continue

                    if (
                        TeamMatchStats.objects
                        .filter(event=event)
                        .count()
                        == 2
                    ):
                        reused += 1
                        continue

                    payload = provider.get_statistics(
                        event.external_id
                    )

                    if save_event_statistics(
                        event,
                        payload,
                    ):
                        downloaded += 1
                    else:
                        no_stats += 1

                    time.sleep(0.15)

                except Exception:
                    errors += 1

        self.stdout.write(
            self.style.SUCCESS(
                "\n=== EXPANSÃO CONCLUÍDA ==="
                f"\nCompetições: {len(competitions)}"
                f"\nTimes: {len(teams)}"
                f"\nNovas partidas: {downloaded}"
                f"\nReaproveitadas: {reused}"
                f"\nSem estatísticas: {no_stats}"
                f"\nErros: {errors}"
            )
        )
