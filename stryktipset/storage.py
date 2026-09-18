"""Read, merge and write results.csv.

Writing is a full rewrite rather than an append: that makes the whole
pipeline idempotent, so re-running it (or running it twice in the same
week) can never duplicate or half-write rows.
"""

from __future__ import annotations

import logging
import os
import tempfile

import pandas as pd

from .parse import COLUMNS, KEY, empty_frame

log = logging.getLogger(__name__)


def read_results(path):
    """Load results.csv, or an empty frame if it does not exist yet."""
    if not os.path.isfile(path):
        log.info("%s does not exist yet, starting from scratch", path)
        return empty_frame()

    frame = pd.read_csv(path, dtype={"draw_number": "Int64"})
    missing = [column for column in COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"{path} is missing columns: {missing}")
    return frame.reindex(columns=COLUMNS)


def last_drawnumber(frame):
    """Highest draw number in the frame, or None when it is empty."""
    if frame.empty or frame["draw_number"].isna().all():
        return None
    return int(frame["draw_number"].max())


def merge(existing, new):
    """Combine old and new rows, newest winning, sorted by draw number.

    Duplicates are resolved on (draw_number, team_home, team_away), so a
    draw that is fetched again - for instance after a corrected score -
    replaces the stored rows instead of being appended next to them.
    """
    frames = [f for f in (existing, new) if not f.empty]
    if not frames:
        return empty_frame()

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(subset=KEY, keep="last")
    # stable sort keeps the API's match order (1-13) inside each draw
    combined = combined.sort_values("draw_number", kind="stable")
    return combined.reset_index(drop=True)


def write_results(frame, path):
    """Write the frame to path atomically (temp file, then replace)."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)

    handle, temporary = tempfile.mkstemp(dir=directory, suffix=".csv")
    os.close(handle)
    try:
        frame.to_csv(temporary, index=False)
        os.replace(temporary, path)
    except BaseException:
        if os.path.exists(temporary):
            os.remove(temporary)
        raise
    log.info("Wrote %d rows to %s", len(frame), path)
