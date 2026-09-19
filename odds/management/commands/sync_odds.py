from django.core.management.base import BaseCommand

from odds.providers.the_odds_api import TheOddsApiProvider


class Command(BaseCommand):

    help = "Sincroniza odds das casas."

    def handle(self, *args, **options):

        provider = TheOddsApiProvider()

        result = provider.sync()

        self.stdout.write(
            self.style.SUCCESS(str(result))
        )
