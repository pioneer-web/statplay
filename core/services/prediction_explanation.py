from statistics import mean

from odds.models import OddSnapshot
from sports.models import (
    EventLineupPlayer,
    TeamMatchStats,
)
from sports.services.player_features import (
    defensive_position,
    player_form,
)


def avg(values):
    values = [
        float(value)
        for value in values
        if value is not None
    ]

    if not values:
        return None

    return round(mean(values), 2)


def team_recent_summary(
    team,
    event,
    limit=10,
):
    rows = list(
        TeamMatchStats.objects
        .filter(
            team=team,
            event__status="finished",
            event__starts_at__lt=event.starts_at,
        )
        .select_related(
            "event",
            "event__home_team",
            "event__away_team",
        )
        .order_by(
            "-event__starts_at"
        )[:limit]
    )

    goals_for = []
    goals_against = []

    for row in rows:
        match = row.event

        if (
            match.home_score is None
            or match.away_score is None
        ):
            continue

        if match.home_team_id == team.id:
            goals_for.append(
                match.home_score
            )
            goals_against.append(
                match.away_score
            )
        else:
            goals_for.append(
                match.away_score
            )
            goals_against.append(
                match.home_score
            )

    return {
        "team": team.name,
        "matches": len(rows),
        "goals_for": avg(
            goals_for
        ),
        "goals_against": avg(
            goals_against
        ),
        "xg": avg(
            row.xg
            for row in rows
        ),
        "shots": avg(
            row.shots
            for row in rows
        ),
        "shots_on_target": avg(
            row.shots_on_target
            for row in rows
        ),
        "corners": avg(
            row.corners
            for row in rows
        ),
        "cards": avg(
            row.cards
            for row in rows
        ),
        "possession": avg(
            row.possession
            for row in rows
        ),
    }


def lineup_summary(
    event,
    team,
):
    entries = list(
        EventLineupPlayer.objects
        .filter(
            event=event,
            team=team,
            starter=True,
        )
        .select_related("player")
    )

    if not entries:
        return {
            "available": False,
            "confirmed": False,
            "status": "Não disponível",
            "starters": [],
            "attackers": [],
            "defenders": [],
        }

    confirmed = any(
        entry.confirmed
        for entry in entries
    )

    attackers = []
    defenders = []

    for entry in entries:
        player = entry.player

        data = player_form(
            player,
            event.starts_at,
            team,
        )

        item = {
            "name": player.name,
            "position": (
                entry.position
                or player.position
                or "—"
            ),
        }

        if data:
            item.update({
                "goals90": round(
                    data["goals90"],
                    2,
                ),
                "xg90": round(
                    data["xg90"],
                    2,
                ),
                "shots_target90": round(
                    data[
                        "shots_target90"
                    ],
                    2,
                ),
                "attack_score": round(
                    data[
                        "attack_score"
                    ],
                    3,
                ),
                "conceded": (
                    round(
                        data[
                            "conceded"
                        ],
                        2,
                    )
                    if data[
                        "conceded"
                    ] is not None
                    else None
                ),
            })

        if defensive_position(
            item["position"]
        ):
            defenders.append(item)

        if (
            data
            and data["attack_score"] > 0
        ):
            attackers.append(item)

    attackers.sort(
        key=lambda item: item.get(
            "attack_score",
            0,
        ),
        reverse=True,
    )

    return {
        "available": True,
        "confirmed": confirmed,
        "status": (
            "Confirmada"
            if confirmed
            else "Provável"
        ),
        "starters": [
            {
                "name": entry.player.name,
                "position": (
                    entry.position
                    or entry.player.position
                    or "—"
                ),
            }
            for entry in entries
        ],
        "attackers": attackers[:4],
        "defenders": defenders,
    }


def best_odd(prediction):
    odds = (
        OddSnapshot.objects
        .filter(
            event=prediction.event,
            market=prediction.market,
            selection=prediction.selection,
        )
    )

    if prediction.line is None:
        odds = odds.filter(
            line__isnull=True
        )
    else:
        odds = odds.filter(
            line=prediction.line
        )

    odd = (
        odds
        .select_related("bookmaker")
        .order_by("-odd")
        .first()
    )

    if not odd:
        return None

    value = float(odd.odd)

    return {
        "odd": odd.odd,
        "bookmaker": (
            odd.bookmaker.name
        ),
        "implied": round(
            100 / value,
            1,
        ),
        "edge": round(
            float(
                prediction.probability
            )
            - (100 / value),
            1,
        ),
    }


def build_explanation(
    prediction,
):
    event = prediction.event

    home_form = (
        team_recent_summary(
            event.home_team,
            event,
        )
    )

    away_form = (
        team_recent_summary(
            event.away_team,
            event,
        )
    )

    home_lineup = (
        lineup_summary(
            event,
            event.home_team,
        )
    )

    away_lineup = (
        lineup_summary(
            event,
            event.away_team,
        )
    )

    context = getattr(
        prediction,
        "context",
        None,
    )

    adjustment = None

    if context:
        adjustment = {
            "base_home": (
                context.base_home_goals
            ),
            "base_away": (
                context.base_away_goals
            ),
            "adjusted_home": (
                context.adjusted_home_goals
            ),
            "adjusted_away": (
                context.adjusted_away_goals
            ),
            "home_attack": float(
                context.home_attack_factor
            ),
            "away_attack": float(
                context.away_attack_factor
            ),
            "home_defense": float(
                context.home_defense_factor
            ),
            "away_defense": float(
                context.away_defense_factor
            ),
            "home_confirmed": (
                context.home_lineup_confirmed
            ),
            "away_confirmed": (
                context.away_lineup_confirmed
            ),
        }

    code = prediction.market.code

    if code.startswith(
        "goals_"
    ):
        explanation_type = "goals"

        conclusion = (
            "O StatPlay combina a produção "
            "ofensiva recente de cada equipe, "
            "gols sofridos pelo adversário, "
            "mando de campo e, quando disponível, "
            "o impacto da escalação. A expectativa "
            "de gols resultante é transformada em "
            "probabilidade pela distribuição de "
            "Poisson."
        )

    elif code == "btts_yes":
        explanation_type = "goals"

        conclusion = (
            "O modelo calcula separadamente a "
            "expectativa de gols de cada equipe. "
            "A partir dessas duas expectativas, "
            "estima a chance de ambos os times "
            "marcarem pelo menos uma vez."
        )

    elif code.startswith(
        "corners_"
    ):
        explanation_type = "corners"

        conclusion = (
            "A probabilidade é baseada principalmente "
            "nas médias recentes de escanteios "
            "produzidos e concedidos pelas duas "
            "equipes. A escalação é exibida como "
            "contexto, mas nesta versão ainda não "
            "altera diretamente o cálculo de "
            "escanteios."
        )

    elif code.startswith(
        "cards_"
    ):
        explanation_type = "cards"

        conclusion = (
            "A probabilidade é baseada principalmente "
            "no histórico recente de cartões das "
            "equipes e na combinação dessas médias. "
            "A escalação é exibida como contexto, "
            "mas nesta versão ainda não altera "
            "diretamente o cálculo de cartões."
        )

    else:
        explanation_type = "general"

        conclusion = (
            "O percentual é produzido pelo modelo "
            "estatístico StatPlay a partir do "
            "histórico disponível antes do jogo."
        )

    return {
        "home_form": home_form,
        "away_form": away_form,
        "home_lineup": home_lineup,
        "away_lineup": away_lineup,
        "adjustment": adjustment,
        "odds": best_odd(
            prediction
        ),
        "type": explanation_type,
        "conclusion": conclusion,
    }
