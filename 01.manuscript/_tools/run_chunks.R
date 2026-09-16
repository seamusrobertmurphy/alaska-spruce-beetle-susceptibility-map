# Run named R chunks of manuscript.qmd in order, from the repository root, the way a
# render would, without rendering. Use for checking a chunk after an edit.
#   Rscript 01.manuscript/_tools/run_chunks.R setup extents studyarea-context
# Chunk flags such as eval: false are ignored, so a named chunk always runs.
# POST, if set, is R code evaluated after the last chunk, for printing a result.
setwd(normalizePath(file.path(dirname(sub("^--file=", "", grep("^--file=", commandArgs(), value = TRUE))), "../..")))
src <- readLines("01.manuscript/manuscript.qmd")
op <- grep("^```\\{r", src); cl <- grep("^```\\s*$", src)
chunks <- lapply(op, function(o) { e <- cl[cl > o][1]; body <- src[(o + 1):(e - 1)]
  lab <- sub("^#\\|\\s*label:\\s*", "", grep("^#\\|\\s*label:", body, value = TRUE))
  list(label = if (length(lab)) lab[1] else NA, code = body[!grepl("^#\\|", body)]) })
labs <- vapply(chunks, `[[`, "", "label")
dup <- unique(labs[duplicated(labs) & !is.na(labs)]); if (length(dup)) warning("duplicate labels: ", paste(dup, collapse = ", "))
for (l in commandArgs(trailingOnly = TRUE)) {
  i <- match(l, labs); if (is.na(i)) stop("no chunk ", l)
  cat("\n==== chunk", l, format(Sys.time(), "%H:%M:%S"), "\n")
  eval(parse(text = chunks[[i]]$code), envir = globalenv())
}
post <- Sys.getenv("POST"); if (nzchar(post)) eval(parse(text = post), envir = globalenv())
