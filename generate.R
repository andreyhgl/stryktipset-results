#!/usr/bin/env Rscript

# randomise 3 values ( 0, 1, 2 ) 13 times
# in matrix form
# in stylish form

generate <- function(){
  dat <- matrix(nrow = 13, ncol = 3)
  dat[] <- ""

  for (i in seq_len(nrow(dat))){
    index <- list("1" = 1, "X" = 2, "2" = 3)
    row <- sample(3, 1)

    dat[i, row] <- names(index)[row]
  }
  dat <- data.frame(dat)
  names(dat) <- NULL
  show(dat)
}

generate()