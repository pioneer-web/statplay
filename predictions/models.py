from django.db import models

from sports.models import Event
from odds.models import Market


class ModelVersion(models.Model):
    name = models.CharField(
        max_length=100
    )
    version = models.CharField(
        max_length=40
    )
    algorithm = models.CharField(
        max_length=80
    )
    trained_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    active = models.BooleanField(
        default=True
    )

    def __str__(self):
        return (
            f"{self.name} "
            f"{self.version}"
        )


class Prediction(models.Model):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="predictions",
    )
    market = models.ForeignKey(
        Market,
        on_delete=models.PROTECT,
    )
    model_version = models.ForeignKey(
        ModelVersion,
        on_delete=models.PROTECT,
    )

    selection = models.CharField(
        max_length=120
    )

    line = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )

    probability = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        db_index=True,
    )

    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    fair_odd = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    locked = models.BooleanField(
        default=True
    )

    revision = (
        models.PositiveSmallIntegerField(
            default=1
        )
    )

    is_current = models.BooleanField(
        default=True,
        db_index=True,
    )

    reason = models.CharField(
        max_length=30,
        default="initial",
    )

    replaces = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="revisions",
    )

    result = models.CharField(
        max_length=10,
        choices=[
            (
                "pending",
                "Pendente",
            ),
            (
                "win",
                "Acerto",
            ),
            (
                "loss",
                "Erro",
            ),
            (
                "void",
                "Anulada",
            ),
        ],
        default="pending",
    )

    settled_at = (
        models.DateTimeField(
            null=True,
            blank=True,
        )
    )

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "-probability",
                    "created_at",
                ]
            ),
            models.Index(
                fields=[
                    "event",
                    "model_version",
                    "is_current",
                ]
            ),
        ]

    def save(
        self,
        *args,
        **kwargs,
    ):
        if (
            self.probability
            and not self.fair_odd
        ):
            self.fair_odd = round(
                100
                / float(
                    self.probability
                ),
                3,
            )

        super().save(
            *args,
            **kwargs,
        )


class PredictionContext(
    models.Model
):
    prediction = (
        models.OneToOneField(
            Prediction,
            on_delete=models.CASCADE,
            related_name="context",
        )
    )

    engine_version = (
        models.CharField(
            max_length=30,
            default="1.1.0",
        )
    )

    home_lineup_available = (
        models.BooleanField(
            default=False
        )
    )
    away_lineup_available = (
        models.BooleanField(
            default=False
        )
    )

    home_lineup_confirmed = (
        models.BooleanField(
            default=False
        )
    )
    away_lineup_confirmed = (
        models.BooleanField(
            default=False
        )
    )

    home_attack_factor = (
        models.DecimalField(
            max_digits=6,
            decimal_places=4,
            default=1,
        )
    )
    away_attack_factor = (
        models.DecimalField(
            max_digits=6,
            decimal_places=4,
            default=1,
        )
    )

    home_defense_factor = (
        models.DecimalField(
            max_digits=6,
            decimal_places=4,
            default=1,
        )
    )
    away_defense_factor = (
        models.DecimalField(
            max_digits=6,
            decimal_places=4,
            default=1,
        )
    )

    base_home_goals = (
        models.DecimalField(
            max_digits=6,
            decimal_places=3,
            null=True,
            blank=True,
        )
    )
    base_away_goals = (
        models.DecimalField(
            max_digits=6,
            decimal_places=3,
            null=True,
            blank=True,
        )
    )

    adjusted_home_goals = (
        models.DecimalField(
            max_digits=6,
            decimal_places=3,
            null=True,
            blank=True,
        )
    )
    adjusted_away_goals = (
        models.DecimalField(
            max_digits=6,
            decimal_places=3,
            null=True,
            blank=True,
        )
    )

    # Snapshot exato dos dados usados
    # para explicar a previsão.
    rationale = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = (
        models.DateTimeField(
            auto_now_add=True
        )
    )
