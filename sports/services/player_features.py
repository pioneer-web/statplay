from statistics import median

from sports.models import (
    EventLineupPlayer,
    Player,
    PlayerMatchStats,
)


def clamp(
    value,
    minimum,
    maximum,
):
    return max(
        minimum,
        min(maximum, value),
    )


def defensive_position(position):
    value = str(
        position or ""
    ).upper()

    return value in (
        "G",
        "GK",
        "D",
        "DF",
        "CB",
        "LB",
        "RB",
        "LWB",
        "RWB",
    )


def player_form(
    player,
    before,
    team,
    limit=12,
):
    rows = list(
        PlayerMatchStats.objects
        .filter(
            player=player,
            team=team,
            event__starts_at__lt=before,
            event__status="finished",
        )
        .select_related("event")
        .order_by(
            "-event__starts_at"
        )[:limit]
    )

    usable = [
        row
        for row in rows
        if row.minutes
        and row.minutes > 0
    ]

    if not usable:
        return None

    minutes = sum(
        row.minutes
        for row in usable
    )

    if minutes < 90:
        return None

    goals = sum(
        row.goals or 0
        for row in usable
    )

    assists = sum(
        row.assists or 0
        for row in usable
    )

    xg = sum(
        float(row.xg or 0)
        for row in usable
    )

    shots_target = sum(
        row.shots_on_target or 0
        for row in usable
    )

    per90 = 90 / minutes

    goals90 = goals * per90
    assists90 = assists * per90
    xg90 = xg * per90
    sot90 = shots_target * per90

    attack_score = (
        goals90 * 0.45
        + xg90 * 0.35
        + sot90 * 0.12
        + assists90 * 0.08
    )

    conceded_values = [
        row.team_goals_conceded
        for row in usable
        if (
            row.team_goals_conceded
            is not None
        )
    ]

    conceded = None

    if conceded_values:
        conceded = (
            sum(conceded_values)
            / len(conceded_values)
        )

    return {
        "minutes": minutes,
        "matches": len(usable),
        "goals90": goals90,
        "xg90": xg90,
        "shots_target90": sot90,
        "assists90": assists90,
        "attack_score": attack_score,
        "conceded": conceded,
    }


def team_lineup_adjustment(
    event,
    team,
):
    lineup = list(
        EventLineupPlayer.objects
        .filter(
            event=event,
            team=team,
            starter=True,
        )
        .select_related("player")
    )

    if len(lineup) < 8:
        return {
            "available": False,
            "confirmed": False,
            "starters": len(lineup),
            "attack_factor": 1.0,
            "defense_factor": 1.0,
        }

    confirmed = any(
        row.confirmed
        for row in lineup
    )

    recent_player_ids = (
        PlayerMatchStats.objects
        .filter(
            team=team,
            event__starts_at__lt=(
                event.starts_at
            ),
            event__status="finished",
        )
        .values_list(
            "player_id",
            flat=True,
        )
        .distinct()
    )

    roster = list(
        Player.objects.filter(
            id__in=recent_player_ids
        )
    )

    cache = {}

    def form(player):
        if player.id not in cache:
            cache[player.id] = (
                player_form(
                    player,
                    event.starts_at,
                    team,
                )
            )

        return cache[player.id]

    lineup_forms = []

    for entry in lineup:
        data = form(
            entry.player
        )

        if data:
            lineup_forms.append(
                (
                    entry.player,
                    data,
                )
            )

    roster_forms = []

    for player in roster:
        data = form(player)

        if data:
            roster_forms.append(
                (
                    player,
                    data,
                )
            )

    attack_factor = 1.0

    if (
        len(lineup_forms) >= 6
        and len(roster_forms) >= 8
    ):
        current_attack = sum(
            sorted(
                (
                    data[
                        "attack_score"
                    ]
                    for _, data
                    in lineup_forms
                ),
                reverse=True,
            )[:5]
        )

        baseline_attack = sum(
            sorted(
                (
                    data[
                        "attack_score"
                    ]
                    for _, data
                    in roster_forms
                ),
                reverse=True,
            )[:5]
        )

        if baseline_attack > 0.05:
            raw = (
                current_attack
                / baseline_attack
            )

            if confirmed:
                attack_factor = clamp(
                    raw,
                    0.88,
                    1.12,
                )
            else:
                attack_factor = clamp(
                    raw,
                    0.94,
                    1.06,
                )

    current_defense = []

    for entry in lineup:
        if not defensive_position(
            entry.position
            or entry.player.position
        ):
            continue

        data = form(
            entry.player
        )

        if (
            data
            and data["conceded"]
            is not None
            and data["matches"] >= 3
        ):
            current_defense.append(
                data["conceded"]
            )

    roster_defense = []

    for player, data in roster_forms:
        if not defensive_position(
            player.position
        ):
            continue

        if (
            data["conceded"]
            is not None
            and data["matches"] >= 3
        ):
            roster_defense.append(
                data["conceded"]
            )

    defense_factor = 1.0

    if (
        len(current_defense) >= 3
        and len(roster_defense) >= 4
    ):
        current_vulnerability = (
            median(
                current_defense
            )
        )

        baseline_vulnerability = (
            median(
                roster_defense
            )
        )

        if baseline_vulnerability > 0:
            raw = (
                current_vulnerability
                / baseline_vulnerability
            )

            if confirmed:
                defense_factor = clamp(
                    raw,
                    0.90,
                    1.10,
                )
            else:
                defense_factor = clamp(
                    raw,
                    0.95,
                    1.05,
                )

    return {
        "available": True,
        "confirmed": confirmed,
        "starters": len(lineup),
        "attack_factor": round(
            attack_factor,
            4,
        ),
        "defense_factor": round(
            defense_factor,
            4,
        ),
    }
