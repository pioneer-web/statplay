import math


from sports.services.features import (
    team_recent_features,
)
from sports.services.player_features import (
    team_lineup_adjustment,
)


ENGINE_VERSION = "2.0.0"


def clamp(value, minimum, maximum):
    return max(
        minimum,
        min(maximum, value),
    )


def average(*values):
    clean = [
        float(v)
        for v in values
        if v is not None
    ]

    if not clean:
        return None

    return sum(clean) / len(clean)


def blend_goals_xg(goals, xg):
    if goals is not None and xg is not None:
        return (
            float(goals) * 0.45
            + float(xg) * 0.55
        )

    if xg is not None:
        return float(xg)

    if goals is not None:
        return float(goals)

    return None


def poisson(goal_count, expected):
    return (
        math.exp(-expected)
        * expected ** goal_count
        / math.factorial(goal_count)
    )


def dixon_coles_tau(
    home_goals,
    away_goals,
    home_expected,
    away_expected,
    rho=-0.08,
):
    if home_goals == 0 and away_goals == 0:
        return (
            1
            - home_expected
            * away_expected
            * rho
        )

    if home_goals == 0 and away_goals == 1:
        return (
            1
            + home_expected
            * rho
        )

    if home_goals == 1 and away_goals == 0:
        return (
            1
            + away_expected
            * rho
        )

    if home_goals == 1 and away_goals == 1:
        return 1 - rho

    return 1.0


def score_matrix(
    home_expected,
    away_expected,
    max_goals=8,
):
    matrix = {}
    total = 0.0

    for home in range(max_goals + 1):
        for away in range(max_goals + 1):
            probability = (
                poisson(
                    home,
                    home_expected,
                )
                * poisson(
                    away,
                    away_expected,
                )
                * dixon_coles_tau(
                    home,
                    away,
                    home_expected,
                    away_expected,
                )
            )

            probability = max(
                0,
                probability,
            )

            matrix[
                (home, away)
            ] = probability

            total += probability

    if total:
        for key in matrix:
            matrix[key] /= total

    return matrix


def poisson_over(
    expected,
    line,
):
    maximum = int(
        math.floor(line)
    )

    under = sum(
        poisson(goals, expected)
        for goals in range(
            maximum + 1
        )
    )

    return clamp(
        (1 - under) * 100,
        0.5,
        99.5,
    )


def fair_odd(probability):
    if probability <= 0:
        return None

    return round(
        100 / probability,
        3,
    )


def pct(value):
    return round(
        clamp(
            value,
            0.5,
            99.5,
        ),
        1,
    )


def add_market(
    markets,
    code,
    name,
    category,
    probability,
    confidence,
    line=None,
    method="",
    analysis=None,
):
    probability = pct(
        probability
    )

    markets.append({
        "code": code,
        "name": name,
        "category": category,
        "line": line,
        "probability": probability,
        "confidence": round(
            confidence,
            1,
        ),
        "fair_odd": (
            fair_odd(
                probability
            )
        ),
        "method": method,
        "analysis_rows": (
            analysis or []
        ),
    })


