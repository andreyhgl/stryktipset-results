"""Command line entry point: python -m stryktipset

With no arguments it continues where results.csv stopped and fetches
every finished draw up to the most recent one. That covers both the
one-off backfill (empty file) and the weekly update (full file).
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

import pandas as pd

from . import api, parse, storage

log = logging.getLogger("stryktipset")

FIRST_DRAW = 4631  # first draw of January 2020
DEFAULT_OUTPUT = "results.csv"
SLEEP_SECONDS = 0.5
MAX_MISSES = 5
LOOKAHEAD = 5


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m stryktipset", description=__doc__
    )
    parser.add_argument(
        "--start",
        type=int,
        help="first draw number (default: one past the last stored draw)",
    )
    parser.add_argument(
        "--end",
        type=int,
        help="last draw number (default: latest draw known to the API)",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"CSV to update (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=SLEEP_SECONDS,
        help="seconds to wait between API calls (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="fetch and report, but do not write the CSV",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="log every request",
    )
    return parser.parse_args(argv)


def resolve_range(args, existing):
    """Work out which draw numbers to ask for."""
    start = args.start
    if start is None:
        last = storage.last_drawnumber(existing)
        start = FIRST_DRAW if last is None else last + 1
        log.info("Last stored draw: %s", last)

    end = args.end
    if end is None:
        end = api.latest_drawnumber()
        if end is None:
            end = start + LOOKAHEAD
            log.info("No open draws listed, probing up to %d", end)
        else:
            log.info("Latest draw known to the API: %s", end)

    return start, end


def collect(start, end, sleep):
    """Fetch every finished draw in the range, skipping the rest."""
    frames = []
    misses = 0

    for drawnumber in range(start, end + 1):
        result = api.fetch_result(drawnumber)

        if result is None:
            misses += 1
            if misses >= MAX_MISSES:
                log.warning(
                    "%d draws in a row unavailable, stopping at %d",
                    misses,
                    drawnumber,
                )
                break
            time.sleep(sleep)
            continue

        misses = 0
        if not parse.is_finished(result):
            log.info("Draw %d is not finished yet, skipping", drawnumber)
            time.sleep(sleep)
            continue

        frames.append(parse.result_to_frame(result))
        log.info("Draw %d collected", drawnumber)
        time.sleep(sleep)

    if not frames:
        return parse.empty_frame()
    return pd.concat(frames, ignore_index=True)


def main(argv=None):
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    existing = storage.read_results(args.output)

    try:
        start, end = resolve_range(args, existing)
    except api.ApiError as err:
        log.error("Could not work out the draw range: %s", err)
        return 1

    if start > end:
        log.info("Nothing to do, %s is up to date", args.output)
        return 0

    log.info("Fetching draws %d-%d", start, end)
    try:
        new = collect(start, end, args.sleep)
    except api.ApiError as err:
        log.error("Aborted: %s", err)
        return 1

    if new.empty:
        log.info("No finished draws found, %s unchanged", args.output)
        return 0

    merged = storage.merge(existing, new)
    added = len(merged) - len(existing)
    log.info(
        "%d new rows (%d draws), %d rows in total",
        added,
        new["draw_number"].nunique(),
        len(merged),
    )

    if args.dry_run:
        log.info("Dry run, not writing %s", args.output)
        return 0

    storage.write_results(merged, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
