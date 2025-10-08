# README

This project gathers all the football results from [stryktipset](https://spela.svenskaspel.se/stryktipset) and holds all the data inside a `csv`-file.

## Approach

+ The results for each week are found in json format at [Svenskaspels API URL](api.spela.svenskaspel.se). https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/4912/result
  + `.../draw/1/stryktipset/...` = stryktipset
  + `.../draws/4912/...` = week ID
  + `.../result` = the results
+ `bin/gather_results.py` extracts the results
+ iterate over the weeks unique identifier (`drawNumber`)

<details>
  <summary>Environment setup</summary><br>

  > Assumes the packages manager Conda is already installed on the system
  
  Python is ran inside a conda environment with all the nessessary dependencies installed and contained within. The environment can be setup in multiple ways, here the environment is built from a single file: `environment.yml`

  ```yml
  # environment.yml
  
  name: stryket
  channels:
    - conda-forge
  dependencies:
    - python=3.13
    - marimo=0.16.1
    - pandas
    - numpy
  ```
  
  Install the dependencies (create environment) and "enter" the environment (activate)

  ```sh
  conda env create -f environment.yml -n stryket
  conda activate stryket
  
  # ~ ~ In case new dependancies are needed: ~ ~
  # 1. add them to environmental.yml
  # 2. remove the environment
  # > conda env remove -n <env-name>
  
  # 3. install from file again
  # > conda env create -f environment.yml
  ```
  
  Start a python notebook (marimo)
  
  ```sh
  marimo edit notebook.py
  ```
</details>

## The code

+ `bin/gather_results.py`, gathers results from early 2020 (`drawnumber = 4631`) to september 2025 (`drawnumber = 4921`) and saves to `results.csv`
+ `bin/fetch_results.py`, pings the API ones a week and appends the `results.csv`