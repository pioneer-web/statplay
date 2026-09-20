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

    return re.sub(
        r"\s+",
        " ",
        value.lower().strip(),
    )


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
    " a2",
    " a3",
    "segunda divisao",
    "divisao de acesso",
    "terceira divisao",
    "quarta divisao",
    "copa paulista",
)


def is_target_competition(
    name,
    country="",
):
    name = normalize(name)
    country = normalize(country)

    if not name:
        return False

    if any(
        term in name
        for term in BLOCKED
    ):
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

    # Brasil nacional
    if (
        name == "brasileirao"
        or name.startswith(
            "brasileirao serie a"
        )
        or name.startswith(
            "brasileirao serie b"
        )
        or name.startswith(
            "brasileiro serie a"
        )
        or name.startswith(
            "brasileiro serie b"
        )
        or name.startswith(
            "copa do brasil"
        )
    ):
        return True

    # Estaduais - somente primeira divisão
    if country in (
        "brazil",
        "brasil",
    ):
        if any(
            state in name
            for state in STATE_NAMES
        ):
            if any(
                blocked in name
                for blocked
                in STATE_BLOCKED
            ):
                return False

            return True

        return False

    # Principais ligas europeias
    if country == "england":
        return name == "premier league"

    if country == "spain":
        return name in (
            "laliga",
            "la liga",
        )

    if country == "italy":
        return name == "serie a"

    if country == "germany":
        return name == "bundesliga"

    if country == "france":
        return name == "ligue 1"

    if country == "portugal":
        return (
            name.startswith(
                "liga portugal"
            )
            or name
            == "primeira liga"
        )

    if country in (
        "netherlands",
        "holland",
    ):
        return name == "eredivisie"

    return False
