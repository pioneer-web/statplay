from decimal import Decimal

from odds.models import Bookmaker, Market, OddSnapshot


MARKETS = {
    "home_win": ("Vitória mandante", "1x2", None),
    "draw": ("Empate", "1x2", None),
    "away_win": ("Vitória visitante", "1x2", None),
    "btts_yes": ("Ambas marcam", "btts", None),

    "goals_over_1_5": (
        "Mais de 1.5 gols",
        "goals",
        1.5,
    ),
    "goals_over_2_5": (
        "Mais de 2.5 gols",
        "goals",
        2.5,
    ),

    "cards_over_2_5": (
        "Mais de 2.5 cartões",
        "cards",
        2.5,
    ),
    "cards_over_3_5": (
        "Mais de 3.5 cartões",
        "cards",
        3.5,
    ),
    "cards_over_4_5": (
        "Mais de 4.5 cartões",
        "cards",
        4.5,
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
    "corners_over_9_5": (
        "Mais de 9.5 escanteios",
        "corners",
        9.5,
    ),
}


LINES = {
    9: {
        1.5: "goals_over_1_5",
        2.5: "goals_over_2_5",
    },
    20: {
        2.5: "cards_over_2_5",
        3.5: "cards_over_3_5",
        4.5: "cards_over_4_5",
    },
    21: {
        7.5: "corners_over_7_5",
        8.5: "corners_over_8_5",
        9.5: "corners_over_9_5",
    },
}


def decimal_odd(choice):
    fraction = choice.get("fractionalValue")

    if fraction:
        try:
            numerator, denominator = str(
                fraction
            ).split("/")

            denominator = float(denominator)

            if denominator:
                return round(
                    1
                    + float(numerator)
                    / denominator,
                    3,
                )
        except Exception:
            pass

    value = choice.get("decimalValue")

    try:
        value = float(value)

        if value > 1:
            return value
    except Exception:
        pass

    return None


def extract_offers(payload):
    offers = {}

    for market in payload.get("markets", []):
        if market.get("isLive") is True:
            continue

        if market.get("suspended") is True:
            continue

        period = str(
            market.get("marketPeriod") or ""
        ).lower()

        if period and period not in (
            "full-time",
            "full time",
        ):
            continue

        market_id = market.get("marketId")

        if market_id == 1:
            mapping = {
                "1": "home_win",
                "x": "draw",
                "2": "away_win",
            }

            for choice in market.get(
                "choices",
                [],
            ):
                code = mapping.get(
                    str(
                        choice.get("name", "")
                    ).lower()
                )

                odd = decimal_odd(choice)

                if code and odd:
                    offers[code] = odd

            continue

        if market_id == 5:
            for choice in market.get(
                "choices",
                [],
            ):
                if (
                    str(
                        choice.get("name", "")
                    ).lower()
                    != "yes"
                ):
                    continue

                odd = decimal_odd(choice)

                if odd:
                    offers["btts_yes"] = odd

            continue

        if market_id not in LINES:
            continue

        try:
            line = float(
                market.get("choiceGroup")
            )
        except (TypeError, ValueError):
            continue

        code = LINES[
            market_id
        ].get(line)

        if not code:
            continue

        for choice in market.get(
            "choices",
            [],
        ):
            if (
                str(
                    choice.get("name", "")
                ).lower()
                != "over"
            ):
                continue

            odd = decimal_odd(choice)

            if odd:
                offers[code] = odd

    return offers


def save_event_odds(event, payload):
    bookmaker, _ = (
        Bookmaker.objects.get_or_create(
            slug="sofascore-feed",
            defaults={
                "name": "SofaScore Feed",
                "active": True,
            },
        )
    )

    offers = extract_offers(payload)

    created = 0

    for code, odd in offers.items():
        if code not in MARKETS:
            continue

        name, category, line = (
            MARKETS[code]
        )

        market, _ = (
            Market.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "category": category,
                },
            )
        )

        latest = (
            OddSnapshot.objects
            .filter(
                event=event,
                bookmaker=bookmaker,
                market=market,
                selection=code,
            )
            .order_by("-captured_at")
            .first()
        )

        if (
            latest
            and float(latest.odd)
            == float(odd)
        ):
            continue

        OddSnapshot.objects.create(
            event=event,
            bookmaker=bookmaker,
            market=market,
            selection=code,
            line=(
                Decimal(str(line))
                if line is not None
                else None
            ),
            odd=Decimal(str(odd)),
        )

        created += 1

    return {
        "offers": len(offers),
        "snapshots": created,
    }
