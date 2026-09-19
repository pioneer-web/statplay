def _avg(values):
    clean = [
        float(value)
        for value in values
        if value is not None
    ]

    if not clean:
        return None

    return sum(clean) / len(clean)


def team_recent_features(
    team,
    before=None,
    limit=10,
):
    from sports.models import TeamMatchStats

    qs = (
        TeamMatchStats.objects
        .filter(
            team=team,
            event__status="finished",
        )
        .select_related("event")
        .order_by("-event__starts_at")
    )

    if before is not None:
        qs = qs.filter(
            event__starts_at__lt=before
        )

    stats = list(qs[:limit])

    goals_for = []
    goals_against = []

    corners_for = []
    corners_against = []

    cards_for = []
    cards_against = []

    xg_for = []
    xg_against = []

    shots_for = []
    shots_against = []

    shots_target_for = []
    shots_target_against = []

    possession = []

    for stat in stats:
        event = stat.event

        opponent = (
            TeamMatchStats.objects
            .filter(event=event)
            .exclude(team=team)
            .first()
        )

        if opponent is None:
            continue

        is_home = event.home_team_id == team.id

        if (
            event.home_score is not None
            and event.away_score is not None
        ):
            if is_home:
                goals_for.append(event.home_score)
                goals_against.append(event.away_score)
            else:
                goals_for.append(event.away_score)
                goals_against.append(event.home_score)

        if stat.corners is not None:
            corners_for.append(stat.corners)

        if opponent.corners is not None:
            corners_against.append(
                opponent.corners
            )

        if stat.cards is not None:
            cards_for.append(stat.cards)

        if opponent.cards is not None:
            cards_against.append(
                opponent.cards
            )

        if stat.xg is not None:
            xg_for.append(stat.xg)

        if opponent.xg is not None:
            xg_against.append(opponent.xg)

        if stat.shots is not None:
            shots_for.append(stat.shots)

        if opponent.shots is not None:
            shots_against.append(
                opponent.shots
            )

        if stat.shots_on_target is not None:
            shots_target_for.append(
                stat.shots_on_target
            )

        if opponent.shots_on_target is not None:
            shots_target_against.append(
                opponent.shots_on_target
            )

        if stat.possession is not None:
            possession.append(
                stat.possession
            )

    return {
        "matches": len(stats),

        "goals_for": _avg(goals_for),
        "goals_against": _avg(goals_against),

        "corners_for": _avg(corners_for),
        "corners_against": _avg(
            corners_against
        ),

        "cards_for": _avg(cards_for),
        "cards_against": _avg(
            cards_against
        ),

        "xg_for": _avg(xg_for),
        "xg_against": _avg(
            xg_against
        ),

        "shots_for": _avg(shots_for),
        "shots_against": _avg(
            shots_against
        ),

        "shots_target_for": _avg(
            shots_target_for
        ),
        "shots_target_against": _avg(
            shots_target_against
        ),

        "possession": _avg(possession),

        "cards_samples": len(cards_for),
        "corners_samples": len(
            corners_for
        ),
        "xg_samples": len(xg_for),
    }
