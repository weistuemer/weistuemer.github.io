#!/usr/bin/env Rscript
# Kombiniertes binomiales GAM für Wein und Haus.
# Mischformen werden ausgeschlossen.
# Aufruf: Rscript scripts/05_combined_gam_wein_haus.R data/Diphthongierung.csv output/tables

suppressPackageStartupMessages({
  library(tidyverse)
  library(mgcv)
})

args <- commandArgs(trailingOnly = TRUE)
input_file <- ifelse(length(args) >= 1, args[1], "data/Diphthongierung.csv")
outdir <- ifelse(length(args) >= 2, args[2], "output/tables")
dir.create(outdir, recursive = TRUE, showWarnings = FALSE)

num_coord <- function(x) as.numeric(gsub(",", ".", as.character(x)))
num_year_exact <- function(x) suppressWarnings(as.numeric(as.character(x)))

daten_wide <- read.csv(
  input_file,
  sep = ";",
  stringsAsFactors = FALSE,
  check.names = FALSE,
  na.strings = c("", "NA")
)
names(daten_wide) <- trimws(names(daten_wide))
daten_wide <- daten_wide[, !(is.na(names(daten_wide)) | names(daten_wide) == ""), drop = FALSE]
names(daten_wide) <- make.unique(names(daten_wide))

daten_long <- daten_wide %>%
  filter(!is.na(Wein) | !is.na(Haus)) %>%
  pivot_longer(
    cols = c(Wein, Haus),
    names_to = "Lexem",
    values_to = "Variante",
    values_drop_na = TRUE
  )

daten_vorbereitet <- daten_long %>%
  mutate(
    Diph_Bin = case_when(
      Variante %in% c("i", "u") ~ 0,
      Variante %in% c("ei", "au") ~ 1,
      Variante %in% c("i_ei", "u_au", "i/ei", "u/au") ~ 0.5,
      TRUE ~ NA_real_
    ),
    Jahr_num = num_year_exact(`Jahr eigene`),
    X_num = num_coord(X),
    Y_num = num_coord(Y),
    Lexem_fac = factor(Lexem)
  )

daten_modell <- daten_vorbereitet %>%
  filter(!is.na(X_num), !is.na(Y_num), !is.na(Jahr_num)) %>%
  filter(Diph_Bin %in% c(0, 1))

modell_kombiniert <- gam(
  Diph_Bin ~ Lexem_fac + te(X_num, Y_num, Jahr_num, by = Lexem_fac),
  data = daten_modell,
  family = binomial(link = "logit"),
  method = "REML"
)

s <- summary(modell_kombiniert)
write.csv(daten_modell, file.path(outdir, "gam_combined_data_binary.csv"), row.names = FALSE)

stats <- tibble(
  N = nrow(daten_modell),
  N_wein = sum(daten_modell$Lexem == "Wein"),
  N_haus = sum(daten_modell$Lexem == "Haus"),
  N_mono = sum(daten_modell$Diph_Bin == 0),
  N_diph = sum(daten_modell$Diph_Bin == 1),
  deviance_explained = s$dev.expl,
  lexem_p_value = ifelse(nrow(s$p.table) >= 2, s$p.table[2, ncol(s$p.table)], NA_real_)
)
write.csv(stats, file.path(outdir, "gam_combined_model_stats.csv"), row.names = FALSE)

sink(file.path(outdir, "gam_combined_summary.txt"))
print(s)
sink()

print(stats)
