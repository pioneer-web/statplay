import re

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date

from odds.models import Bookmaker, Market, OddSnapshot
from predictions.stat_engine import evaluate_event
from sports.models import Event
from sports.providers.sofascore import SofaScoreProvider


TARGETS = {
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

    "home_win": ("Vitória mandante", "1x2", None),
    "draw": ("Empate", "1x2", None),
    "away_win": ("Vitória visitante", "1x2", None),
}


def decimal_odd(choice):
    for key in ("decimalValue", "decimal"):
        value = choice.get(key)

        if value is not None:
            try:
                value = float(value)

                if value > 1:
                    return value
            except (TypeError, ValueError):
                pass

    fractional = choice.get("fractionalValue")

    if fractional and "/" in str(fractional):
        try:
            a, b = str(fractional).split("/", 1)
            return 1 + float(a) / float(b)
        except Exception:
            pass

    value = choice.get("value")

    try:
        value = float(value)

        if 1.01 <= value <= 100:
            return value
    except (TypeError, ValueError):
        pass

    return None


def number_from_text(text):
    match = re.search(
        r"(\d+(?:[.,]\d+)?)",
        text,
    )

    if not match:
        return None

    return float(
        match.group(1).replace(",", ".")
    )


def normalize(value):
    return (
        str(value or "")
        .lower()
        .strip()
    )


def detect_offer(event, market, choice):
    market_name = normalize(
        market.get("marketName")
        or market.get("name")
    )

    choice_name = normalize(
        choice.get("name")
    )

    combined = (
        market_name
        + " "
        + choice_name
    )

    odd = decimal_odd(choice)

    if odd is None:
        return None

    #
    # 1X2
    #
    result_market = any(
        term in market_name
        for term in (
            "1x2",
            "match result",
            "full time result",
            "winner",
            "resultado",
        )
    )

    if result_market:
        if choice_name in ("1", "home"):
            return "home_win", odd

        if choice_name in ("x", "draw"):
            return "draw", odd

        if choice_name in ("2", "away"):
            return "away_win", odd

        home = normalize(
            event.home_team.name
        )

        away = normalize(
            event.away_team.name
        )

        if home and home in choice_name:
            return "home_win", odd

        if away and away in choice_name:
            return "away_win", odd

        if "draw" in choice_name:
            return "draw", odd

    #
    # Somente OVER
    #
    if "over" not in combined:
        return None

    line = number_from_text(
        choice_name
    )

    if line is None:
        line = number_from_text(
            market_name
        )

    if line is None:
        return None

    if "corner" in combined:
        code = (
            f"corners_over_"
            f"{str(line).replace('.', '_')}"
        )

    elif "card" in combined:
        code = (
            f"cards_over_"
            f"{str(line).replace('.', '_')}"
        )

    elif (
        "goal" in combined
        or "total" in market_name
    ):
        code = (
            f"goals_over_"
            f"{str(line).replace('.', '_')}"
        )

    else:
        return None

    if code not in TARGETS:
        return None

    return code, odd


class Command(BaseCommand):
    help = "Sincroniza odds e calcula edge StatPlay"

    def add_arguments(self, parser):
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
            "--min-edge",
            type=float,
            default=3.0,
        )

        parser.add_argument(
            "--min-prob",
            type=float,
            default=60.0,
        )

    def handle(self, *args, **options):
        target_date = parse_date(
            options["date"]
        )

        bookmaker, _ = (
            Bookmaker.objects.get_or_create(
                slug="sofascore",
                defaults={
                    "name": "SofaScore",
                    "active": True,
                },
            )
        )

        events = (
            Event.objects
            .filter(
                starts_at__date=target_date,
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

        provider = SofaScoreProvider()

        tested = 0
        with_model = 0
        with_odds = 0
        mapped_odds = 0

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

            model_markets = {
                item["code"]: item
                for item in model["markets"]
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
                []
            )

            if not markets:
                continue

            with_odds += 1

            best = {}

            for raw_market in markets:
                for choice in raw_market.get(
                    "choices",
                    [],
                ):
                    detected = detect_offer(
                        event,
                        raw_market,
                        choice,
                    )

                    if not detected:
                        continue

                    code, odd = detected

                    current = best.get(code)

                    if (
                        current is None
                        or odd > current
                    ):
                        best[code] = odd

            for code, odd in best.items():
                if code not in model_markets:
                    continue

                mapped_odds += 1

                label, category, line = (
                    TARGETS[code]
                )

                market, _ = (
                    Market.objects.get_or_create(
                        code=code,
                        defaults={
                            "name": label,
                            "category": category,
                        },
                    )
                )

                OddSnapshot.objects.create(
                    event=event,
                    bookmaker=bookmaker,
                    market=market,
                    selection=code,
                    line=line,
                    odd=odd,
                )

                prediction = (
                    model_markets[code]
                )

                probability = float(
                    prediction["probability"]
                )

                implied = 100 / odd

                edge = (
                    probability - implied
                )

                if (
                    probability
                    >= options["min_prob"]
                    and edge
                    >= options["min_edge"]
                ):
                    opportunities.append({
                        "event": event,
                        "code": code,
                        "label": label,
                        "probability": probability,
                        "odd": odd,
                        "implied": implied,
                        "edge": edge,
                        "fair": (
                            100 / probability
                        ),
                    })

        opportunities.sort(
            key=lambda item: item["edge"],
            reverse=True,
        )

        self.stdout.write(
            "\n=== STATPLAY VALUE ENGINE ==="
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
            f"Odds mapeadas: {mapped_odds}"
        )

        self.stdout.write(
            f"Oportunidades: "
            f"{len(opportunities)}"
        )

        self.stdout.write(
            "\n=== MAIORES EDGES ==="
        )

        for item in opportunities[:25]:
            event = item["event"]

            self.stdout.write(
                f"{event.home_team.name} "
                f"x {event.away_team.name}"
            )

            self.stdout.write(
                f"  {item['label']}"
                f" | modelo={item['probability']:.1f}%"
                f" | odd={item['odd']:.2f}"
                f" | implícita={item['implied']:.1f}%"
                f" | justa={item['fair']:.2f}"
                f" | EDGE={item['edge']:+.1f}pp"
            )
