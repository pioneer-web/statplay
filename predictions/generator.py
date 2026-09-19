from decimal import Decimal

from odds.models import Market
from predictions.models import (
    ModelVersion,
    Prediction,
    PredictionContext,
)
from predictions.stat_engine_v11 import (
    evaluate_event,
)


OFFICIAL_MARKETS = {
    "goals_over_1_5": (
        "Mais de 1.5 gols",
        "goals",
        1.5,
    ),
    "cards_over_2_5": (
        "Mais de 2.5 cartões",
        "cards",
        2.5,
    ),
    "corners_over_7_5": (
        "Mais de 7.5 escanteios",
        "corners",
        7.5,
    ),
    "corners_over_8_5": (
        "Mais de 8.5 escanteios",
        "corners",
        8.5,
    ),
    "cards_over_3_5": (
        "Mais de 3.5 cartões",
        "cards",
        3.5,
    ),
    "btts_yes": (
        "Ambas marcam",
        "btts",
        None,
    ),
}


def get_model_version():
    model, _ = (
        ModelVersion.objects
        .get_or_create(
            name="StatPlay Core",
            version="1.1.0",
            defaults={
                "algorithm": (
                    "recent-form+poisson"
                    "+player-lineup"
                ),
                "active": True,
            },
        )
    )

    return model


def generate_predictions(events):
    model_version = (
        get_model_version()
    )

    generated = 0
    existing = 0
    insufficient = 0

    for event in events:
        result = evaluate_event(
            event,
            sample=10,
            min_matches=5,
        )

        if not result:
            insufficient += 1
            continue

        calculated = {
            item["code"]: item
            for item in result.get(
                "markets",
                [],
            )
        }

        context_data = result.get(
            "player_adjustment",
            {},
        )

        home = context_data.get(
            "home",
            {},
        )

        away = context_data.get(
            "away",
            {},
        )

        for code, definition in (
            OFFICIAL_MARKETS.items()
        ):
            if code not in calculated:
                continue

            name, category, line = (
                definition
            )

            market, _ = (
                Market.objects
                .get_or_create(
                    code=code,
                    defaults={
                        "name": name,
                        "category": category,
                    },
                )
            )

            item = calculated[code]

            lookup = {
                "event": event,
                "market": market,
                "model_version": (
                    model_version
                ),
                "selection": code,
                "line": (
                    Decimal(str(line))
                    if line is not None
                    else None
                ),
            }

            prediction = (
                Prediction.objects
                .filter(**lookup)
                .first()
            )

            if prediction:
                existing += 1
                continue

            prediction = (
                Prediction.objects.create(
                    **lookup,
                    probability=Decimal(
                        str(
                            item[
                                "probability"
                            ]
                        )
                    ),
                    confidence=Decimal(
                        str(
                            item.get(
                                "confidence",
                                0,
                            )
                        )
                    ),
                    fair_odd=(
                        Decimal(
                            str(
                                item[
                                    "fair_odd"
                                ]
                            )
                        )
                        if item.get(
                            "fair_odd"
                        )
                        else None
                    ),
                    locked=True,
                )
            )

            PredictionContext.objects.create(
                prediction=prediction,
                engine_version="1.1.0",

                home_lineup_available=bool(
                    home.get(
                        "available",
                        False,
                    )
                ),
                away_lineup_available=bool(
                    away.get(
                        "available",
                        False,
                    )
                ),

                home_lineup_confirmed=bool(
                    home.get(
                        "confirmed",
                        False,
                    )
                ),
                away_lineup_confirmed=bool(
                    away.get(
                        "confirmed",
                        False,
                    )
                ),

                home_attack_factor=Decimal(
                    str(
                        home.get(
                            "attack_factor",
                            1,
                        )
                    )
                ),
                away_attack_factor=Decimal(
                    str(
                        away.get(
                            "attack_factor",
                            1,
                        )
                    )
                ),

                home_defense_factor=Decimal(
                    str(
                        home.get(
                            "defense_factor",
                            1,
                        )
                    )
                ),
                away_defense_factor=Decimal(
                    str(
                        away.get(
                            "defense_factor",
                            1,
                        )
                    )
                ),

                base_home_goals=(
                    context_data.get(
                        "base_home_goals"
                    )
                ),
                base_away_goals=(
                    context_data.get(
                        "base_away_goals"
                    )
                ),
                adjusted_home_goals=(
                    context_data.get(
                        "adjusted_home_goals"
                    )
                ),
                adjusted_away_goals=(
                    context_data.get(
                        "adjusted_away_goals"
                    )
                ),
            )

            generated += 1

    return {
        "generated": generated,
        "existing": existing,
        "insufficient": insufficient,
    }
