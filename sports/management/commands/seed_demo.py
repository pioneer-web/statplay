from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from odds.models import Bookmaker, Market, OddSnapshot
from predictions.models import ModelVersion, Prediction
from sports.models import Competition, Event, Sport, Team


class Command(BaseCommand):
    help = "Cria dados demonstrativos da StatPlay"

    def handle(self, *args, **options):

        football, _ = Sport.objects.get_or_create(
            slug="football",
            defaults={"name": "Futebol"},
        )

        competition, _ = Competition.objects.get_or_create(
            sport=football,
            name="Brasileirão",
            defaults={"country": "Brasil"},
        )

        home, _ = Team.objects.get_or_create(
            sport=football,
            name="Flamengo",
        )

        away, _ = Team.objects.get_or_create(
            sport=football,
            name="Palmeiras",
        )

        event = Event.objects.filter(
            competition=competition,
            home_team=home,
            away_team=away,
            status="scheduled",
        ).first()

        if not event:
            event = Event.objects.create(
                competition=competition,
                home_team=home,
                away_team=away,
                starts_at=timezone.now() + timedelta(days=1),
            )

        betano, _ = Bookmaker.objects.get_or_create(
            slug="betano",
            defaults={"name": "Betano"},
        )

        bet365, _ = Bookmaker.objects.get_or_create(
            slug="bet365",
            defaults={"name": "bet365"},
        )

        superbet, _ = Bookmaker.objects.get_or_create(
            slug="superbet",
            defaults={"name": "Superbet"},
        )

        corners, _ = Market.objects.get_or_create(
            code="corners_over",
            defaults={
                "name": "Total de escanteios",
                "category": "corners",
            },
        )

        goals, _ = Market.objects.get_or_create(
            code="goals_over",
            defaults={
                "name": "Total de gols",
                "category": "goals",
            },
        )

        model, _ = ModelVersion.objects.get_or_create(
            name="StatPlay Core",
            version="0.2",
            algorithm="baseline",
        )

        OddSnapshot.objects.filter(event=event).delete()

        odds = [
            (betano, corners, "Mais de", Decimal("8.50"), Decimal("1.42")),
            (bet365, corners, "Mais de", Decimal("8.50"), Decimal("1.46")),
            (superbet, corners, "Mais de", Decimal("8.50"), Decimal("1.44")),

            (betano, goals, "Mais de", Decimal("1.50"), Decimal("1.39")),
            (bet365, goals, "Mais de", Decimal("1.50"), Decimal("1.41")),
            (superbet, goals, "Mais de", Decimal("1.50"), Decimal("1.38")),
        ]

        for bookmaker, market, selection, line, odd in odds:
            OddSnapshot.objects.create(
                event=event,
                bookmaker=bookmaker,
                market=market,
                selection=selection,
                line=line,
                odd=odd,
            )

        Prediction.objects.filter(
            event=event,
            model_version=model,
        ).delete()

        Prediction.objects.create(
            event=event,
            market=corners,
            model_version=model,
            selection="Mais de",
            line=Decimal("8.50"),
            probability=Decimal("91.00"),
            confidence=Decimal("82.00"),
        )

        Prediction.objects.create(
            event=event,
            market=goals,
            model_version=model,
            selection="Mais de",
            line=Decimal("1.50"),
            probability=Decimal("84.00"),
            confidence=Decimal("78.00"),
        )

        self.stdout.write(
            self.style.SUCCESS("Dados demo da StatPlay criados.")
        )
