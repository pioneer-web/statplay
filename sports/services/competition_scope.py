import re
import unicodedata


def normalize(value):
    value = unicodedata.normalize(
        "NFKD",
        str(value or ""),
    )

    value = "".join(
        char
        for char in value
        if not unicodedata.combining(char)
    )

    value = value.lower().strip()

    return re.sub(r"\s+", " ", value)


BLOCKED = (
    "women",
    "woman",
    "feminino",
    "feminina",
    "femenino",
    "femenina",
    "frauen",
    "youth",
    "juvenil",
    "junior",
    "primavera",
    "amador",
    "academy",
    "reserve",
    "reserves",
    "u15",
    "u16",
    "u17",
    "u18",
    "u19",
    "u20",
    "u21",
    "u23",
    "sub 15",
    "sub 17",
    "sub 20",
    "sub 23",
)


EUROPE = (
    "premier league",
    "laliga",
    "la liga",
    "serie a",
    "bundesliga",
    "ligue 1",
    "liga portugal",
    "primeira liga",
    "eredivisie",
)


EUROPE_CONTINENTAL = (
    "champions league",
    "europa league",
    "conference league",
)


SOUTH_AMERICA = (
    "libertadores",
    "sudamericana",
    "sul-americana",
    "recopa sudamericana",
    "recopa sul-americana",
)


BRAZIL_NATIONAL = (
    "brasileirao",
    "brasileirao serie a",
    "brasileirao serie b",
    "brasileiro serie a",
    "brasileiro serie b",
    "copa do brasil",
)


STATE_NAMES = (
    "paulista",
    "carioca",
    "mineiro",
    "gaucho",
    "paranaense",
    "catarinense",
    "baiano",
    "pernambucano",
    "cearense",
    "goiano",
    "paraense",
)


STATE_BLOCKED = (
    "serie b",
    "serie b1",
    "serie b2",
    "serie c",
    "serie d",
    "serie a2",
    "serie a3",
    "a2",
    "a3",
    "2a divisao",
    "2ª divisao",
    "segunda divisao",
    "divisao de acesso",
    "3a divisao",
    "3ª divisao",
    "terceira divisao",
    "copa paulista",
)


def is_target_competition(name, country=""):
    name = normalize(name)
    country = normalize(country)

    if not name:
        return False

    if any(term in name for term in BLOCKED):
        return False

    # UEFA
    if any(
        term in name
        for term in EUROPE_CONTINENTAL
    ):
        return True

    # CONMEBOL
    if any(
        term in name
        for term in SOUTH_AMERICA
    ):
        return True

    # Brasil
    if country in ("brazil", "brasil") or "brasileir" in name:
        if any(
            term in name
            for term in STATE_BLOCKED
        ):
            return False

        if name == "brasileirao":
            return True

        if any(
            term in name
            for term in BRAZIL_NATIONAL
        ):
            return True

        if any(
            state in name
            for state in STATE_NAMES
        ):
            return True

        return False

    # Inglaterra
    if country == "england":
        return name == "premier league"

    # Espanha
    if country == "spain":
        return name in (
            "laliga",
            "la liga",
        )

    # Itália
    if country == "italy":
        return name == "serie a"

    # Alemanha
    if country == "germany":
        return name == "bundesliga"

    # França
    if country == "france":
        return name == "ligue 1"

    # Portugal
    if country == "portugal":
        return (
            "liga portugal" in name
            or name == "primeira liga"
        )

    # Holanda
    if country in (
        "netherlands",
        "holland",
    ):
        return name == "eredivisie"

    return False
