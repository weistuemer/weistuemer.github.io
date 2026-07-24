library(ggplot2)
library(dplyr)
library(sf)
library(rnaturalearth)
library(rnaturalearthdata)

# Daten einlesen und Koordinaten aufbereiten
# Pfad geht davon aus, dass das Skript aus scripts/scripts/ heraus laeuft
# (Datei liegt in scripts/data/Diphthongierung.csv, also eine Ebene hoch + data/)
df <- read.csv2("../data/Diphthongierung.csv", stringsAsFactors = FALSE)

df_map <- df %>% 
  filter(!is.na(X) & !is.na(Y)) %>%
  mutate(X = as.numeric(X), Y = as.numeric(Y))

# Weltkarte laden
world <- ne_countries(scale = "medium", returnclass = "sf")


# =========================================================
# KARTE 1: BÄNDE (MIT WUNSCHFARBEN UND GRÖSSEREM AUSSCHNITT)
# =========================================================
ggplot(data = world) +
  geom_sf(fill = "#f2f2f2", color = "darkgray") +
  
  geom_point(data = df_map, aes(x = X, y = Y, color = as.factor(Band)), 
             size = 2, alpha = 0.5) +
  
  # HIER IST DIE KORREKTUR: xlim bis 17.5 erweitert (für Wien und Umgebung)
  coord_sf(xlim = c(5.5, 17.5), ylim = c(46.0, 55.5), expand = FALSE) +
  
  scale_color_manual(
    name = "Band",
    values = c(
      "1" = "#1b9e77", 
      "2" = "#e6ab02", 
      "3" = "#7570b3", 
      "4" = "#e7298a", 
      "5" = "#66a61e", 
      "6" = "#d95f02"  
    )
  ) +
  
  theme_minimal() +
  labs(#title = "Räumliche Verteilung der Grimmschen Weistümer",
       #subtitle = "Farbliche Kennzeichnung nach Editionsband",
       x = "Längengrad", y = "Breitengrad")
       
ggsave("Karte_nach_Band.png", width = 8.5, height = 6, dpi = 300)

# =========================================================
# KARTE 2: DIPHTHONGIERUNG WEIN (î) - KUGELSICHER
# =========================================================
# Hinweis: Der fruehere erste Entwurf dieser Karte (Filter "Wein != """,
# einfache case_when-Klassifikation) hatte einen Syntaxfehler (fehlendes
# schliessendes Anfuehrungszeichen bei "#D55E00) und wurde entfernt, da er
# ohnehin von diesem robusteren Block ueberschrieben wurde.

# 1. Daten säubern (Leerzeichen an den Rändern entfernen)
df_wein <- df_map %>%
  filter(!is.na(Wein) & Wein != "") %>%
  mutate(Wein = trimws(Wein)) # Beseitigt versteckte Tippfehler

# 2. Karte zeichnen
ggplot(data = world) +
  geom_sf(fill = "#f2f2f2", color = "darkgray") +
  
  geom_point(data = df_wein, aes(x = X, y = Y, color = Wein, shape = Wein), 
             size = 2.5, alpha = 0.8) +
             
  coord_sf(xlim = c(5.5, 17.5), ylim = c(46.0, 55.5), expand = FALSE) +
  
  # Wir stellen 6 Farben bereit. Die ersten drei sind deine Wunschfarben!
  scale_color_manual(values = c("#5e3c99", "#e66101", "#b2abd2", "#a6dba0", "#008837", "#404040")) +
  
  # Wir stellen 6 Formen bereit, damit R für eine 4. Kategorie nicht abstürzt
  scale_shape_manual(values = c(16, 17, 15, 18, 3, 4)) +
  
  theme_minimal() +
  labs(#title = "Verteilung: mhd. î (Wein)",
       x = "Längengrad", y = "Breitengrad",
       color = "Variante", shape = "Variante")
       
ggsave("wein.png", width = 8.5, height = 6, dpi = 300)

# =========================================================
# KARTE 3: DIPHTHONGIERUNG HAUS (û) - KUGELSICHER
# =========================================================

# 1. Daten säubern (Leerzeichen an den Rändern entfernen)
df_haus <- df_map %>%
  filter(!is.na(Haus) & Haus != "") %>%
  mutate(Haus = trimws(Haus)) # Beseitigt versteckte Tippfehler wie "au " statt "au"

# 2. Karte zeichnen
ggplot(data = world) +
  geom_sf(fill = "#f2f2f2", color = "darkgray") +
  
  geom_point(data = df_haus, aes(x = X, y = Y, color = Haus, shape = Haus), 
             size = 2.5, alpha = 0.8) +
             
  coord_sf(xlim = c(5.5, 17.5), ylim = c(46.0, 55.5), expand = FALSE) +
  
  # Wir stellen 6 Farben bereit, falls es mehr als 3 Kategorien in der Spalte gibt.
  # Die ersten drei sind deine Wunschfarben!
  scale_color_manual(values = c("#5e3c99", "#e66101", "#b2abd2", "#a6dba0", "#008837", "#404040")) +
  
  # Wir stellen auch 6 Formen bereit, damit R nicht abstürzt
  scale_shape_manual(values = c(16, 17, 15, 18, 3, 4)) +
  
  theme_minimal() +
  labs(#title = "Verteilung: mhd. û (Haus)",
       x = "Längengrad", y = "Breitengrad",
       color = "Variante", shape = "Variante")

ggsave("haus.png", width = 8.5, height = 6, dpi = 300)

# =========================================================
# KARTE 4: REGIONALE ZUORDNUNG (AD HOC CLUSTER)
# =========================================================

# 1. Daten filtern und säubern
# Wir nutzen Region.eigene (so nennt R meist Spalten mit Leerzeichen)
# Falls R meckert, ändere "Region.eigene" in "`Region eigene`" (mit den Backticks)
df_region <- df_map %>%
  filter(!is.na(Region.eigene) & Region.eigene != "") %>%
  mutate(Region = trimws(Region.eigene)) # Leerzeichen abschneiden

# 2. Karte plotten
ggplot(data = world) +
  geom_sf(fill = "#f2f2f2", color = "darkgray") +
  
  geom_point(data = df_region, aes(x = X, y = Y, color = Region), 
             size = 2.5, alpha = 0.4) +
             
  coord_sf(xlim = c(5.5, 17.5), ylim = c(46.0, 55.5), expand = FALSE) +
  
  # 7 kontrastreiche Farben OHNE Gelb!
  scale_color_manual(
    name = "Eigene Region",
    values = c(
      "OOD"    = "#e41a1c", # Kräftiges Rot
      "WMD"    = "#377eb8", # Sattes Blau
      "MDT"    = "#4daf4a", # Grün
      "CH"     = "#984ea3", # Violett
      "Elsass" = "#ff7f00", # Dunkelorange
      "WOD"    = "#a65628", # Erdbraun
      "NDT"    = "#f781bf"  # Pink/Magenta
    )
  ) +
  
  theme_minimal() +
  labs(#title = "Dialektgeographische Zuordnung der Weistümer",
       #subtitle = "Ad-hoc-Klassifikation für die quantitative Auswertung",
       x = "Längengrad", y = "Breitengrad")

# 3. Speichern
ggsave("Karte_Regionen_Eigene.png", width = 8.5, height = 6, dpi = 300)