from copy import deepcopy
from decimal import Decimal

from django.db import transaction

from odds.models import Market
from predictions.engine_v2 import (
    ENGINE_VERSION,
    evaluate_event,
)
from predictions.models import (
    ModelVersion,
    Prediction,
    PredictionContext,
)
from predictions.rationale import (
    build_rationale,
)
from sports.services.competition_scope import (
    is_target_competition,
)


def decimal_value(value):
    if value is None:
        return None

    return Decimal(
        str(value)
    )


def get_model_version():
    model, _ = (
        ModelVersion.objects
        .get_or_create(
            name="StatPlay Core",
            version=ENGINE_VERSION,
            defaults={
                "algorithm":
                    "market-specific-v2",
                "active": True,
            },
        )
    )

    ModelVersion.objects.filter(
        name="StatPlay Core",
    ).exclude(
        pk=model.pk,
    ).update(
        active=False
    )

    if not model.active:
        model.active = True
        model.save(
            update_fields=[
                "active"
            ]
        )

    return model


def same_prediction(
    prediction,
    item,
    rationale,
):
    context = getattr(
        prediction,
        "context",
        None,
    )

    if not context:
        return False

    if (
        context.rationale
        != rationale
    ):
        return False

    return (
        round(
            float(
                prediction.probability
            ),
            2,
        )
        ==
        round(
            float(
                item[
                    "probability"
                ]
            ),
            2,
        )
    )


def generate_predictions(
    events,
):
    model_version = (
        get_model_version()
    )

    generated = 0
    revised = 0
    existing = 0
    insufficient = 0

    for event in events:
        if not is_target_competition(
            event.competition.name,
            event.competition.country,
        ):
            continue

        result = evaluate_event(
            event,
            sample=10,
            min_matches=5,
        )

        if not result:
            insufficient += 1
            continue

        context_data = (
            result.get(
                "player_adjustment",
                {},
            )
        )

        base_rationale = (
            build_rationale(
                event,
                context_data,
            )
        )

        home = context_data.get(
            "home",
            {},
        )

        away = context_data.get(
            "away",
            {},
        )

        for item in result.get(
            "markets",
            [],
        ):
            market, _ = (
                Market.objects
                .get_or_create(
                    code=item["code"],
                    defaults={
                        "name":
                            item["name"],
                        "category":
                            item[
                                "category"
                            ],
                    },
                )
            )

            if (
                market.name
                != item["name"]
                or market.category
                != item["category"]
            ):
                market.name = (
                    item["name"]
                )
                market.category = (
                    item["category"]
                )
                market.save(
                    update_fields=[
                        "name",
                        "category",
                    ]
                )

            rationale = deepcopy(
                base_rationale
            )

            rationale[
                "market_analysis"
            ] = item.get(
                "analysis_rows",
                [],
            )

            rationale[
                "method"
            ] = item.get(
                "method",
                "",
            )

            rationale[
                "market_code"
            ] = item["code"]

            rationale[
                "market_name"
            ] = item["name"]

            rationale[
                "engine_version"
            ] = ENGINE_VERSION

            line = (
                Decimal(
                    str(
                        item["line"]
                    )
                )
                if item.get(
                    "line"
                )
                is not None
                else None
            )

            lookup = {
                "event":
                    event,

                "market":
                    market,

                "model_version":
                    model_version,

                "selection":
                    item["code"],

                "line":
                    line,
            }

            with transaction.atomic():
                current = (
                    Prediction.objects
                    .select_for_update()
                    .filter(
                        **lookup,
                        is_current=True,
                    )
                    .order_by(
                        "-revision",
                        "-created_at",
                    )
                    .first()
                )

                if (
                    current
                    and same_prediction(
                        current,
                        item,
                        rationale,
                    )
                ):
                    existing += 1
                    continue

                revision = 1
                reason = "initial"

                if current:
                    revision = (
                        current.revision
                        + 1
                    )

                    reason = (
                        "model_refresh"
                    )

                    Prediction.objects.filter(
                        pk=current.pk
                    ).update(
                        is_current=False
                    )

                prediction = (
                    Prediction.objects
                    .create(
                        **lookup,

                        probability=
                            decimal_value(
                                item[
                                    "probability"
                                ]
                            ),

                        confidence=
                            decimal_value(
                                item[
                                    "confidence"
                                ]
                            ),

                        fair_odd=
                            decimal_value(
                                item[
                                    "fair_odd"
                                ]
                            ),

                        locked=True,

                        revision=
                            revision,

                        is_current=True,

                        reason=
                            reason,

                        replaces=
                            current,
                    )
                )

                PredictionContext.objects.create(
                    prediction=
                        prediction,

                    engine_version=
                        ENGINE_VERSION,

                    home_lineup_available=
                        bool(
                            home.get(
                                "available",
                                False,
                            )
                        ),

                    away_lineup_available=
                        bool(
                            away.get(
                                "available",
                                False,
                            )
                        ),

                    home_lineup_confirmed=
                        bool(
                            home.get(
                                "confirmed",
                                False,
                            )
                        ),

                    away_lineup_confirmed=
                        bool(
                            away.get(
                                "confirmed",
                                False,
                            )
                        ),

                    home_attack_factor=
                        decimal_value(
                            home.get(
                                "attack_factor",
                                1,
                            )
                        ),

                    away_attack_factor=
                        decimal_value(
                            away.get(
                                "attack_factor",
                                1,
                            )
                        ),

                    home_defense_factor=
                        decimal_value(
                            home.get(
                                "defense_factor",
                                1,
                            )
                        ),

                    away_defense_factor=
                        decimal_value(
                            away.get(
                                "defense_factor",
                                1,
                            )
                        ),

                    base_home_goals=
                        decimal_value(
                            context_data.get(
                                "base_home_goals"
                            )
                        ),

                    base_away_goals=
                        decimal_value(
                            context_data.get(
                                "base_away_goals"
                            )
                        ),

                    adjusted_home_goals=
                        decimal_value(
                            context_data.get(
                                "adjusted_home_goals"
                            )
                        ),

                    adjusted_away_goals=
                        decimal_value(
                            context_data.get(
                                "adjusted_away_goals"
                            )
                        ),

                    rationale=
                        rationale,
                )

                if current:
                    revised += 1
                else:
                    generated += 1

    return {
        "generated":
            generated,

        "revised":
            revised,

        "existing":
            existing,

        "insufficient":
            insufficient,
    }
