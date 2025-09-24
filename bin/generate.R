#!/usr/bin/env Rscript

# randomise 3 values ( 0, 1, 2 ) 13 times
# in matrix form
# in stylish form

generate <- function(){
  # which rows are halfs?
  n <- 8
  half <- sort(sample(seq_len(13), n))

  # randomize a set of rows
  row <- c("1", "X", "2")
  dat <- sample(row, 13, replace = TRUE)

  # make a nice dataframe
  index <- list("1" = 1, "X" = 2, "2" = 3)
  mat <- matrix(nrow = 13, ncol = 3)
  mat[] <- ""
  
  for (i in seq_along(dat)){
    data <- if (i %in% half) c(sample(row[!row %in% dat[i]], 1), dat[i])
    mat[i, names(index) %in% dat[i]] <- dat[i]
  }

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