def goals_engine(
    home,
    away,
    home_lineup,
    away_lineup,
):
    home_attack = blend_goals_xg(
        home.get("goals_for"),
        home.get("xg_for"),
    )

    away_defence = blend_goals_xg(
        away.get("goals_against"),
        away.get("xg_against"),
    )

    away_attack = blend_goals_xg(
        away.get("goals_for"),
        away.get("xg_for"),
    )

    home_defence = blend_goals_xg(
        home.get("goals_against"),
        home.get("xg_against"),
    )

    if (
        home_attack is None
        or away_defence is None
        or away_attack is None
        or home_defence is None
    ):
        return None

    home_expected = (
        average(
            home_attack,
            away_defence,
        )
        * 1.07
    )

    away_expected = (
        average(
            away_attack,
            home_defence,
        )
        * 0.93
    )

    home_sot = average(
        home.get(
            "shots_target_for"
        ),
        away.get(
            "shots_target_against"
        ),
    )

    away_sot = average(
        away.get(
            "shots_target_for"
        ),
        home.get(
            "shots_target_against"
        ),
    )

    if home_sot is not None:
        home_expected *= (
            1
            + clamp(
                (
                    home_sot
                    - 4.5
                )
                * 0.015,
                -0.06,
                0.06,
            )
        )

    if away_sot is not None:
        away_expected *= (
            1
            + clamp(
                (
                    away_sot
                    - 4.5
                )
                * 0.015,
                -0.06,
                0.06,
            )
        )

    base_home = home_expected
    base_away = away_expected

    home_expected *= (
        home_lineup[
            "attack_factor"
        ]
        * away_lineup[
            "defense_factor"
        ]
    )

    away_expected *= (
        away_lineup[
            "attack_factor"
        ]
        * home_lineup[
            "defense_factor"
        ]
    )

    home_expected = clamp(
        home_expected,
        0.15,
        4.0,
    )

    away_expected = clamp(
        away_expected,
        0.15,
        4.0,
    )

    matrix = score_matrix(
        home_expected,
        away_expected,
    )

    home_win = sum(
        probability
        for (hg, ag), probability
        in matrix.items()
        if hg > ag
    ) * 100

    draw = sum(
        probability
        for (hg, ag), probability
        in matrix.items()
        if hg == ag
    ) * 100

    away_win = sum(
        probability
        for (hg, ag), probability
        in matrix.items()
        if hg < ag
    ) * 100

    btts = sum(
        probability
        for (hg, ag), probability
        in matrix.items()
        if hg > 0 and ag > 0
    ) * 100

    total_expected = (
        home_expected
        + away_expected
    )

    sample = min(
        home.get("matches", 0),
        away.get("matches", 0),
    )

    confidence = (
        45
        + min(sample, 10) * 3.5
    )

    if (
        home.get(
            "xg_samples",
            0,
        ) >= 5
        and away.get(
            "xg_samples",
            0,
        ) >= 5
    ):
        confidence += 5

    if (
        home_lineup["available"]
        and away_lineup[
            "available"
        ]
    ):
        confidence += 2

    if (
        home_lineup["confirmed"]
        and away_lineup[
            "confirmed"
        ]
    ):
        confidence += 3

    confidence = clamp(
        confidence,
        45,
        92,
    )

    analysis = [
        {
            "label":
                "Gols esperados - mandante",
            "value":
                round(
                    home_expected,
                    2,
                ),
        },
        {
            "label":
                "Gols esperados - visitante",
            "value":
                round(
                    away_expected,
                    2,
                ),
        },
        {
            "label":
                "Gols esperados - total",
            "value":
                round(
                    total_expected,
                    2,
                ),
        },
        {
            "label":
                "Gols médios mandante",
            "value":
                round(
                    home.get(
                        "goals_for"
                    )
                    or 0,
                    2,
                ),
        },
        {
            "label":
                "xG médio mandante",
            "value":
                round(
                    home.get(
                        "xg_for"
                    )
                    or 0,
                    2,
                ),
        },
        {
            "label":
                "Gols sofridos visitante",
            "value":
                round(
                    away.get(
                        "goals_against"
                    )
                    or 0,
                    2,
                ),
        },
        {
            "label":
                "xGA visitante",
            "value":
                round(
                    away.get(
                        "xg_against"
                    )
                    or 0,
                    2,
                ),
        },
        {
            "label":
                "Fator ataque mandante",
            "value":
                home_lineup[
                    "attack_factor"
                ],
        },
        {
            "label":
                "Fator defesa visitante",
            "value":
                away_lineup[
                    "defense_factor"
                ],
        },
    ]

    return {
        "home_expected":
            home_expected,

        "away_expected":
            away_expected,

        "base_home":
            base_home,

        "base_away":
            base_away,

        "home_win":
            home_win,

        "draw":
            draw,

        "away_win":
            away_win,

        "btts":
            btts,

        "total_expected":
            total_expected,

        "confidence":
            confidence,

        "analysis":
            analysis,
    }


