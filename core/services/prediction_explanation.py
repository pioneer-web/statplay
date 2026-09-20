from odds.models import (
    OddSnapshot,
)
from sports.services.features import (
    team_recent_features,
)


GROUPS = {
    "home_win": (
        "home_win",
        "draw",
        "away_win",
    ),

    "draw": (
        "home_win",
        "draw",
        "away_win",
    ),

    "away_win": (
        "home_win",
        "draw",
        "away_win",
    ),

    "btts_yes": (
        "btts_yes",
        "btts_no",
    ),

    "btts_no": (
        "btts_yes",
        "btts_no",
    ),
}


for prefix, lines in (
    (
        "goals",
        (1.5, 2.5, 3.5),
    ),
    (
        "corners",
        (
            7.5,
            8.5,
            9.5,
            10.5,
        ),
    ),
    (
        "cards",
        (
            2.5,
            3.5,
            4.5,
            5.5,
        ),
    ),
):
    for line in lines:
        value = (
            str(line)
            .replace(
                ".",
                "_",
            )
        )

        pair = (
            f"{prefix}_over_{value}",
            f"{prefix}_under_{value}",
        )

        GROUPS[
            pair[0]
        ] = pair

        GROUPS[
            pair[1]
        ] = pair


def latest_snapshot(
    event,
    bookmaker_id,
    selection,
):
    return (
        OddSnapshot.objects
        .filter(
            event=event,
            bookmaker_id=
                bookmaker_id,
            selection=
                selection,
        )
        .order_by(
            "-captured_at"
        )
        .first()
    )


def best_odd(prediction):
    candidates = (
        OddSnapshot.objects
        .filter(
            event=
                prediction.event,

            selection=
                prediction.selection,
        )
        .select_related(
            "bookmaker"
        )
        .order_by(
            "bookmaker_id",
            "-captured_at",
        )
    )

    latest = {}

    for snapshot in candidates:
        if (
            snapshot.bookmaker_id
            not in latest
        ):
            latest[
                snapshot.bookmaker_id
            ] = snapshot

    if not latest:
        return None

    best = max(
        latest.values(),
        key=lambda item:
            float(item.odd),
    )

    odd = float(
        best.odd
    )

    raw_probability = (
        100 / odd
    )

    group = GROUPS.get(
        prediction.selection
    )

    market_probability = None
    edge_method = (
        "implícita bruta"
    )

    if group:
        group_snapshots = []

        for selection in group:
            snapshot = (
                latest_snapshot(
                    prediction.event,
                    best.bookmaker_id,
                    selection,
                )
            )

            if not snapshot:
                group_snapshots = []
                break

            group_snapshots.append(
                snapshot
            )

        if group_snapshots:
            implied_values = [
                1
                / float(
                    snapshot.odd
                )
                for snapshot
                in group_snapshots
            ]

            margin_sum = sum(
                implied_values
            )

            target_index = (
                list(group).index(
                    prediction.selection
                )
            )

            market_probability = (
                implied_values[
                    target_index
                ]
                / margin_sum
                * 100
            )

            edge_method = (
                "probabilidade "
                "de mercado sem margem"
            )

    comparison_probability = (
        market_probability
        if market_probability
        is not None
        else raw_probability
    )

    edge = (
        float(
            prediction.probability
        )
        - comparison_probability
    )

    return {
        "odd":
            best.odd,

        "bookmaker":
            best.bookmaker.name,

        "captured_at":
            best.captured_at,

        "raw_implied":
            round(
                raw_probability,
                1,
            ),

        "market_probability": (
            round(
                market_probability,
                1,
            )
            if market_probability
            is not None
            else None
        ),

        "edge":
            round(
                edge,
                1,
            ),

        "edge_method":
            edge_method,
    }


def fallback_form(
    team,
    event,
):
    data = team_recent_features(
        team,
        before=
            event.starts_at,
        limit=10,
    )

    return {
        "team":
            team.name,

        "matches":
            data.get(
                "matches",
                0,
            ),

        "goals_for":
            data.get(
                "goals_for"
            ),

        "goals_against":
            data.get(
                "goals_against"
            ),

        "xg":
            data.get(
                "xg_for"
            ),

        "shots_on_target":
            data.get(
                "shots_target_for"
            ),

        "corners":
            data.get(
                "corners_for"
            ),

        "cards":
            data.get(
                "cards_for"
            ),
    }


def conclusion(prediction):
    category = (
        prediction.market.category
    )

    if category in (
        "result",
        "double_chance",
        "goals",
    ):
        return (
            "A probabilidade combina força "
            "ofensiva e defensiva, gols, xG, "
            "chutes no alvo, mando, escalação "
            "e distribuição de placares."
        )

    if category == "corners":
        return (
            "Este mercado usa um motor próprio "
            "de escanteios, considerando "
            "escanteios produzidos e cedidos "
            "e volume ofensivo recente."
        )

    if category == "cards":
        return (
            "Este mercado usa um motor próprio "
            "de cartões, considerando o histórico "
            "de cartões produzidos e cedidos "
            "pelas duas equipes."
        )

    return (
        "Probabilidade calculada pelo "
        "StatPlay Engine."
    )


def build_explanation(
    prediction,
):
    context = getattr(
        prediction,
        "context",
        None,
    )

    rationale = (
        context.rationale
        if context
        else {}
    )

    event = prediction.event

    return {
        "home_form":
            rationale.get(
                "home_form"
            )
            or fallback_form(
                event.home_team,
                event,
            ),

        "away_form":
            rationale.get(
                "away_form"
            )
            or fallback_form(
                event.away_team,
                event,
            ),

        "home_lineup":
            rationale.get(
                "home_lineup",
                {},
            ),

        "away_lineup":
            rationale.get(
                "away_lineup",
                {},
            ),

        "adjustment":
            rationale.get(
                "adjustment"
            ),

        "analysis_rows":
            rationale.get(
                "market_analysis",
                [],
            ),

        "method":
            rationale.get(
                "method",
                "",
            ),

        "odds":
            best_odd(
                prediction
            ),

        "conclusion":
            conclusion(
                prediction
            ),
    }
