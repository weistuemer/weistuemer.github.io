#!/usr/bin/env Rscript
# Getrennte binomiale GAMs für Wein und Haus.
# Mischformen werden ausgeschlossen.
# Aufruf: Rscript scripts/04_separate_gams_wein_haus.R data/Diphthongierung.csv output/tables

suppressPackageStartupMessages({
  library(tidyverse)
  library(mgcv)
})

args <- commandArgs(trailingOnly = TRUE)
input_file <- ifelse(length(args) >= 1, args[1], "data/Diphthongierung.csv")
outdir <- ifelse(length(args) >= 2, args[2], "output/tables")
dir.create(outdir, recursive = TRUE, showWarnings = FALSE)

read_data <- function(path) {
  df <- read.csv(
    path,
    sep = ";",
    stringsAsFactors = FALSE,
    check.names = FALSE,
    na.strings = c("", "NA")
  )
  names(df) <- trimws(names(df))
  df <- df[, !(is.na(names(df)) | names(df) == ""), drop = FALSE]
  names(df) <- make.unique(names(df))
  df
}

num_coord <- function(x) as.numeric(gsub(",", ".", as.character(x)))
num_year_exact <- function(x) suppressWarnings(as.numeric(as.character(x)))

prepare_gam_data <- function(df, lexem) {
  if (lexem == "Wein") {
    mono <- "i"; diph <- "ei"; var_col <- "Wein"
  } else if (lexem == "Haus") {
    mono <- "u"; diph <- "au"; var_col <- "Haus"
  } else {
    stop("Unbekanntes Lexem")
  }

  df %>%
    mutate(
      Variante = .data[[var_col]],
      Diph_Bin = case_when(
        Variante == mono ~ 0,
        Variante == diph ~ 1,
        TRUE ~ NA_real_
      ),
      Jahr_num = num_year_exact(`Jahr eigene`),
      X_num = num_coord(X),
      Y_num = num_coord(Y)
    ) %>%
    filter(!is.na(Diph_Bin), !is.na(Jahr_num), !is.na(X_num), !is.na(Y_num))
}

fit_one <- function(df, lexem) {
  d <- prepare_gam_data(df, lexem)
  m <- gam(
    Diph_Bin ~ te(X_num, Y_num, Jahr_num, d = c(2, 1)),
    data = d,
    family = binomial(link = "logit"),
    method = "REML"
  )
  s <- summary(m)
  sm <- as.data.frame(s$s.table)
  out <- tibble(
    Lexem = lexem,
    N = nrow(d),
    N_mono = sum(d$Diph_Bin == 0),
    N_diph = sum(d$Diph_Bin == 1),
    edf = sm$edf[1],
    chi_sq = sm$Chi.sq[1],
    p_value = sm$`p-value`[1],
    deviance_explained = s$dev.expl
  )
  list(data = d, model = m, stats = out)
}

df <- read_data(input_file)
res_wein <- fit_one(df, "Wein")
res_haus <- fit_one(df, "Haus")

stats <- bind_rows(res_wein$stats, res_haus$stats)
write.csv(stats, file.path(outdir, "gam_separate_model_stats.csv"), row.names = FALSE)
write.csv(res_wein$data, file.path(outdir, "gam_data_wein_binary.csv"), row.names = FALSE)
write.csv(res_haus$data, file.path(outdir, "gam_data_haus_binary.csv"), row.names = FALSE)

sink(file.path(outdir, "gam_separate_summaries.txt"))
cat("=== WEIN ===\n")
print(summary(res_wein$model))
cat("\n=== HAUS ===\n")
print(summary(res_haus$model))
sink()

print(stats)
