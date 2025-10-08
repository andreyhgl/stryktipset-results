import marimo

__generated_with = "0.16.1"
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
def _(datetime, os, out, pd):
    # fetch results from API with a unique draw number
    def fetch_data_from_api(drawnumber):
        URL = "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/" + drawnumber + "/result"
        print("Using URL: " + URL)
        page = pd.read_json(URL)
        return(page)

    def curate_results(page):
        # split the json
        events = page["result"]["events"]
        result = pd.json_normalize(events, sep="_")
    
        # refactor, json_normalize(events, sep="_") # merge the keys with underscore

        # Extract home and away team names
        result["team_home"] = result["participants"].apply(lambda x: next(p["name"] for p in x if p["type"] == "home"))
        result["team_away"] = result["participants"].apply(lambda x: next(p["name"] for p in x if p["type"] == "away"))

        # Extract home and away team IDs
        # Note, some teams lack shortName format. Use NaN for those, they are not interesting anyway
        result["team_home_id"] = result["participants"].apply(
            lambda x: ", ".join(p.get("shortName", "NaN") for p in x if p["type"] == "home")
        )
        result["team_away_id"] = result["participants"].apply(
            lambda x: ", ".join(p.get("shortName", "NaN") for p in x if p["type"] == "away")
        )
        #result["team_home_id"] = result["participants"].apply(lambda x: next(p["shortName"] for p in x if p["type"] == "home"))
        #result["team_away_id"] = result["participants"].apply(lambda x: next(p["shortName"] for p in x if p["type"] == "away"))
    
        # Extract country
        result["country"] = result["participants"].apply(
            lambda x: x[0]["countryName"] if x[0]["countryName"] == x[1]["countryName"]
            else f"{x[0]['countryName']}, {x[1]['countryName']}"
        )

        out = result.rename(columns={
            "eventDescription": "event",
            "outcomeScore_home": "score_home",
            "outcomeScore_away": "score_away"
        })
        out = out[["outcome", "score_home", "score_away", "team_home", "team_away", "team_home_id", "team_away_id", "country"]]

        # add date column w/ date in datetime format
        date = page["result"]["regCloseTime"]
        date = date.split("T")[0]
        date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        out["date"] = date
        out["draw_number"] = page["result"]["drawNumber"]
        #print(out)
        return(out)

    def save_results():
        filename = "results.csv"

        if not os.path.isfile(filename):
            # Write header if file does not exist
            print("File not found, generating one")
            out.to_csv(filename, index=False)
        else:
            # Append without header
            print("Appending the results")
            out.to_csv(filename, mode="a", index=False, header=False)
    return curate_results, fetch_data_from_api


@app.cell
def _(curate_results, fetch_data_from_api):
    drawnumber = "4697"
    page = fetch_data_from_api(drawnumber)
    out = curate_results(page)
    #print(out)
    #save_results(out)
    return (out,)


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
