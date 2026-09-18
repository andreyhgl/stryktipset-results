"""Turn one draw's API result into a tidy DataFrame.

The column set and order here define the schema of results.csv.
"""

from __future__ import annotations

import datetime
import logging

import pandas as pd

log = logging.getLogger(__name__)

COLUMNS = [
    "outcome",
    "score_home",
    "score_away",
    "team_home",
    "team_away",
    "team_home_id",
    "team_away_id",
    "country",
    "date",
    "draw_number",
]

# A row is uniquely identified by the draw it belongs to and the fixture
KEY = ["draw_number", "team_home", "team_away"]

EVENTS_PER_DRAW = 13


def is_finished(result):
    """True when every event in the draw has an outcome (1, X or 2)."""
    events = result.get("events") or []
    if not events:
        return False
    return all(event.get("outcome") for event in events)


def _participant(participants, side, field, default=""):
    """Look up one field for the home or away side of an event."""
    for participant in participants:
        if participant.get("type") == side:
            return participant.get(field) or default
    return default


def _country(participants):
    """Country of the fixture; both countries if the teams differ."""
    countries = [p.get("countryName") for p in participants if p.get("type")]
    countries = [c for c in countries if c]
    if not countries:
        return ""
    if len(set(countries)) == 1:
        return countries[0]
    return ", ".join(countries)


def result_to_frame(result):
    """Flatten a draw's result section into a DataFrame with COLUMNS."""
    events = result["events"]
    if len(events) != EVENTS_PER_DRAW:
        log.warning(
            "Draw %s has %d events, expected %d",
            result.get("drawNumber"),
            len(events),
            EVENTS_PER_DRAW,
        )

    frame = pd.json_normalize(events, sep="_")

    participants = frame["participants"]
    frame["team_home"] = participants.apply(_participant, args=("home", "name"))
    frame["team_away"] = participants.apply(_participant, args=("away", "name"))
    # Some teams have no shortName; an empty cell is fine, we do not use them
    frame["team_home_id"] = participants.apply(
        _participant, args=("home", "shortName")
    )
    frame["team_away_id"] = participants.apply(
        _participant, args=("away", "shortName")
    )
    frame["country"] = participants.apply(_country)

    frame = frame.rename(
        columns={
            "outcomeScore_home": "score_home",
            "outcomeScore_away": "score_away",
        }
    )

    frame["date"] = parse_date(result["regCloseTime"])
    frame["draw_number"] = int(result["drawNumber"])

    # reindex, so a column the API omitted becomes NaN instead of KeyError
    return frame.reindex(columns=COLUMNS)


def parse_date(reg_close_time):
    """'2025-09-13T15:59:00' -> '2025-09-13' (ISO date, as a string)."""
    date = reg_close_time.split("T")[0]
    return datetime.date.fromisoformat(date).isoformat()


def empty_frame():
    """An empty frame with the right columns, for the no-data case."""
    return pd.DataFrame(columns=COLUMNS)
