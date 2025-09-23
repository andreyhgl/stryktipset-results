import marimo

__generated_with = "0.15.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import json
    import datetime as datetime
    import os
    return datetime, mo, os, pd


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
    # README

    Make a collection of all the _[Stryktipset](https://spela.svenskaspel.se/stryktipset/)_ results, ~~either~~ in ~~json or~~ csv format.

    The results can be fetch via an API, URL: https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/4912/result. The `4912` is the identifier for a specific week. Collect the results from late 2021 when Premier league resumed post COVID.

    Save the results containing the following data: 

    1. Home team
    2. Away team
    3. Result (outcome): `1,X,2`
    4. Country (subset later for England to get Premier League)
    5. Date
    6. Draw number (unique identifier for the game week)
    """
    )
    return


@app.cell
def _():
    # The setup
    # Make work on a sub sample, scale up
    return


@app.cell
def _(pd):
    # fetch results from URL
    URL = "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/4912/result"
    page = pd.read_json(URL)
    return (page,)


@app.cell
def _(datetime, page, pd):
    # split the json
    events = page["result"]["events"]
    result = pd.json_normalize(events)

    # refactor, json_normalize(events, sep="_") # merge the keys with underscore

    drawNumber = page["result"]["drawNumber"]
    date = page["result"]["regCloseTime"]
    date = date.split("T")[0]
    date = datetime.datetime.strptime(date, "%Y-%m-%d").date()

    #print(drawNumber)
    #print(date)
    #print(result)
    #print(result.columns)
    return date, drawNumber, result


@app.cell
def _(date, drawNumber, result):
    # Extract home and away team names
    result["team.home"] = result["participants"].apply(lambda x: next(p["name"] for p in x if p["type"] == "home"))
    result["team.away"] = result["participants"].apply(lambda x: next(p["name"] for p in x if p["type"] == "away"))
    result["team.home.id"] = result["participants"].apply(lambda x: next(p["shortName"] for p in x if p["type"] == "home"))
    result["team.away.id"] = result["participants"].apply(lambda x: next(p["shortName"] for p in x if p["type"] == "away"))
    result["country"] = result["participants"].apply(
        lambda x: x[0]["countryName"] if x[0]["countryName"] == x[1]["countryName"]
        else f"{x[0]['countryName']}, {x[1]['countryName']}"
    )

    out = result.rename(columns={
        "eventDescription": "event",
        "outcomeScore.home": "score.home",
        "outcomeScore.away": "score.away"
    })
    out = out[["outcome", "score.home", "score.away", "team.home", "team.away", "team.home.id", "team.away.id", "country"]]

    out["date"] = date
    out["drawNumber"] = drawNumber

    #print(result[["eventDescription", "outcome", "outcomeScore.home", "outcomeScore.away", "home_team", "away_team", "home_team_short", "away_team_short", "country"]].to_string())
    #print(out[["event", "outcome", "score.home", "score.away", "team.home", "team.away", "team.home.id", "team.away.id", "country"]].to_string())
    print(out)
    return (out,)


@app.cell
def _(os, out):
    # save output
    filename = "results.csv"

    if not os.path.isfile(filename):
        # Write header if file does not exist
        print("file not found, generating one")
        out.to_csv(filename, index=False)
    else:
        # Append without header
        print("appends the results")
        out.to_csv(filename, mode="a", index=False, header=False)
    return


if __name__ == "__main__":
    app.run()
