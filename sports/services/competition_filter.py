import re


EXCLUDED_TERMS = (
    "friendly",
    "friendlies",
    "amistoso",
    "amistosos",
    "academy",
    "youth",
    "junior",
    "juniors",
    "reserves",
    "reserve",
)


def is_professional_competition(name):
    if not name:
        return False

    text = name.lower().strip()

    if any(term in text for term in EXCLUDED_TERMS):
        return False

    # U17, U18, U19, U20, U21, U23 etc.
    if re.search(r"\bu[\s-]?(1[5-9]|2[0-3])\b", text):
        return False

    # Sub-17, Sub 20 etc.
    if re.search(r"\bsub[\s-]?(1[5-9]|2[0-3])\b", text):
        return False

    return True
