import math

from sports.services.features import (
    team_recent_features,
)


def _blend(a, b):
    if a is None and b is None:
        return None

    if a is None:
        return float(b)

    if b is None:
        return float(a)

    return (
        float(a) + float(b)
    ) / 2


def _clamp(value, minimum, maximum):
    return max(
        minimum,
        min(maximum, value),
    )


def _poisson_probability(
    expected,
    goals,
):
    return (
        math.exp(-expected)
        * expected ** goals
        / math.factorial(goals)
    )


def poisson_over(
    expected,
    line,
):
    threshold = int(
        math.floor(line)
    ) + 1

    under_probability = sum(
        _poisson_probability(
            expected,
            value,
        )
        for value in range(threshold)
    )

    return _clamp(
        1 - under_probability,
        0,
        1,
    )


def btts_probability(
    home_expected,
    away_expected,
):
    home_zero = math.exp(
        -home_expected
    )

    away_zero = math.exp(
        -away_expected
    )

    both_zero = math.exp(
        -(
            home_expected
            + away_expected
        )
    )

    return _clamp(
        1
        - home_zero
        - away_zero
        + both_zero,
        0,
        1,
    )


def outcome_probabilities(
    home_expected,
    away_expected,
):
    home = 0.0
    draw = 0.0
    away = 0.0

    for home_goals in range(11):
        ph = _poisson_probability(
            home_expected,
            home_goals,
        )

        for away_goals in range(11):
            pa = _poisson_probability(
                away_expected,
                away_goals,
            )

            probability = ph * pa

            if home_goals > away_goals:
                home += probability
            elif home_goals == away_goals:
                draw += probability
            else:
                away += probability

    total = home + draw + away

    if total:
        home /= total
        draw /= total
        away /= total

    return {
        "home": home,
        "draw": draw,
        "away": away,
    }


def _market(
    code,
    label,
    probability,
    confidence,
    expected=None,
):
    probability = _clamp(
        probability * 100,
        1,
        99,
    )

    fair_odd = (
        100 / probability
        if probability
        else None
    )

    return {
        "code": code,
        "label": label,
        "probability": round(
            probability,
            2,
        ),
        "fair_odd": round(
            fair_odd,
            3,
        ),
        "confidence": round(
            confidence,
            2,
        ),
        "expected": (
            round(expected, 2)
            if expected is not None
            else None
        ),
    }


def evaluate_event(
    event,
    sample=10,
    min_matches=5,
):
    home = team_recent_features(
        event.home_team,
        before=event.starts_at,
        limit=sample,
    )

    away = team_recent_features(
        event.away_team,
        before=event.starts_at,
        limit=sample,
    )

    if (
        home["matches"] < min_matches
        or away["matches"] < min_matches
    ):
        return None

    home_goal_base = _blend(
        home["goals_for"],
        away["goals_against"],
    )

    away_goal_base = _blend(
        away["goals_for"],
        home["goals_against"],
    )

    if (
        home_goal_base is None
        or away_goal_base is None
    ):
        return None

    #
    # Ajuste inicial por mando.
    # Depois será calibrado pelo backtest.
    #
    home_goals = _clamp(
        home_goal_base * 1.08,
        0.20,
        4.50,
    )

    away_goals = _clamp(
        away_goal_base * 0.92,
        0.20,
        4.50,
    )

    expected_goals = (
        home_goals
        + away_goals
    )

    confidence = min(
        90.0,
        40.0
        + min(
            home["matches"],
            away["matches"],
        ) * 5,
    )

    markets = []

    outcomes = outcome_probabilities(
        home_goals,
        away_goals,
    )

    markets.extend([
        _market(
            "home_win",
            "Vitória mandante",
            outcomes["home"],
            confidence,
        ),
        _market(
            "draw",
            "Empate",
            outcomes["draw"],
            confidence,
        ),
        _market(
            "away_win",
            "Vitória visitante",
            outcomes["away"],
            confidence,
        ),
        _market(
            "goals_over_1_5",
            "Mais de 1.5 gols",
            poisson_over(
                expected_goals,
                1.5,
            ),
            confidence,
            expected_goals,
        ),
        _market(
            "goals_over_2_5",
            "Mais de 2.5 gols",
            poisson_over(
                expected_goals,
                2.5,
            ),
            confidence,
            expected_goals,
        ),
        _market(
            "btts_yes",
            "Ambas marcam",
            btts_probability(
                home_goals,
                away_goals,
            ),
            confidence,
            expected_goals,
        ),
    ])

    home_corners = _blend(
        home["corners_for"],
        away["corners_against"],
    )

    away_corners = _blend(
        away["corners_for"],
        home["corners_against"],
    )

    if (
        home_corners is not None
        and away_corners is not None
    ):
        expected_corners = (
            home_corners
            + away_corners
        )

        corner_confidence = min(
            confidence,
            40
            + min(
                home["corners_samples"],
                away["corners_samples"],
            ) * 5,
        )

        for line in (
            7.5,
            8.5,
            9.5,
            10.5,
        ):
            markets.append(
                _market(
                    f"corners_over_{str(line).replace('.', '_')}",
                    f"Mais de {line} escanteios",
                    poisson_over(
                        expected_corners,
                        line,
                    ),
                    corner_confidence,
                    expected_corners,
                )
            )

    home_cards = _blend(
        home["cards_for"],
        away["cards_against"],
    )

    away_cards = _blend(
        away["cards_for"],
        home["cards_against"],
    )

    if (
        home_cards is not None
        and away_cards is not None
    ):
        expected_cards = (
            home_cards
            + away_cards
        )

        card_confidence = min(
            confidence,
            40
            + min(
                home["cards_samples"],
                away["cards_samples"],
            ) * 5,
        )

        for line in (
            2.5,
            3.5,
            4.5,
            5.5,
        ):
            markets.append(
                _market(
                    f"cards_over_{str(line).replace('.', '_')}",
                    f"Mais de {line} cartões",
                    poisson_over(
                        expected_cards,
                        line,
                    ),
                    card_confidence,
                    expected_cards,
                )
            )

    return {
        "event_id": event.id,
        "external_id": event.external_id,
        "home": event.home_team.name,
        "away": event.away_team.name,
        "home_sample": home["matches"],
        "away_sample": away["matches"],
        "expected_home_goals": round(
            home_goals,
            2,
        ),
        "expected_away_goals": round(
            away_goals,
            2,
        ),
        "markets": sorted(
            markets,
            key=lambda item: (
                item["probability"]
            ),
            reverse=True,
        ),
    }
