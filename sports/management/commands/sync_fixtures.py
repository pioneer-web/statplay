from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from sports.providers.sofascore import SofaScoreProvider


class Command(BaseCommand):
    help = "Sincroniza jogos do SofaScore"

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            help="Data no formato YYYY-MM-DD",
        )

        parser.add_argument(
            "--days",
            type=int,
            default=0,
            help="Quantidade de dias futuros",
        )

    def handle(self, *args, **options):
        provider = SofaScoreProvider()

        date = options.get("date")
        days = options.get("days", 0)

        try:
            if date:
                result = provider.sync_date(date)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nSINCRONIZAÇÃO CONCLUÍDA\n"
                        f"Data: {result['date']}\n"
                        f"Torneios: {result['tournaments']}\n"
                        f"Jogos encontrados: {result['events_found']}\n"
                        f"Criados: {result['created']}\n"
                        f"Atualizados: {result['updated']}\n"
                        f"Ignorados: {result['ignored']}"
                    )
                )

                return

            today = timezone.localdate()

            for offset in range(days + 1):
                current_date = (
                    today + timedelta(days=offset)
                ).isoformat()

                result = provider.sync_date(
                    current_date
                )

                self.stdout.write(
                    f"\n{current_date}"
                    f" | torneios={result['tournaments']}"
                    f" | jogos={result['events_found']}"
                    f" | criados={result['created']}"
                    f" | atualizados={result['updated']}"
                    f" | ignorados={result['ignored']}"
                )

        except Exception as exc:
            raise CommandError(str(exc))
