from django.core.management.base import BaseCommand
from django.db.models import Count

from sports.models import (
    Competition,
    Event,
    Team,
    TeamMatchStats,
)


class Command(BaseCommand):
    help = "Audita integridade e qualidade dos dados"

    def audit_external_ids(self, model, label):
        duplicates = (
            model.objects
            .exclude(external_id="")
            .values("external_id")
            .annotate(total=Count("id"))
            .filter(total__gt=1)
        )

        blanks = model.objects.filter(
            external_id=""
        ).count()

        self.stdout.write(
            f"{label}: "
            f"IDs duplicados={duplicates.count()} | "
            f"IDs vazios={blanks}"
        )

    def handle(self, *args, **options):
        qs = TeamMatchStats.objects.all()

        self.stdout.write(
            "\n=== STATPLAY DATA QUALITY ===\n"
        )

        self.stdout.write(
            f"TeamMatchStats: {qs.count()}"
        )

        for field in [
            "corners",
            "shots",
            "shots_on_target",
            "cards",
            "possession",
            "xg",
        ]:
            nulls = qs.filter(
                **{f"{field}__isnull": True}
            ).count()

            zeros = qs.filter(
                **{field: 0}
            ).count()

            self.stdout.write(
                f"{field}: "
                f"null={nulls} | "
                f"zero={zeros}"
            )

        bad_events = (
            qs.values("event_id")
            .annotate(total=Count("id"))
            .exclude(total=2)
            .count()
        )

        self.stdout.write(
            f"Eventos sem exatamente 2 "
            f"registros estatísticos: {bad_events}"
        )

        self.stdout.write(
            "\n=== INTEGRIDADE DOS IDs ==="
        )

        self.audit_external_ids(
            Team,
            "Times",
        )

        self.audit_external_ids(
            Competition,
            "Competições",
        )

        self.audit_external_ids(
            Event,
            "Eventos",
        )

        self.stdout.write(
            "\n=== AMOSTRA ==="
        )

        for stat in (
            qs.select_related(
                "event",
                "team",
            )
            .order_by(
                "-event__starts_at"
            )[:15]
        ):
            self.stdout.write(
                f"{stat.event.starts_at.date()} | "
                f"{stat.team.name} | "
                f"CORN={stat.corners} | "
                f"SHOTS={stat.shots} | "
                f"SOT={stat.shots_on_target} | "
                f"CARDS={stat.cards} | "
                f"POS={stat.possession} | "
                f"xG={stat.xg}"
            )
