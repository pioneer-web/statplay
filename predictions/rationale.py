from sports.models import (
    EventLineupPlayer,
)
from sports.services.features import (
    team_recent_features,
)
from sports.services.player_features import (
    defensive_position,
    player_form,
)


def _round(
    value,
    digits=2,
):
    if value is None:
        return None

    return round(
        float(value),
        digits,
    )


def team_summary(
    team,
    event,
    limit=10,
):
    data = team_recent_features(
        team,
        before=event.starts_at,
        limit=limit,
    )

    return {
        "team": team.name,
        "matches": data.get(
            "matches",
            0,
        ),
        "goals_for": _round(
            data.get(
                "goals_for"
            )
        ),
        "goals_against": _round(
            data.get(
                "goals_against"
            )
        ),
        "xg": _round(
            data.get("xg_for")
        ),
        "xg_against": _round(
            data.get(
                "xg_against"
            )
        ),
        "shots": _round(
            data.get("shots_for")
        ),
        "shots_on_target": _round(
            data.get(
                "shots_target_for"
            )
        ),
        "corners": _round(
            data.get(
                "corners_for"
            )
        ),
        "corners_against": _round(
            data.get(
                "corners_against"
            )
        ),
        "cards": _round(
            data.get(
                "cards_for"
            )
        ),
        "cards_against": _round(
            data.get(
                "cards_against"
            )
        ),
        "possession": _round(
            data.get(
                "possession"
            )
        ),
    }


def lineup_snapshot(
    event,
    team,
):
    entries = list(
        EventLineupPlayer.objects
        .filter(
            event=event,
            team=team,
            starter=True,
        )
        .select_related(
            "player"
        )
        .order_by(
            "player__name"
        )
    )

    if not entries:
        return {
            "available": False,
            "confirmed": False,
            "status": (
                "Não disponível"
            ),
            "starters": [],
            "attackers": [],
            "defenders": [],
        }

    confirmed = all(
        row.confirmed
        for row in entries
    )

    starters = []
    attackers = []
    defenders = []

    for entry in entries:
        player = entry.player

        position = (
            entry.position
            or player.position
            or "—"
        )

        data = player_form(
            player,
            event.starts_at,
            team,
        )

        item = {
            "name": player.name,
            "position": position,
        }

        if data:
            item.update({
                "goals90": _round(
                    data.get(
                        "goals90"
                    )
                ),
                "xg90": _round(
                    data.get(
                        "xg90"
                    )
                ),
                "shots_target90":
                    _round(
                        data.get(
                            "shots_target90"
                        )
                    ),
                "attack_score":
                    _round(
                        data.get(
                            "attack_score"
                        ),
                        3,
                    ),
                "conceded":
                    _round(
                        data.get(
                            "conceded"
                        )
                    ),
            })

        starters.append({
            "name": player.name,
            "position": position,
        })

        if (
            data
            and data.get(
                "attack_score",
                0,
            ) > 0
        ):
            attackers.append(
                item
            )

        if defensive_position(
            position
        ):
            defenders.append(
                item
            )

    attackers.sort(
        key=lambda item:
            item.get(
                "attack_score"
            )
            or 0,
        reverse=True,
    )

    defenders.sort(
        key=lambda item:
            item["name"]
    )

    return {
        "available": True,
        "confirmed": confirmed,
        "status": (
            "Confirmada"
            if confirmed
            else "Provável"
        ),
        "starters": starters,
        "attackers":
            attackers[:4],
        "defenders":
            defenders,
    }


def build_rationale(
    event,
    context_data,
):
    home = context_data.get(
        "home",
        {},
    )

    away = context_data.get(
        "away",
        {},
    )

    return {
        "sample_size": 10,

        "home_form":
            team_summary(
                event.home_team,
                event,
            ),

        "away_form":
            team_summary(
                event.away_team,
                event,
            ),

        "home_lineup":
            lineup_snapshot(
                event,
                event.home_team,
            ),

        "away_lineup":
            lineup_snapshot(
                event,
                event.away_team,
            ),

        "adjustment": {
            "base_home":
                context_data.get(
                    "base_home_goals"
                ),

            "base_away":
                context_data.get(
                    "base_away_goals"
                ),

            "adjusted_home":
                context_data.get(
                    "adjusted_home_goals"
                ),

            "adjusted_away":
                context_data.get(
                    "adjusted_away_goals"
                ),

            "home_attack":
                _round(
                    home.get(
                        "attack_factor",
                        1,
                    ),
                    4,
                ),

            "away_attack":
                _round(
                    away.get(
                        "attack_factor",
                        1,
                    ),
                    4,
                ),

            "home_defense":
                _round(
                    home.get(
                        "defense_factor",
                        1,
                    ),
                    4,
                ),

            "away_defense":
                _round(
                    away.get(
                        "defense_factor",
                        1,
                    ),
                    4,
                ),

            "home_confirmed":
                bool(
                    home.get(
                        "confirmed",
                        False,
                    )
                ),

            "away_confirmed":
                bool(
                    away.get(
                        "confirmed",
                        False,
                    )
                ),
        },
    }