def corners_engine(
    home,
    away,
):
    home_expected = average(
        home.get(
            "corners_for"
        ),
        away.get(
            "corners_against"
        ),
    )

    away_expected = average(
        away.get(
            "corners_for"
        ),
        home.get(
            "corners_against"
        ),
    )

    if (
        home_expected is None
        or away_expected is None
    ):
        return None

    home_shots = average(
        home.get(
            "shots_for"
        ),
        away.get(
            "shots_against"
        ),
    )

    away_shots = average(
        away.get(
            "shots_for"
        ),
        home.get(
            "shots_against"
        ),
    )

    if home_shots is not None:
        home_expected *= (
            1
            + clamp(
                (
                    home_shots
                    - 12
                )
                * 0.006,
                -0.04,
                0.04,
            )
        )

    if away_shots is not None:
        away_expected *= (
            1
            + clamp(
                (
                    away_shots
                    - 12
                )
                * 0.006,
                -0.04,
                0.04,
            )
        )

    total_expected = clamp(
        home_expected
        + away_expected,
        3,
        18,
    )

    samples = min(
        home.get(
            "corners_samples",
            0,
        ),
        away.get(
            "corners_samples",
            0,
        ),
    )

    confidence = clamp(
        45
        + min(
            samples,
            10,
        ) * 4,
        45,
        85,
    )

    return {
        "expected":
            total_expected,

        "confidence":
            confidence,

        "analysis": [
            {
                "label":
                    "Escanteios esperados",
                "value":
                    round(
                        total_expected,
                        2,
                    ),
            },
            {
                "label":
                    "Mandante - escanteios feitos",
                "value":
                    round(
                        home.get(
                            "corners_for"
                        )
                        or 0,
                        2,
                    ),
            },
            {
                "label":
                    "Mandante - escanteios cedidos",
                "value":
                    round(
                        home.get(
                            "corners_against"
                        )
                        or 0,
                        2,
                    ),
            },
            {
                "label":
                    "Visitante - escanteios feitos",
                "value":
                    round(
                        away.get(
                            "corners_for"
                        )
                        or 0,
                        2,
                    ),
            },
            {
                "label":
                    "Visitante - escanteios cedidos",
                "value":
                    round(
                        away.get(
                            "corners_against"
                        )
                        or 0,
                        2,
                    ),
            },
        ],
    }


