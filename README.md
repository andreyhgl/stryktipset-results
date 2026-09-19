[![Update results](https://github.com/andreyhgl/stryktipset-results/actions/workflows/update_results.yml/badge.svg)](https://github.com/andreyhgl/stryktipset-results/actions/workflows/update_results.yml/badge.svg)

# stryktipset-results

This project gathers all the football results from
[stryktipset](https://spela.svenskaspel.se/stryktipset) and holds all
the data inside `results.csv`. The file is updated automatically once a
week by a GitHub Action running inside the
[py-webscrape](https://github.com/andreyhgl/py-webscrape) Docker image.

Svenska Spel publishes each week's results as JSON:
<https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/4912/result>

- `.../draw/1/stryktipset/...` = stryktipset
- `.../draws/4912/...` = week ID (`drawNumber`)
- `.../result` = the results

## The data

One row per match, 13 matches per draw:

| column | description |
| --- | --- |
| `outcome` | `1`, `X` or `2` |
| `score_home`, `score_away` | final score |
| `team_home`, `team_away` | team names |
| `team_home_id`, `team_away_id` | short names, empty when the API has none |
| `country` | both countries listed when the teams differ |
| `date` | `regCloseTime` of the draw, as `YYYY-MM-DD` |
| `draw_number` | unique identifier of the game week |

## Running it

```
python -m stryktipset
```

With no arguments the script looks at the highest `draw_number` already
in `results.csv`, asks the API what the newest draw is, and fetches
everything in between. That one command is therefore both the initial
backfill (empty file, starts at draw 4631 = January 2020) and the
weekly top-up (full file, fetches one or two draws).

<details>
  <summary>Why January 2020?</summary>

  1. Post-covid football changed number of substitutions, 3 => 5.
  2. Teams change over time, teams from 2020 is still kinda same team in terms of strategy, budget, management.
</details>

```
--start N      first draw number (default: one past the last stored draw)
--end N        last draw number (default: latest draw known to the API)
--output PATH  CSV to update (default: results.csv)
--sleep S      seconds between API calls (default: 0.5)
--dry-run      fetch and report, but do not write
-v/--verbose   log every request
```

---

# The code

> [!NOTE]
> This project is an effort to learn Python. Hence, there will be a lot of
> somewhat "un-necessesary" comments and steps.

The program is a pipeline with four stages:

```
API (JSON) --> fetch --> parse --> merge with old rows --> write CSV
              api.py    parse.py       storage.py         storage.py
```

Each stage is its own file, and each file has one job. Separate the
code that talks to the outside world (network, disk) from the code
that only transforms data. Most code bugs occur in the latter stage.
The `tests/test_pipeline.py` tests dummy data and requires no internet
connection.

## Why a folder instead of one script?

```
stryktipset/
  __init__.py    # makes the folder a "package"
  api.py         # HTTP: fetch JSON from Svenska Spel
  parse.py       # JSON -> table (defines the CSV schema)
  storage.py     # read / merge / write results.csv
  __main__.py    # the command line program that wires it together
```

A folder with an `__init__.py` inside is a **package**: a module made
of modules. `import stryktipset` runs `__init__.py`, and the files
inside can import each other with `from . import api` ("from the
package I live in, import api").

`__main__.py` has a magic file: it listens to `stryktipset` and runs the
program.

```sh
python -m stryktipset
```

`-m` means "find this name the same way `import` would, then run it as
the main program". For a package, Python runs its `__main__.py`. You
have used this before with `python -m venv` and `python -m pytest`.
Note that you must stand in the repository root, because that is what
makes the `stryktipset/` folder findable.

## api.py

Fetch the results. The idea with this script is to wrap every request in a
routine.

```python
response = session.get(url, timeout=timeout)
```

- `session` is a `requests.Session()` created once at the top of the
  file. It reuses the connection between calls, which is faster and
  politer than reconnecting for every draw.
- `timeout=30` means "give up after 30 seconds". Without it, one hung
  request could freeze the program forever. Always set a timeout.

<details>
  <summary>Return status</summary>

  Then the status code is inspected:

  - **404** means "this draw number does not exist". That is a normal,
    expected situation (there are gaps in the numbering), so it gets its
    own exception, `DrawNotFound`, and the caller turns it into `None`.
  - **other 4xx** means our request is wrong. Retrying an identical
    wrong request cannot help, so it fails immediately.
  - **5xx / timeout / connection error** means the *server* had a bad
    moment. These are worth retrying, so the loop sleeps and tries
    again: 2 s, then 4 s, then 8 s (`backoff ** attempt`). Waiting longer
    each time is called **exponential backoff** and stops us from
    hammering a struggling server.
  
  Also, define exception classes to catch failures

  ```python
  class ApiError(Exception): ...
  class DrawNotFound(ApiError): ...
  ```
</details>

## parse.py

The API answers with a nested JSON structure, parse it to a readable table:

```json
{"result": {"drawNumber": 4912,
            "regCloseTime": "2026-01-01T13:33:37",
            "events": [{"outcome": "1",
                        "outcomeScore": {"home": 2, "away": 0},
                        "participants": [{"type": "home", "name": "Liverpool", ...},
                                         {"type": "away", "name": "Arsenal", ...}]},
                       ...12 more...]}}
```

- pandas `pd.json_normalize(events, sep="_")` flattens each event's nested
   dicts into columns, so `outcomeScore.home` becomes a column named
   `outcomeScore_home`.
- For `participants` use `.apply()` to call the function on each cell 
- **The schema.** `COLUMNS` is the single list that decides which
  columns `results.csv` has and in which order. Every frame is passed
  through `frame.reindex(columns=COLUMNS)` on the way out, which also
  means a column the API forgot becomes an empty cell instead of a
  `KeyError`.
- `is_finished()` only returns non-empty outcomes, all games must be finished.

## storage.py

Save the outcomes to `results.csv`. The correct way to add new results is to read => merge => rewrite the file. Appending need many safe-guards, like not running the script twice and failed runs that end mid write. This idempotence way of writting a program ensure that running program multiple times produces the same results.

<!-- fortsätt här -->

```python
combined = pd.concat([existing, new], ignore_index=True)
combined = combined.drop_duplicates(subset=KEY, keep="last")
combined = combined.sort_values("draw_number", kind="stable")
```

- `KEY = ["draw_number", "team_home", "team_away"]` uniquely
  identifies a row (a fixture within a week). If the same draw is
  fetched twice, `keep="last"` means the fresh row silently replaces
  the stored one — which also means a *corrected* result replaces the
  wrong one instead of sitting next to it.
- `kind="stable"` a sort keeping the rows that compare equal in their original
  order, so the 13 matches inside a draw stay in match order 1–13 while the
  draws themselves get sorted.

Finally, write to a temp file first, then `os.replace` swaps it into place in
one atomic step. If the program dies mid-write, the half-written file
is the temp file; `results.csv` is either the complete old version or
the complete new one, never garbage in between.

```python
frame.to_csv(temporary, index=False)
os.replace(temporary, path)
```

## \_\_main\_\_.py

This file contains no data logic at all. It:

1. parses command line flags with `argparse` (which also generates
   `--help` for free),
2. sets up `logging` — like `print()`, but with levels, so `-v` can
   switch the noise on and off without touching the other files,
3. works out the draw range: last stored draw + 1 up to the newest
   draw the API reports,
4. loops over the range, skipping unfinished draws, and gives up after
   5 *consecutive* missing draws (a single hole in the numbering
   should not end the run; five in a row means we ran off the end),
5. returns an **exit code**: `0` for success, `1` for failure.
   `sys.exit(main())` hands that number to the operating system.
   Humans never look at it — but GitHub Actions does, and marks the
   run red when it is not 0.

A pattern worth noticing throughout: functions *return* values and
*raise* exceptions; only `__main__.py` prints, logs and exits. That is
what keeps every other file reusable and testable.

## tests/

`tests/test_pipeline.py` builds tiny fake API responses (a dict that
looks like one draw) and checks the pipeline against them: the schema
comes out right, unfinished draws are rejected, merging twice does not
duplicate, a corrected score wins, a CSV round-trip is stable. Run
them with:

```sh
python -m pytest
```

Further sanity checks:

```sh
python -m stryktipset --start 4940 --end 4945 --output /tmp/test.csv -v
head /tmp/test.csv
```

---

# Automation

`.github/workflows/update_results.yml` runs every Sunday-Wednesday at 06:00 UTC
(games finish on Saturay), and can also be started by
hand from the Actions tab, optionally with a `start`/`end` draw
number.

## The Docker image

The job does not install anything. Instead every step runs inside

```yaml
container:
  image: ghcr.io/andreyhgl/py-webscrape:latest
```

[py-webscrape](https://github.com/andreyhgl/py-webscrape) is a small
image built on `python:3.12-slim` with `pandas`, `requests` and `git`
already installed, rebuilt automatically on every push to that repo.
Using it here means:

- no `setup-python`, no `pip install` — the environment is baked in
  and identical on every run,
- the same environment can be used locally:

  ```
  docker run -it --rm -v $(pwd):/app -w /app \
    ghcr.io/andreyhgl/py-webscrape python -m stryktipset
  ```

Two container-specific details in the workflow:

- `git config --global --add safe.directory "$GITHUB_WORKSPACE"` —
  inside the container the checked-out files are owned by a different
  user, and modern git refuses to work in such a directory until it is
  marked safe. Without this line the commit step fails with a
  "dubious ownership" error.
- the ghcr package must be **public** (py-webscrape repo → package
  settings → visibility), otherwise uncomment the `credentials:` block
  so the job can log in and pull it.

## The update-and-commit dance

```yaml
- run: python -m stryktipset --output results.csv
- run: |
    if [ ! -f results.csv ]; then
      echo "::error::results.csv is missing"
      exit 1
    fi

    git add results.csv

    if git diff --quiet -- results.csv; then
      echo "No new results, nothing to commit"
      exit 0
    fi
    git add results.csv
    git commit -m "data: update results (...)"
    git push
```

`git diff --quiet` exits with 0 when nothing changed, so on a week
with no finished draw the job simply ends without a commit. Pushing
requires the workflow to have write access: **Settings → Actions →
General → Workflow permissions → Read and write permissions** (the
`permissions: contents: write` line in the workflow asks for it, the
repo setting allows it).

One GitHub quirk to know about: scheduled workflows are paused in
repositories with no activity for 60 days. The weekly commit itself
counts as activity, so this only bites if the API returns nothing new
for two months straight.

---

# Local development

Either use the Docker image (see above), or the conda environment,
which additionally carries `marimo` for exploratory work in
`notebook.py`:

```
conda env create -f environment.yml -n stryket
conda activate stryket
```

`requirements.txt` lists the minimal packages (`pandas`, `requests`,
`pytest`) for anyone who prefers a plain virtualenv.
