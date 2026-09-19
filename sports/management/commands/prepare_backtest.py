from datetime import date

from django.core.management.base import BaseCommand
from django.db.models import Count

from sports.models import Competition, Event, TeamMatchStats
from sports.providers.sofascore import SofaScoreProvider
from sports.services.competition_filter import is_professional_competition
from sports.services.statistics import save_event_statistics


class Command(BaseCommand):
    help = "Prepara uma base histórica consistente para backtest"

    def add_arguments(self, parser):
        parser.add_argument("--date", required=True)
        parser.add_argument("--matches", type=int, default=30)
        parser.add_argument("--pages", type=int, default=3)

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

        competition = None

        for row in ranking:
            candidate = Competition.objects.get(
                id=row["competition_id"]
            )

            if is_professional_competition(
                candidate.name
            ):
                competition = candidate
                break

        if competition is None:
            self.stdout.write(
                self.style.ERROR(
                    "Nenhuma competição profissional encontrada."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"\nCompetição escolhida: "
                f"{competition.name} "
                f"({competition.country})"
            )
        )

        fixtures = (
            Event.objects
            .filter(
                starts_at__date=target,
                competition=competition,
            )
            .select_related(
                "home_team",
                "away_team",
            )
        )

        teams = {}

        for event in fixtures:
            if event.home_team.external_id:
                teams[event.home_team.id] = event.home_team

            if event.away_team.external_id:
                teams[event.away_team.id] = event.away_team

        teams = list(teams.values())

        self.stdout.write(
            f"Times encontrados: {len(teams)}"
        )

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
                f"\n[{index}/{len(teams)}] {team.name}"
            )

            history = []
            seen = set()

            for page in range(options["pages"]):
                try:
                    data = provider._get_web(
                        f"team/{team.external_id}/events/last/{page}"
                    ) or {}
                except Exception as exc:
                    self.stdout.write(
                        f"  ERRO página {page}: {exc}"
                    )
                    errors += 1
                    break

                events = data.get("events", [])

                if not events:
                    break

                for raw in events:
                    event_id = raw.get("id")

                    if not event_id:
                        continue

                    if event_id in seen:
                        continue

                    if (
                        raw.get("status", {})
                        .get("type")
                        != "finished"
                    ):
                        continue

                    seen.add(event_id)
                    history.append(raw)

                    if (
                        len(history)
                        >= options["matches"]
                    ):
                        break

                if (
                    len(history)
                    >= options["matches"]
                ):
                    break

            self.stdout.write(
                f"  Histórico: {len(history)} jogos"
            )

            for raw in history:
                try:
                    event, _ = provider._save_event(
                        raw,
                        team.sport,
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

                except Exception:
                    errors += 1

        self.stdout.write(
            self.style.SUCCESS(
                "\n\n=== BASE DE BACKTEST ==="
                f"\nCompetição: {competition.name}"
                f"\nTimes: {len(teams)}"
                f"\nNovas partidas com stats: {downloaded}"
                f"\nPartidas reaproveitadas: {reused}"
                f"\nSem estatísticas: {no_stats}"
                f"\nErros: {errors}"
            )
        )