def cards_engine(
    home,
    away,
):
    home_expected = average(
        home.get(
            "cards_for"
        ),
        away.get(
            "cards_against"
        ),
    )

    away_expected = average(
        away.get(
            "cards_for"
        ),
        home.get(
            "cards_against"
        ),
    )

    if (
        home_expected is None
        or away_expected is None
    ):
        return None

    total_expected = clamp(
        home_expected
        + away_expected,
        0.5,
        10,
    )

    samples = min(
        home.get(
            "cards_samples",
            0,
        ),
        away.get(
            "cards_samples",
            0,
        ),
    )

    confidence = clamp(
        42
        + min(
            samples,
            10,
        ) * 4,
        42,
        82,
    )

    return {
        "expected":
            total_expected,

        "confidence":
            confidence,

        "analysis": [
            {
                "label":
                    "Cartões esperados",
                "value":
                    round(
                        total_expected,
                        2,
                    ),
            },
            {
                "label":
                    "Mandante - cartões",
                "value":
                    round(
                        home.get(
                            "cards_for"
                        )
                        or 0,
                        2,
                    ),
            },
            {
                "label":
                    "Mandante - cartões cedidos",
                "value":
                    round(
                        home.get(
                            "cards_against"
                        )
                        or 0,
                        2,
                    ),
            },
            {
                "label":
                    "Visitante - cartões",
                "value":
                    round(
                        away.get(
                            "cards_for"
                        )
                        or 0,
                        2,
                    ),
            },
            {
                "label":
                    "Visitante - cartões cedidos",
                "value":
                    round(
                        away.get(
                            "cards_against"
                        )
                        or 0,
                        2,
                    ),
            },
        ],
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
        home.get("matches", 0)
        < min_matches
        or away.get("matches", 0)
        < min_matches
    ):
        return None

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

    markets = []

    goals = goals_engine(
        home,
        away,
        home_lineup,
        away_lineup,
    )

    if goals:
        method = (
            "xG + gols + força ofensiva/defensiva "
            "+ chutes no alvo + mando + escalação "
            "+ Poisson/Dixon-Coles"
        )

        analysis = goals[
            "analysis"
        ]

        confidence = goals[
            "confidence"
        ]

        add_market(
            markets,
            "home_win",
            "Vitória mandante",
            "result",
            goals["home_win"],
            confidence,
            method=method,
            analysis=analysis,
        )

        add_market(
            markets,
            "draw",
            "Empate",
            "result",
            goals["draw"],
            confidence,
            method=method,
            analysis=analysis,
        )

        add_market(
            markets,
            "away_win",
            "Vitória visitante",
            "result",
            goals["away_win"],
            confidence,
            method=method,
            analysis=analysis,
        )

        add_market(
            markets,
            "double_home_draw",
            "Mandante ou empate",
            "double_chance",
            (
                goals["home_win"]
                + goals["draw"]
            ),
            confidence,
            method=method,
            analysis=analysis,
        )

        add_market(
            markets,
            "double_away_draw",
            "Visitante ou empate",
            "double_chance",
            (
                goals["away_win"]
                + goals["draw"]
            ),
            confidence,
            method=method,
            analysis=analysis,
        )

        add_market(
            markets,
            "double_home_away",
            "Mandante ou visitante",
            "double_chance",
            (
                goals["home_win"]
                + goals["away_win"]
            ),
            confidence,
            method=method,
            analysis=analysis,
        )

        for line in (
            1.5,
            2.5,
            3.5,
        ):
            over = poisson_over(
                goals[
                    "total_expected"
                ],
                line,
            )

            under = 100 - over

            code_line = (
                str(line)
                .replace(
                    ".",
                    "_",
                )
            )

            add_market(
                markets,
                f"goals_over_{code_line}",
                f"Mais de {line} gols",
                "goals",
                over,
                confidence,
                line=line,
                method=method,
                analysis=analysis,
            )

            add_market(
                markets,
                f"goals_under_{code_line}",
                f"Menos de {line} gols",
                "goals",
                under,
                confidence,
                line=line,
                method=method,
                analysis=analysis,
            )

        add_market(
            markets,
            "btts_yes",
            "Ambas marcam - Sim",
            "goals",
            goals["btts"],
            confidence,
            method=method,
            analysis=analysis,
        )

        add_market(
            markets,
            "btts_no",
            "Ambas marcam - Não",
            "goals",
            (
                100
                - goals["btts"]
            ),
            confidence,
            method=method,
            analysis=analysis,
        )

    corners = corners_engine(
        home,
        away,
    )

    if corners:
        method = (
            "escanteios feitos/cedidos "
            "+ volume recente de finalizações "
            "+ distribuição de contagem"
        )

        for line in (
            7.5,
            8.5,
            9.5,
            10.5,
        ):
            over = poisson_over(
                corners[
                    "expected"
                ],
                line,
            )

            under = 100 - over

            code_line = (
                str(line)
                .replace(
                    ".",
                    "_",
                )
            )

            add_market(
                markets,
                f"corners_over_{code_line}",
                f"Mais de {line} escanteios",
                "corners",
                over,
                corners["confidence"],
                line=line,
                method=method,
                analysis=corners[
                    "analysis"
                ],
            )

            add_market(
                markets,
                f"corners_under_{code_line}",
                f"Menos de {line} escanteios",
                "corners",
                under,
                corners["confidence"],
                line=line,
                method=method,
                analysis=corners[
                    "analysis"
                ],
            )

    cards = cards_engine(
        home,
        away,
    )

    if cards:
        method = (
            "cartões feitos/cedidos "
            "+ comportamento recente das equipes "
            "+ distribuição de contagem"
        )

        for line in (
            2.5,
            3.5,
            4.5,
            5.5,
        ):
            over = poisson_over(
                cards[
                    "expected"
                ],
                line,
            )

            under = 100 - over

            code_line = (
                str(line)
                .replace(
                    ".",
                    "_",
                )
            )

            add_market(
                markets,
                f"cards_over_{code_line}",
                f"Mais de {line} cartões",
                "cards",
                over,
                cards["confidence"],
                line=line,
                method=method,
                analysis=cards[
                    "analysis"
                ],
            )

            add_market(
                markets,
                f"cards_under_{code_line}",
                f"Menos de {line} cartões",
                "cards",
                under,
                cards["confidence"],
                line=line,
                method=method,
                analysis=cards[
                    "analysis"
                ],
            )

    return {
        "engine_version":
            ENGINE_VERSION,

        "markets":
            markets,

        "player_adjustment": {
            "home":
                home_lineup,

            "away":
                away_lineup,

            "base_home_goals": (
                goals[
                    "base_home"
                ]
                if goals
                else None
            ),

            "base_away_goals": (
                goals[
                    "base_away"
                ]
                if goals
                else None
            ),

            "adjusted_home_goals": (
                goals[
                    "home_expected"
                ]
                if goals
                else None
            ),

            "adjusted_away_goals": (
                goals[
                    "away_expected"
                ]
                if goals
                else None
            ),
        },
    }
