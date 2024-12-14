# README

To generate a random stryktipset-rad, run generate.R

```sh
Rscript generate.R
```

<!-- 

todo:

+ how does 'beautifulsoup::find_all' work?

+ save last weeks correct row
+ allow for adding variables to generate.R: whole and half "gardering"

-->

## Conda environment


```sh
# create an environement
conda create -n stryket beautifulsoup4 urllib3 jupyterlab

# jump into the virual environment
conda activate stryket

# find packages
conda search <package-name>

# remove the environement
conda remove -n environment --all
```
