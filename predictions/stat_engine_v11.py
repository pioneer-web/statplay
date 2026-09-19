import math

from predictions.stat_engine import (
    evaluate_event as evaluate_base,
)
from sports.services.features import (
    team_recent_features,
)
from sports.services.player_features import (
    team_lineup_adjustment,
)


def poisson_probability(
    goals,
    expected,
):
    return (
        math.exp(-expected)
        * expected ** goals
        / math.factorial(goals)
    )


def over_probability(
    expected,
    line,
):
    maximum_under = int(
        math.floor(line)
    )

    under = sum(
        poisson_probability(
            goals,
            expected,
        )
        for goals in range(
            maximum_under + 1
        )
    )

    return (
        1 - under
    ) * 100


def btts_probability(
    home_expected,
    away_expected,
):
    home_scores = (
        1
        - math.exp(
            -home_expected
        )
    )

    away_scores = (
        1
        - math.exp(
            -away_expected
        )
    )

    return (
        home_scores
        * away_scores
        * 100
    )


def outcome_probabilities(
    home_expected,
    away_expected,
):
    home_win = 0.0
    draw = 0.0
    away_win = 0.0

    for home_goals in range(13):
        ph = poisson_probability(
            home_goals,
            home_expected,
        )

        for away_goals in range(13):
            pa = poisson_probability(
                away_goals,
                away_expected,
            )

            value = ph * pa

            if home_goals > away_goals:
                home_win += value

            elif home_goals == away_goals:
                draw += value

            else:
                away_win += value

    total = (
        home_win
        + draw
        + away_win
    )

    if total:
        home_win /= total
        draw /= total
        away_win /= total

    return {
        "home_win": home_win * 100,
        "draw": draw * 100,
        "away_win": away_win * 100,
    }


def evaluate_event(
    event,
    sample=10,
    min_matches=5,
):
    base = evaluate_base(
        event,
        sample=sample,
        min_matches=min_matches,
    )

    if not base:
        return None

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

    if not home or not away:
        return base

    try:
        base_home = (
            (
                float(
                    home["goals_for"]
                )
                + float(
                    away[
                        "goals_against"
                    ]
                )
            )
            / 2
        ) * 1.08

        base_away = (
            (
                float(
                    away["goals_for"]
                )
                + float(
                    home[
                        "goals_against"
                    ]
                )
            )
            / 2
        ) * 0.92

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return base

    home_lineup = (
        team_lineup_adjustment(
            event,
            event.home_team,
        )
    )

    away_lineup = (
        team_lineup_adjustment(
            event,
            event.away_team,
        )
    )

    adjusted_home = (
        base_home
        * home_lineup[
            "attack_factor"
        ]
        * away_lineup[
            "defense_factor"
        ]
    )

    adjusted_away = (
        base_away
        * away_lineup[
            "attack_factor"
        ]
        * home_lineup[
            "defense_factor"
        ]
    )

    adjusted_home = max(
        0.15,
        min(4.0, adjusted_home),
    )

    adjusted_away = max(
        0.15,
        min(4.0, adjusted_away),
    )

    total_expected = (
        adjusted_home
        + adjusted_away
    )

    outcomes = (
        outcome_probabilities(
            adjusted_home,
            adjusted_away,
        )
    )

    probabilities = {
        "home_win": (
            outcomes["home_win"]
        ),
        "draw": (
            outcomes["draw"]
        ),
        "away_win": (
            outcomes["away_win"]
        ),
        "goals_over_1_5": (
            over_probability(
                total_expected,
                1.5,
            )
        ),
        "goals_over_2_5": (
            over_probability(
                total_expected,
                2.5,
            )
        ),
        "btts_yes": (
            btts_probability(
                adjusted_home,
                adjusted_away,
            )
        ),
    }

    both_confirmed = (
        home_lineup["confirmed"]
        and away_lineup["confirmed"]
    )

    both_available = (
        home_lineup["available"]
        and away_lineup["available"]
    )

    confidence_bonus = 0

    if both_confirmed:
        confidence_bonus = 4

    elif both_available:
        confidence_bonus = 1

    for item in base.get(
        "markets",
        [],
    ):
        code = item.get("code")

        if code not in probabilities:
            continue

        probability = round(
            probabilities[code],
            1,
        )

        item["probability"] = (
            probability
        )

        item["fair_odd"] = (
            round(
                100 / probability,
                3,
            )
            if probability > 0
            else None
        )

        try:
            confidence = float(
                item.get(
                    "confidence",
                    0,
                )
            )

            item["confidence"] = min(
                100,
                round(
                    confidence
                    + confidence_bonus,
                    1,
                ),
            )

        except Exception:
            pass

    base[
        "engine_version"
    ] = "1.1.0"

    base[
        "player_adjustment"
    ] = {
        "home": home_lineup,
        "away": away_lineup,

        "base_home_goals": round(
            base_home,
            3,
        ),
        "base_away_goals": round(
            base_away,
            3,
        ),

        "adjusted_home_goals": round(
            adjusted_home,
            3,
        ),
        "adjusted_away_goals": round(
            adjusted_away,
            3,
        ),
    }

    return base
