#!/usr/bin/env Rscript
# GAM-Effektplots aus mgcv für Wein und Haus.
# Aufruf: Rscript scripts/06_gam_effectplots_mgcv.R data/Diphthongierung.csv output/figures output/tables

suppressPackageStartupMessages({
  library(tidyverse)
  library(mgcv)
  library(viridisLite)
})

args <- commandArgs(trailingOnly = TRUE)
input_file <- ifelse(length(args) >= 1, args[1], "data/Diphthongierung.csv")
figdir <- ifelse(length(args) >= 2, args[2], "output/figures")
tabledir <- ifelse(length(args) >= 3, args[3], "output/tables")
dir.create(figdir, recursive = TRUE, showWarnings = FALSE)
dir.create(tabledir, recursive = TRUE, showWarnings = FALSE)

TIME_SLICES <- c(1400, 1500, 1600)
GRID_N <- 160

num_coord <- function(x) as.numeric(gsub(",", ".", as.character(x)))
num_year_exact <- function(x) suppressWarnings(as.numeric(as.character(x)))

prepare_gam_data <- function(df, lexem) {
  if (lexem == "Wein") {
    mono <- "i"; diph <- "ei"; var_col <- "Wein"
  } else {
    mono <- "u"; diph <- "au"; var_col <- "Haus"
  }
  df %>%
    mutate(
      Variante = .data[[var_col]],
      Diph_Bin = case_when(Variante == mono ~ 0, Variante == diph ~ 1, TRUE ~ NA_real_),
      Jahr_num = num_year_exact(`Jahr eigene`),
      X_num = num_coord(X),
      Y_num = num_coord(Y)
    ) %>%
    filter(!is.na(Diph_Bin), !is.na(Jahr_num), !is.na(X_num), !is.na(Y_num))
}

plot_for_lexem <- function(df, lexem) {
  d <- prepare_gam_data(df, lexem)
  m <- gam(
    Diph_Bin ~ te(X_num, Y_num, Jahr_num, d = c(2, 1)),
    data = d,
    family = binomial(link = "logit"),
    method = "REML"
  )

  xseq <- seq(quantile(d$X_num, 0.01), quantile(d$X_num, 0.99), length.out = GRID_N)
  yseq <- seq(quantile(d$Y_num, 0.01), quantile(d$Y_num, 0.99), length.out = GRID_N)
  grid_xy <- expand.grid(X_num = xseq, Y_num = yseq)

  png(file.path(figdir, paste0("gam_effektplot_", tolower(lexem), "_zeitschnitte.png")), width = 4800, height = 1600, res = 300)
  oldpar <- par(mfrow = c(1, length(TIME_SLICES)), mar = c(4.8, 4.8, 2.5, 1.2), oma = c(4.5, 0, 0, 4.5))
  on.exit({par(oldpar); dev.off()}, add = TRUE)

  cols <- viridis(100)
  for (yr in TIME_SLICES) {
    newdata <- grid_xy %>% mutate(Jahr_num = yr)
    newdata$prob <- predict(m, newdata = newdata, type = "response")
    z <- matrix(newdata$prob, nrow = length(xseq), ncol = length(yseq))
    image(xseq, yseq, z, col = cols, zlim = c(0, 1), xlab = "Längengrad", ylab = "Breitengrad", main = as.character(yr), cex.lab = 1.2, cex.axis = 1.0)
    contour(xseq, yseq, z, levels = c(0.25, 0.5, 0.75), add = TRUE, drawlabels = FALSE, col = "white", lwd = 1)
    near <- d %>% filter(Jahr_num >= yr - 25, Jahr_num <= yr + 25)
    points(near$X_num[near$Diph_Bin == 0], near$Y_num[near$Diph_Bin == 0], pch = 4, cex = 0.55)
    points(near$X_num[near$Diph_Bin == 1], near$Y_num[near$Diph_Bin == 1], pch = 1, cex = 0.55)
  }
  mtext("Weiße Konturen: 25 %, 50 %, 75 %. Punkte im Zeitfenster ±25 Jahre: x = monophthongisch, o = diphthongisch.", side = 1, outer = TRUE, line = 2.2, cex = 0.85, col = "gray30")

  invisible(tibble(Lexem = lexem, N = nrow(d), deviance_explained = summary(m)$dev.expl))
}

df <- read.csv(
  input_file,
  sep = ";",
  stringsAsFactors = FALSE,
  check.names = FALSE,
  na.strings = c("", "NA")
)
names(df) <- trimws(names(df))
df <- df[, !(is.na(names(df)) | names(df) == ""), drop = FALSE]
names(df) <- make.unique(names(df))
stats <- bind_rows(plot_for_lexem(df, "Wein"), plot_for_lexem(df, "Haus"))
write.csv(stats, file.path(tabledir, "gam_effectplot_model_stats.csv"), row.names = FALSE)
print(stats)
