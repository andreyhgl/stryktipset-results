#!/usr/bin/env python

import pandas as pd
import json
import datetime as datetime
import os
#import sys

def fetch_data_from_api(drawnumber):
  URL = "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/" + str(drawnumber) + "/result"
  print("Using URL: " + URL)
  page = pd.read_json(URL)
  return(page)

def curate_results(page):
  # split the json
  events = page["result"]["events"]

  # merge the keys with underscore
  result = pd.json_normalize(events, sep="_")
  
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

def save_results(out):
  filename = "results.csv"

  if not os.path.isfile(filename):
      # Write header if file does not exist
      print("File not found, generating one")
      out.to_csv(filename, index=False)
  else:
      # Append without header
      print("Appending the results")
      out.to_csv(filename, mode="a", index=False, header=False)

# 2020 start of January
start_date = 4631

# 2025 end of September
end_date = 4921

for drawnumber in range(start_date, end_date + 1):

	page = fetch_data_from_api(drawnumber)
	out = curate_results(page)
	save_results(out)