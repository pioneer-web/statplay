from decimal import Decimal

from sports.models import TeamMatchStats


def _number(value):
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    value = str(value).strip()
    value = value.replace("%", "")
    value = value.replace(",", ".")

    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _find_item(items, keys, names):
    keys = {x.lower() for x in keys}
    names = {x.lower() for x in names}

    for item in items:
        key = str(item.get("key", "")).lower()
        name = str(item.get("name", "")).lower()

        if key in keys or name in names:
            return item

    return None


def _side_value(item, side):
    if item is None:
        return None

    value = item.get(f"{side}Value")

    if value is None:
        value = item.get(side)

    return _number(value)


def _integer(item, side):
    value = _side_value(item, side)

    if value is None:
        return None

    return int(value)


def _cards_value(yellow, red, generic, side):
    values = []

    yellow_value = _side_value(yellow, side)
    red_value = _side_value(red, side)

    if yellow_value is not None:
        values.append(yellow_value)

    if red_value is not None:
        values.append(red_value)

    if values:
        return int(sum(values))

    generic_value = _side_value(
        generic,
        side,
    )

    if generic_value is None:
        return None

    return int(generic_value)


def save_event_statistics(event, payload):
    if not payload:
        return False

    periods = payload.get("statistics", [])

    all_period = next(
        (
            period
            for period in periods
            if period.get("period") == "ALL"
        ),
        None,
    )

    if not all_period:
        return False

    items = []

    for group in all_period.get("groups", []):
        items.extend(
            group.get("statisticsItems", [])
        )

    corners = _find_item(
        items,
        {"cornerKicks", "corners"},
        {"Corner kicks", "Corners"},
    )

    shots = _find_item(
        items,
        {"totalShots"},
        {"Total shots"},
    )

    shots_target = _find_item(
        items,
        {"shotsOnGoal", "shotsOnTarget"},
        {"Shots on target"},
    )

    possession = _find_item(
        items,
        {"ballPossession"},
        {"Ball possession"},
    )

    xg = _find_item(
        items,
        {"expectedGoals"},
        {"Expected goals"},
    )

    yellow = _find_item(
        items,
        {"yellowCards"},
        {"Yellow cards"},
    )

    red = _find_item(
        items,
        {"redCards"},
        {"Red cards"},
    )

    generic_cards = _find_item(
        items,
        {"cards"},
        {"Cards"},
    )

    for side, team in (
        ("home", event.home_team),
        ("away", event.away_team),
    ):
        possession_value = _side_value(
            possession,
            side,
        )

        xg_value = _side_value(
            xg,
            side,
        )

        TeamMatchStats.objects.update_or_create(
            event=event,
            team=team,
            defaults={
                "corners": _integer(
                    corners,
                    side,
                ),
                "shots": _integer(
                    shots,
                    side,
                ),
                "shots_on_target": _integer(
                    shots_target,
                    side,
                ),
                "cards": _cards_value(
                    yellow,
                    red,
                    generic_cards,
                    side,
                ),
                "possession": (
                    Decimal(
                        str(possession_value)
                    )
                    if possession_value is not None
                    else None
                ),
                "xg": (
                    Decimal(str(xg_value))
                    if xg_value is not None
                    else None
                ),
            },
        )

    return True
