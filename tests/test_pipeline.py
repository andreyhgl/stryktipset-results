"""Tests for the parsing and storage logic (no network needed)."""

import pandas as pd
import pytest

from stryktipset import parse, storage


def event(home, away, outcome="1", score=(1, 0), short=True):
    return {
        "eventDescription": f"{home} - {away}",
        "outcome": outcome,
        "outcomeScore": {"home": score[0], "away": score[1]},
        "participants": [
            {
                "type": "home",
                "name": home,
                "countryName": "England",
                **({"shortName": home[:3].upper()} if short else {}),
            },
            {
                "type": "away",
                "name": away,
                "countryName": "England",
                "shortName": away[:3].upper(),
            },
        ],
    }


def draw(drawnumber=4900, events=None, date="2025-09-13T15:59:00"):
    return {
        "drawNumber": drawnumber,
        "regCloseTime": date,
        "events": events if events is not None else [event("Arsenal", "Chelsea")],
    }


def test_result_to_frame_has_the_expected_schema():
    frame = parse.result_to_frame(draw())
    assert list(frame.columns) == parse.COLUMNS
    row = frame.iloc[0]
    assert row["team_home"] == "Arsenal"
    assert row["team_away"] == "Chelsea"
    assert row["team_home_id"] == "ARS"
    assert row["outcome"] == "1"
    assert row["score_home"] == 1
    assert row["country"] == "England"
    assert row["date"] == "2025-09-13"
    assert row["draw_number"] == 4900


def test_missing_short_name_becomes_empty():
    events = [event("Some Team", "Chelsea", short=False)]
    frame = parse.result_to_frame(draw(events=events))
    assert frame.iloc[0]["team_home_id"] == ""


def test_country_lists_both_when_teams_differ():
    result = draw()
    result["events"][0]["participants"][1]["countryName"] = "Wales"
    frame = parse.result_to_frame(result)
    assert frame.iloc[0]["country"] == "England, Wales"


def test_is_finished():
    assert parse.is_finished(draw())
    assert not parse.is_finished(draw(events=[event("A", "B", outcome="")]))
    assert not parse.is_finished(draw(events=[]))


def test_merge_deduplicates_and_keeps_the_newest_row():
    old = parse.result_to_frame(draw(4900))
    corrected = parse.result_to_frame(
        draw(4900, events=[event("Arsenal", "Chelsea", outcome="X", score=(1, 1))])
    )
    merged = storage.merge(old, corrected)
    assert len(merged) == 1
    assert merged.iloc[0]["outcome"] == "X"


def test_merge_sorts_by_draw_number_but_keeps_match_order():
    later = parse.result_to_frame(
        draw(4901, events=[event("Leeds", "Burnley"), event("Fulham", "Brentford")])
    )
    earlier = parse.result_to_frame(draw(4900))
    merged = storage.merge(later, earlier)
    assert list(merged["draw_number"]) == [4900, 4901, 4901]
    assert list(merged["team_home"]) == ["Arsenal", "Leeds", "Fulham"]


def test_round_trip_through_csv_is_stable(tmp_path):
    path = tmp_path / "results.csv"
    frame = parse.result_to_frame(draw())
    storage.write_results(frame, str(path))

    reloaded = storage.read_results(str(path))
    assert list(reloaded.columns) == parse.COLUMNS
    assert storage.last_drawnumber(reloaded) == 4900

    # merging a file with itself must not grow it
    merged = storage.merge(reloaded, parse.result_to_frame(draw()))
    assert len(merged) == 1


def test_read_results_missing_file(tmp_path):
    frame = storage.read_results(str(tmp_path / "nope.csv"))
    assert frame.empty
    assert list(frame.columns) == parse.COLUMNS
    assert storage.last_drawnumber(frame) is None


def test_read_results_rejects_a_wrong_schema(tmp_path):
    path = tmp_path / "bad.csv"
    pd.DataFrame({"foo": [1]}).to_csv(path, index=False)
    with pytest.raises(ValueError):
        storage.read_results(str(path))
