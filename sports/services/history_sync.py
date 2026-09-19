from datetime import datetime, timezone as dt_timezone

from sports.models import TeamMatchStats
from sports.services.statistics import (
    save_event_statistics,
)


def ensure_history(
    events,
    provider,
    min_matches=10,
    fetch_matches=15,
    pages=2,
):
    teams = {}

    for event in events:
        for team in (
            event.home_team,
            event.away_team,
        ):
            if team.external_id:
                teams[team.id] = team

    downloaded = 0
    reused = 0
    skipped_teams = 0
    no_stats = 0

    for team in teams.values():
        existing = (
            TeamMatchStats.objects
            .filter(
                team=team,
                event__status="finished",
            )
            .count()
        )

        if existing >= min_matches:
            skipped_teams += 1
            continue

        history = []
        seen = set()

        for page in range(pages):
            data = provider._get_web(
                f"team/{team.external_id}/events/last/{page}"
            ) or {}

            for raw in data.get(
                "events",
                [],
            ):
                event_id = raw.get("id")

                if (
                    not event_id
                    or event_id in seen
                ):
                    continue

                if (
                    raw.get("status", {})
                    .get("type")
                    != "finished"
                ):
                    continue

                seen.add(event_id)
                history.append(raw)

                if (
                    len(history)
                    >= fetch_matches
                ):
                    break

            if (
                len(history)
                >= fetch_matches
            ):
                break

        for raw in history:
            event, _ = provider._save_event(
                raw,
                team.sport,
            )

            if not event:
                continue

            if (
                TeamMatchStats.objects
                .filter(event=event)
                .count()
                == 2
            ):
                reused += 1
                continue

            stats = provider.get_statistics(
                event.external_id
            )

            if save_event_statistics(
                event,
                stats,
            ):
                downloaded += 1
            else:
                no_stats += 1

    return {
        "teams": len(teams),
        "teams_ready": skipped_teams,
        "downloaded": downloaded,
        "reused": reused,
        "no_stats": no_stats,
    }
