from decimal import Decimal

from odds.models import (
    Bookmaker,
    Market,
    OddSnapshot,
)


MARKETS = {
    "home_win":
        (
            "Vitória mandante",
            "result",
            None,
        ),

    "draw":
        (
            "Empate",
            "result",
            None,
        ),

    "away_win":
        (
            "Vitória visitante",
            "result",
            None,
        ),

    "btts_yes":
        (
            "Ambas marcam - Sim",
            "goals",
            None,
        ),

    "btts_no":
        (
            "Ambas marcam - Não",
            "goals",
            None,
        ),
}


for prefix, category, lines in (
    (
        "goals",
        "goals",
        (1.5, 2.5, 3.5),
    ),
    (
        "corners",
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
        "cards",
        (
            2.5,
            3.5,
            4.5,
            5.5,
        ),
    ),
):
    noun = {
        "goals": "gols",
        "corners": "escanteios",
        "cards": "cartões",
    }[prefix]

    for line in lines:
        code_line = (
            str(line)
            .replace(
                ".",
                "_",
            )
        )

        MARKETS[
            f"{prefix}_over_{code_line}"
        ] = (
            f"Mais de {line} {noun}",
            category,
            line,
        )

        MARKETS[
            f"{prefix}_under_{code_line}"
        ] = (
            f"Menos de {line} {noun}",
            category,
            line,
        )


LINES = {
    9: {
        1.5: "goals",
        2.5: "goals",
        3.5: "goals",
    },

    20: {
        2.5: "cards",
        3.5: "cards",
        4.5: "cards",
        5.5: "cards",
    },

    21: {
        7.5: "corners",
        8.5: "corners",
        9.5: "corners",
        10.5: "corners",
    },
}


def decimal_odd(choice):
    fraction = choice.get(
        "fractionalValue"
    )

    if fraction:
        try:
            numerator, denominator = (
                str(fraction).split(
                    "/"
                )
            )

            denominator = float(
                denominator
            )

            if denominator:
                return round(
                    1
                    + float(
                        numerator
                    )
                    / denominator,
                    3,
                )
        except Exception:
            pass

    value = choice.get(
        "decimalValue"
    )

    try:
        value = float(value)

        if value > 1:
            return value
    except Exception:
        pass

    return None


def extract_offers(payload):
    offers = {}

    for market in payload.get(
        "markets",
        [],
    ):
        if market.get(
            "isLive"
        ) is True:
            continue

        if market.get(
            "suspended"
        ) is True:
            continue

        period = str(
            market.get(
                "marketPeriod"
            )
            or ""
        ).lower()

        if (
            period
            and period not in (
                "full-time",
                "full time",
            )
        ):
            continue

        market_id = (
            market.get(
                "marketId"
            )
        )

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
                        choice.get(
                            "name",
                            "",
                        )
                    ).lower()
                )

                odd = decimal_odd(
                    choice
                )

                if code and odd:
                    offers[
                        code
                    ] = odd

            continue

        if market_id == 5:
            for choice in market.get(
                "choices",
                [],
            ):
                name = str(
                    choice.get(
                        "name",
                        "",
                    )
                ).lower()

                odd = decimal_odd(
                    choice
                )

                if not odd:
                    continue

                if name == "yes":
                    offers[
                        "btts_yes"
                    ] = odd

                elif name == "no":
                    offers[
                        "btts_no"
                    ] = odd

            continue

        if market_id not in LINES:
            continue

        try:
            line = float(
                market.get(
                    "choiceGroup"
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

        prefix = LINES[
            market_id
        ].get(line)

        if not prefix:
            continue

        code_line = (
            str(line)
            .replace(
                ".",
                "_",
            )
        )

        for choice in market.get(
            "choices",
            [],
        ):
            name = str(
                choice.get(
                    "name",
                    "",
                )
            ).lower()

            odd = decimal_odd(
                choice
            )

            if not odd:
                continue

            if name == "over":
                offers[
                    f"{prefix}_over_{code_line}"
                ] = odd

            elif name == "under":
                offers[
                    f"{prefix}_under_{code_line}"
                ] = odd

    return offers


def save_event_odds(
    event,
    payload,
):
    bookmaker, _ = (
        Bookmaker.objects
        .get_or_create(
            slug="sofascore-feed",
            defaults={
                "name":
                    "SofaScore Feed",
                "active":
                    True,
            },
        )
    )

    offers = extract_offers(
        payload
    )

    created = 0

    for code, odd in offers.items():
        definition = (
            MARKETS.get(code)
        )

        if not definition:
            continue

        name, category, line = (
            definition
        )

        market, _ = (
            Market.objects
            .get_or_create(
                code=code,
                defaults={
                    "name":
                        name,
                    "category":
                        category,
                },
            )
        )

        latest = (
            OddSnapshot.objects
            .filter(
                event=event,
                bookmaker=bookmaker,
                selection=code,
            )
            .order_by(
                "-captured_at"
            )
            .first()
        )

        if (
            latest
            and float(
                latest.odd
            )
            == float(odd)
        ):
            continue

        OddSnapshot.objects.create(
            event=event,
            bookmaker=bookmaker,
            market=market,
            selection=code,

            line=(
                Decimal(
                    str(line)
                )
                if line
                is not None
                else None
            ),

            odd=Decimal(
                str(odd)
            ),
        )

        created += 1

    return {
        "offers":
            len(offers),

        "snapshots":
            created,
    }
