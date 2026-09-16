# Parses every chunk and inline expression of manuscript.qmd, and lists figure or table labels without a cross-reference and citation keys missing from references.bib. Run from the repository root.
src <- readLines("01.manuscript/manuscript.qmd"); op <- grep("^```\\{r", src); cl <- grep("^```\\s*$", src)
for (o in op) { e <- cl[cl > o][1]; b <- src[(o+1):(e-1)]; lab <- sub("#\\| label: ", "", grep("^#\\| label:", b, value = TRUE))
  r <- tryCatch({ parse(text = b[!grepl("^#\\|", b)]); "ok" }, error = function(err) conditionMessage(err)); cat(lab, r, "\n") }
inl <- unlist(regmatches(src, gregexpr("`r [^`]+`", src))); cat(length(inl), "inline expressions\n")
for (x in inl) tryCatch(parse(text = sub("^`r ", "", sub("`$", "", x))), error = function(e) cat("BAD", x, "\n"))
refs <- unique(sub("@", "", unlist(regmatches(src, gregexpr("@(fig|tbl)-[a-z-]+", src)))))
labs <- sub("#\\| label: ", "", grep("^#\\| label: (fig|tbl)-", src, value = TRUE))
cat("refs without label:", setdiff(refs, labs), "\nlabels without ref:", setdiff(labs, refs), "\n")
cites <- unique(sub("@", "", unlist(regmatches(src, gregexpr("@[A-Z][A-Za-z_]+_[0-9]{4}[a-z]?", src)))))
bib <- readLines("04.references/references.bib"); keys <- trimws(sub("^\\s*@[a-z]+\\{([^,]+),.*", "\\1", grep("^\\s*@[a-z]+\\{", bib, value = TRUE)))
cat("citations missing from bib:", setdiff(cites, keys), "\n")
