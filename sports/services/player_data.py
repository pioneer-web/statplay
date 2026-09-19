from decimal import Decimal, InvalidOperation

from sports.models import (
    EventLineupPlayer,
    Player,
    PlayerMatchStats,
)


def _int(value):
    if value is None:
        return None

    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _decimal(value):
    if value is None:
        return None

    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _rows(side_payload):
    result = []
    seen = set()

    for key in (
        "players",
        "substitutes",
    ):
        for row in side_payload.get(
            key,
            [],
        ):
            player_data = (
                row.get("player")
                or row
            )

            player_id = player_data.get(
                "id"
            )

            if (
                not player_id
                or player_id in seen
            ):
                continue

            seen.add(player_id)
            result.append(row)

    return result


def _player_from_row(
    row,
    team,
    sport,
):
    raw = (
        row.get("player")
        or row
    )

    external_id = raw.get("id")

    if not external_id:
        return None

    position = (
        row.get("position")
        or raw.get("position")
        or ""
    )

    player, _ = (
        Player.objects.update_or_create(
            sport=sport,
            external_id=str(
                external_id
            ),
            defaults={
                "team": team,
                "name": (
                    raw.get("name")
                    or raw.get("shortName")
                    or f"Player {external_id}"
                ),
                "position": position,
            },
        )
    )

    return player


def sync_finished_event(
    event,
    provider,
):
    payload = provider.get_lineups(
        event.external_id
    )

    if not payload:
        return {
            "players": 0,
            "saved": 0,
        }

    saved = 0
    total = 0

    for side, team, conceded in (
        (
            "home",
            event.home_team,
            event.away_score,
        ),
        (
            "away",
            event.away_team,
            event.home_score,
        ),
    ):
        side_payload = (
            payload.get(side)
            or {}
        )

        for row in _rows(
            side_payload
        ):
            player = _player_from_row(
                row,
                team,
                team.sport,
            )

            if not player:
                continue

            total += 1

            stats = (
                row.get("statistics")
                or {}
            )

            substitute = bool(
                row.get(
                    "substitute",
                    False,
                )
            )

            starter_raw = row.get(
                "starter"
            )

            if starter_raw is None:
                started = not substitute
            else:
                started = bool(
                    starter_raw
                )

            minutes = _int(
                stats.get(
                    "minutesPlayed"
                )
            )

            goals = (
                _int(
                    stats.get(
                        "goals"
                    )
                )
                or 0
            )

            assists = (
                _int(
                    stats.get(
                        "goalAssist",
                        stats.get(
                            "assists"
                        ),
                    )
                )
                or 0
            )

            PlayerMatchStats.objects.update_or_create(
                event=event,
                player=player,
                defaults={
                    "team": team,
                    "position": (
                        row.get(
                            "position"
                        )
                        or player.position
                    ),
                    "started": started,
                    "substitute": (
                        substitute
                    ),
                    "minutes": minutes,
                    "goals": goals,
                    "assists": assists,
                    "xg": _decimal(
                        stats.get(
                            "expectedGoals"
                        )
                    ),
                    "xa": _decimal(
                        stats.get(
                            "expectedAssists"
                        )
                    ),
                    "shots": _int(
                        stats.get(
                            "totalShots"
                        )
                    ),
                    "shots_on_target": _int(
                        stats.get(
                            "shotsOnTarget"
                        )
                    ),
                    "saves": _int(
                        stats.get(
                            "saves"
                        )
                    ),
                    "rating": _decimal(
                        stats.get(
                            "rating"
                        )
                    ),
                    "team_goals_conceded": (
                        conceded
                    ),
                    "clean_sheet": (
                        conceded == 0
                        if conceded
                        is not None
                        else None
                    ),
                },
            )

            saved += 1

    return {
        "players": total,
        "saved": saved,
    }


def sync_upcoming_lineup(
    event,
    provider,
):
    payload = provider.get_lineups(
        event.external_id
    )

    if not payload:
        return {
            "available": False,
            "confirmed": False,
            "starters": 0,
            "players": 0,
        }

    confirmed = bool(
        payload.get("confirmed")
    )

    total = 0
    starters = 0

    for side, team in (
        ("home", event.home_team),
        ("away", event.away_team),
    ):
        side_payload = (
            payload.get(side)
            or {}
        )

        for row in _rows(
            side_payload
        ):
            player = _player_from_row(
                row,
                team,
                team.sport,
            )

            if not player:
                continue

            substitute = bool(
                row.get(
                    "substitute",
                    False,
                )
            )

            starter_raw = row.get(
                "starter"
            )

            if starter_raw is None:
                starter = (
                    not substitute
                )
            else:
                starter = bool(
                    starter_raw
                )

            EventLineupPlayer.objects.update_or_create(
                event=event,
                player=player,
                defaults={
                    "team": team,
                    "position": (
                        row.get(
                            "position"
                        )
                        or player.position
                    ),
                    "starter": starter,
                    "substitute": (
                        substitute
                    ),
                    "confirmed": (
                        confirmed
                    ),
                },
            )

            total += 1

            if starter:
                starters += 1

    return {
        "available": total > 0,
        "confirmed": confirmed,
        "starters": starters,
        "players": total,
    }
