import re
from collections import Counter

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date

from odds.models import Bookmaker, Market, OddSnapshot
from predictions.stat_engine import evaluate_event
from sports.models import Event
from sports.providers.sofascore import SofaScoreProvider


TARGETS = {
    "home_win": ("Vitória mandante", "1x2", None),
    "draw": ("Empate", "1x2", None),
    "away_win": ("Vitória visitante", "1x2", None),
    "btts_yes": ("Ambas marcam", "btts", None),

    "goals_over_1_5": ("Mais de 1.5 gols", "goals", 1.5),
    "goals_over_2_5": ("Mais de 2.5 gols", "goals", 2.5),

    "corners_over_7_5": ("Mais de 7.5 escanteios", "corners", 7.5),
    "corners_over_8_5": ("Mais de 8.5 escanteios", "corners", 8.5),
    "corners_over_9_5": ("Mais de 9.5 escanteios", "corners", 9.5),
    "corners_over_10_5": ("Mais de 10.5 escanteios", "corners", 10.5),

    "cards_over_2_5": ("Mais de 2.5 cartões", "cards", 2.5),
    "cards_over_3_5": ("Mais de 3.5 cartões", "cards", 3.5),
    "cards_over_4_5": ("Mais de 4.5 cartões", "cards", 4.5),
    "cards_over_5_5": ("Mais de 5.5 cartões", "cards", 5.5),
}


def norm(value):
    return re.sub(
        r"\s+",
        " ",
        str(value or "").strip().lower(),
    )


def extract_number(text):
    values = re.findall(
        r"\d+(?:[.,]\d+)?",
        norm(text),
    )

    if not values:
        return None

    # Para mercados O/U preferimos linhas decimais.
    for value in reversed(values):
        number = float(
            value.replace(",", ".")
        )

        if number % 1 == 0.5:
            return number

    return float(
        values[-1].replace(",", ".")
    )


def decimal_odd(choice):
    value = choice.get("decimalValue")

    if value is not None:
        try:
            value = float(value)

            if 1.0 < value < 100:
                return value
        except Exception:
            pass

    fraction = choice.get(
        "fractionalValue"
    )

    if fraction:
        try:
            left, right = (
                str(fraction).split("/")
            )

            right = float(right)

            if right:
                return (
                    1
                    + float(left) / right
                )
        except Exception:
            pass

    value = choice.get("value")

    try:
        value = float(value)

        if 1.0 < value < 100:
            return value
    except Exception:
        pass

    return None


def market_text(market):
    return norm(
        " ".join(
            str(market.get(key) or "")
            for key in (
                "name",
                "marketName",
                "marketGroup",
                "choiceGroup",
                "description",
                "groupName",
                "slug",
            )
        )
    )


def choice_text(choice):
    return norm(
        " ".join(
            str(choice.get(key) or "")
            for key in (
                "name",
                "description",
                "label",
            )
        )
    )


def detect_1x2(market):
    choices = market.get(
        "choices",
        [],
    )

    names = {
        norm(choice.get("name"))
        for choice in choices
    }

    return (
        {"1", "x", "2"}.issubset(names)
        or
        {"home", "draw", "away"}.issubset(names)
    )


def detect_offer(
    market,
    choice,
    is_1x2,
):
    ctext = choice_text(choice)
    mtext = market_text(market)

    odd = decimal_odd(choice)

    if odd is None:
        return None

    #
    # 1X2 pela estrutura das escolhas,
    # independentemente do nome do mercado.
    #
    if is_1x2:
        name = norm(
            choice.get("name")
        )

        if name in (
            "1",
            "home",
        ):
            return "home_win", odd

        if name in (
            "x",
            "draw",
        ):
            return "draw", odd

        if name in (
            "2",
            "away",
        ):
            return "away_win", odd

    combined = (
        f"{mtext} {ctext}"
    )

    #
    # Ambas marcam
    #
    if (
        "both teams to score" in mtext
        or "both teams score" in mtext
    ):
        if ctext in ("yes", "sim"):
            return "btts_yes", odd

    #
    # Apenas escolhas OVER.
    #
    over_terms = (
        "over",
        "mais de",
        "acima de",
    )

    if not any(
        term in combined
        for term in over_terms
    ):
        return None

    line = (
        extract_number(
            market.get("choiceGroup")
        )
        or extract_number(ctext)
        or extract_number(mtext)
    )

    if line is None:
        return None

    #
    # Detecta categoria.
    #
    if any(
        term in combined
        for term in (
            "corner",
            "corners",
            "escanteio",
        )
    ):
        prefix = "corners_over"

    elif any(
        term in combined
        for term in (
            "card",
            "cards",
            "booking",
            "cartão",
            "cartoes",
        )
    ):
        prefix = "cards_over"

    elif any(
        term in combined
        for term in (
            "goal",
            "goals",
            "gols",
        )
    ):
        prefix = "goals_over"

    elif (
        "total" in mtext
        and line in (1.5, 2.5)
    ):
        # Em futebol, total 1.5/2.5
        # sem outra categoria normalmente
        # representa gols.
        prefix = "goals_over"

    else:
        return None

    line_code = (
        f"{line:.1f}"
        .replace(".", "_")
    )

    code = (
        f"{prefix}_{line_code}"
    )

    if code not in TARGETS:
        return None

    return code, odd


class Command(BaseCommand):
    help = "Motor de odds, fair odd e edge da StatPlay"

    def add_arguments(
        self,
        parser,
    ):
        parser.add_argument(
            "--date",
            required=True,
        )

        parser.add_argument(
            "--limit",
            type=int,
            default=1000,
        )

        parser.add_argument(
            "--min-prob",
            type=float,
            default=60,
        )

        parser.add_argument(
            "--min-edge",
            type=float,
            default=3,
        )

    def handle(
        self,
        *args,
        **options,
    ):
        date = parse_date(
            options["date"]
        )

        provider = (
            SofaScoreProvider()
        )

        bookmaker, _ = (
            Bookmaker.objects
            .get_or_create(
                slug="sofascore-feed",
                defaults={
                    "name": (
                        "SofaScore Feed"
                    )
                },
            )
        )

        events = (
            Event.objects
            .filter(
                starts_at__date=date,
                status="scheduled",
            )
            .exclude(external_id="")
            .select_related(
                "home_team",
                "away_team",
                "competition",
            )
            .order_by("starts_at")[
                :options["limit"]
            ]
        )

        tested = 0
        with_model = 0
        with_odds = 0

        raw_markets = 0
        valid_choices = 0
        recognized = 0
        mapped = 0

        unknown_markets = (
            Counter()
        )

        opportunities = []

        for event in events:
            tested += 1

            model = evaluate_event(
                event,
                sample=10,
                min_matches=5,
            )

            if not model:
                continue

            with_model += 1

            model_map = {
                item["code"]: item
                for item
                in model["markets"]
            }

            try:
                payload = (
                    provider.get_odds(
                        event.external_id
                    )
                    or {}
                )
            except Exception:
                continue

            markets = payload.get(
                "markets",
                [],
            )

            if not markets:
                continue

            with_odds += 1
            raw_markets += len(markets)

            best = {}

            for market in markets:
                mtext = market_text(
                    market
                )

                is_1x2 = detect_1x2(
                    market
                )

                market_recognized = (
                    False
                )

                for choice in market.get(
                    "choices",
                    [],
                ):
                    odd = decimal_odd(
                        choice
                    )

                    if odd is not None:
                        valid_choices += 1

                    offer = detect_offer(
                        market,
                        choice,
                        is_1x2,
                    )

                    if not offer:
                        continue

                    market_recognized = (
                        True
                    )

                    recognized += 1

                    code, odd = offer

                    if code not in model_map:
                        continue

                    old = best.get(code)

                    if (
                        old is None
                        or odd > old
                    ):
                        best[code] = odd

                if not market_recognized:
                    unknown_markets[
                        mtext or "(sem nome)"
                    ] += 1

            for code, odd in (
                best.items()
            ):
                mapped += 1

                label, category, line = (
                    TARGETS[code]
                )

                db_market, _ = (
                    Market.objects
                    .get_or_create(
                        code=code,
                        defaults={
                            "name": label,
                            "category": (
                                category
                            ),
                        },
                    )
                )

                OddSnapshot.objects.create(
                    event=event,
                    bookmaker=bookmaker,
                    market=db_market,
                    selection=code,
                    line=line,
                    odd=odd,
                )

                model_item = (
                    model_map[code]
                )

                probability = float(
                    model_item[
                        "probability"
                    ]
                )

                implied = (
                    100.0 / odd
                )

                fair_odd = (
                    100.0
                    / probability
                )

                edge = (
                    probability
                    - implied
                )

                if (
                    probability
                    >= options[
                        "min_prob"
                    ]
                    and edge
                    >= options[
                        "min_edge"
                    ]
                ):
                    opportunities.append({
                        "event": event,
                        "label": label,
                        "probability": (
                            probability
                        ),
                        "odd": odd,
                        "implied": implied,
                        "fair": fair_odd,
                        "edge": edge,
                    })

        opportunities.sort(
            key=lambda x: x["edge"],
            reverse=True,
        )

        self.stdout.write(
            "\n=== STATPLAY VALUE ENGINE V2 ==="
        )

        self.stdout.write(
            f"Jogos testados: {tested}"
        )

        self.stdout.write(
            f"Jogos com modelo: {with_model}"
        )

        self.stdout.write(
            f"Jogos com odds: {with_odds}"
        )

        self.stdout.write(
            f"Mercados brutos: {raw_markets}"
        )

        self.stdout.write(
            f"Escolhas com odd válida: "
            f"{valid_choices}"
        )

        self.stdout.write(
            f"Ofertas reconhecidas: "
            f"{recognized}"
        )

        self.stdout.write(
            f"Odds casadas com modelo: "
            f"{mapped}"
        )

        self.stdout.write(
            f"Oportunidades edge >= "
            f"{options['min_edge']}pp: "
            f"{len(opportunities)}"
        )

        self.stdout.write(
            "\n=== MAIORES EDGES ==="
        )

        for item in (
            opportunities[:20]
        ):
            event = item["event"]

            self.stdout.write(
                f"{event.home_team.name} "
                f"x "
                f"{event.away_team.name}"
            )

            self.stdout.write(
                f"  {item['label']} "
                f"| P={item['probability']:.1f}% "
                f"| odd={item['odd']:.2f} "
                f"| implícita={item['implied']:.1f}% "
                f"| justa={item['fair']:.2f} "
                f"| edge={item['edge']:+.1f}pp"
            )

        self.stdout.write(
            "\n=== MERCADOS NÃO MAPEADOS ==="
        )

        for name, total in (
            unknown_markets
            .most_common(15)
        ):
            self.stdout.write(
                f"{total}x | {name}"
            )
