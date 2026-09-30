document.addEventListener("DOMContentLoaded", function () {
    let dataset = [];
    // Globale Variablen für Karte und Marker-Gruppe
    let map;
    let markers = L.markerClusterGroup(); // Marker Cluster Group für bessere Performance

    const md = window.markdownit({ html: true }).use(window.markdownitFootnote);

    fetch("data.json")
        .then(response => response.json())
        .then(data => {
            dataset = data;
            kategorisiereAlleZeiten(dataset);
            populateDropdowns(dataset);
            displayResults(dataset);
            initializeMap(dataset); // Initialisiert die Karte mit allen Daten
        });

    const searchInput = document.getElementById("search-input");
    const resetButton = document.getElementById("reset-search-btn");
    
    // Event-Listener für Sucheingabe und Filter
    searchInput.addEventListener("input", performSearch);
    document.getElementById("filter-typ").addEventListener("change", performSearch);
    document.getElementById("filter-region").addEventListener("change", performSearch);
    document.getElementById("filter-zeit").addEventListener("change", performSearch);


    if (resetButton) {
        resetButton.addEventListener("click", () => {
            searchInput.value = "";
            document.getElementById("filter-typ").value = "";
            document.getElementById("filter-region").value = "";
            document.getElementById("filter-zeit").value = "";
            performSearch();
        });
    }

    // Export-Button (beibehalten)
    document.getElementById("export-csv-btn").addEventListener("click", () => {
        // Filtere aktuelle Ergebnisse, um nur die angezeigten zu exportieren
        const currentQuery = searchInput.value.trim();
        const filterTyp = document.getElementById("filter-typ").value;
        const filterRegion = document.getElementById("filter-region").value;
        const filterZeit = document.getElementById("filter-zeit").value;
        
        let regex;
        try {
            regex = new RegExp(currentQuery, "i");
        } catch {
            // Bei ungültigem Regex leeres Array exportieren
            exportToCSV([], "weistuemer_export.csv");
            return;
        }

        const filteredForExport = dataset.filter(entry => {
            const matchesQuery = Object.values(entry).some(value =>
                regex.test(typeof value === "object" ? JSON.stringify(value) : String(value))
            );
            const matchesTyp = !filterTyp || entry.typ === filterTyp;
            const matchesRegion = !filterRegion || entry.region === filterRegion;
            const matchesZeit = !filterZeit || entry.zeit_kategorie === filterZeit;
            return matchesQuery && matchesTyp && matchesRegion && matchesZeit;
        });

        exportToCSV(filteredForExport, "weistuemer_export.csv");
    });
    
    // =========================================================
    // KARTEN-FUNKTIONEN
    // =========================================================
    
    function initializeMap(data) {
        // Entfernt die alte Karte, falls sie existiert (wichtig für Entwicklungszwecke)
        if (map) {
            map.remove();
        }

        // Initialisierung der Leaflet-Karte
        // Standard-Zentrum (Deutschland/Schweiz) und Zoom
        map = L.map('map').setView([49.0, 9.0], 6);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap-Mitwirkende'
        }).addTo(map);

        // Marker-Gruppe zur Karte hinzufügen
        markers.clearLayers();
        map.addLayer(markers);
        
        // Füge die initialen Marker hinzu
        updateMapMarkers(data);

        // Klick-Event für die Karte: Setzt den Filter zurück, wenn auf die leere Karte geklickt wird
        map.on('click', () => {
            // Optionale Funktion, derzeit auskommentiert
        });
    }
    
    /**
     * Aktualisiert die Marker auf der Karte basierend auf den gefilterten Daten.
     * @param {Array} filteredData - Die Array der Weistümer, die angezeigt werden sollen.
     */
    function updateMapMarkers(filteredData) {
        // 1. Alle alten Marker entfernen
        markers.clearLayers();

        // 2. Neue Marker hinzufügen
        filteredData.forEach(entry => {
            if (entry.koordinaten && entry.koordinaten.lat && entry.koordinaten.lng) {
                
                // Popup-Text für den Marker erstellen
                const popupText = `
                    <b>${entry.titel}</b><br>
                    Ort: ${entry.ort}<br>
                    Zeit: ${entry.zeit || 'Unbekannt'}<br>
                    Typ: ${entry.typ || 'Unbekannt'}<br>
                    <button onclick="window.filterByLocation('${entry.ort.replace(/'/g, "\\'")}')" style="margin-top: 5px; cursor: pointer;">Nur diesen Ort anzeigen</button>
                `;

                // Marker erstellen
                const marker = L.marker([entry.koordinaten.lat, entry.koordinaten.lng]);
                
                // Popup binden
                marker.bindPopup(popupText);
                
                // Marker zur Marker-Gruppe hinzufügen
                markers.addLayer(marker);
            }
        });

        // 3. Karte auf die Marker zentrieren (optional)
        if (markers.getLayers().length > 0) {
            // Berechne die Begrenzungen der Marker und passe die Ansicht an
            // maxZoom: 10, um nicht zu stark hineinzuzoomen, wenn nur ein Marker existiert
            map.fitBounds(markers.getBounds(), { padding: [50, 50], maxZoom: 10 }); 
        } else {
            // Wenn keine Ergebnisse, kehre zur Standardansicht zurück
            map.setView([49.0, 9.0], 6);
        }
    }
    
    // Globale Funktion, die vom Marker-Popup aufgerufen wird
    window.filterByLocation = function(locationName) {
        // Setzt den Such-Input auf den Ort und führt die Suche durch
        document.getElementById("search-input").value = `\\b${locationName}\\b`; // Sucht exakt nach dem Wort
        document.getElementById("filter-typ").value = "";
        document.getElementById("filter-region").value = "";
        document.getElementById("filter-zeit").value = "";
        performSearch();
    };

    // =========================================================
    // HAUPTSUCHFUNKTION
    // =========================================================
    
    function performSearch() {
        const query = searchInput.value.trim();
        const filterTyp = document.getElementById("filter-typ").value;
        const filterRegion = document.getElementById("filter-region").value;
        const filterZeit = document.getElementById("filter-zeit").value;

        let regex;
        try {
            // RegEx für die Freitextsuche
            regex = new RegExp(query, "i");
        } catch {
            document.getElementById("results").innerHTML = "<p>⚠️ Ungültiger regulärer Ausdruck.</p>";
            // Wichtig: Auch die Karte muss aktualisiert werden
            updateMapMarkers([]); 
            return;
        }

        const filtered = dataset.filter(entry => {
            // 1. Freitextsuche
            const matchesQuery = Object.values(entry).some(value =>
                regex.test(typeof value === "object" ? JSON.stringify(value) : String(value))
            );

            // 2. Filter-Überprüfung
            const matchesTyp = !filterTyp || entry.typ === filterTyp;
            const matchesRegion = !filterRegion || entry.region === filterRegion;
            const matchesZeit = !filterZeit || entry.zeit_kategorie === filterZeit;

            return matchesQuery && matchesTyp && matchesRegion && matchesZeit;
        });

        // Die Karte mit den gefilterten Ergebnissen aktualisieren
        updateMapMarkers(filtered);
        
        // Die Ergebnisse unter der Karte anzeigen
        displayResults(filtered);
    }
    
    // =========================================================
    // RESTLICHE HELFERFUNKTIONEN
    // =========================================================

    function displayResults(data) {
        const resultsDiv = document.getElementById("results");
        resultsDiv.innerHTML = `<p>Gefundene Einträge: <b>${data.length}</b></p>`;

        data.forEach(entry => {
            const resultItem = document.createElement("div");
            resultItem.className = "result-item";
            
            const markdownText = entry.text || "";
            const htmlText = md.render(markdownText);
            
            const detailHtml = `
                <div class="result-header">
                    <h3>${entry.titel}</h3>
                    <p>
                        Ort: <b>${entry.ort || 'N/A'}</b> | 
                        Region: <b>${entry.region || 'N/A'}</b> | 
                        Zeit: <b>${entry.zeit || 'N/A'}</b> |
                        Typ: <b>${entry.typ || 'N/A'}</b>
                    </p>
                </div>
                <div class="result-body">
                    ${htmlText}
                </div>
                <div class="result-details">
                    ${entry.edition && entry.edition.stelle ? `<p>Quelle: ${entry.edition.stelle}</p>` : ''}
                    ${entry.edition && entry.edition.notizen ? `<p>Anmerkungen: ${entry.edition.notizen}</p>` : ''}
                    ${entry.schreiberinfo ? `<p>Schreiberinfo: ${entry.schreiberinfo}</p>` : ''}
                    ${entry.original_link ? `<p><a href="${entry.original_link}" target="_blank">Original-Link</a></p>` : ''}
                </div>
            `;
            resultItem.innerHTML = detailHtml;
            resultsDiv.appendChild(resultItem);
        });
    }

    function populateDropdowns(data) {
        const typSet = new Set();
        const regionSet = new Set();
        const zeitSet = new Set();

        data.forEach(entry => {
            if (entry.typ) typSet.add(entry.typ);
            if (entry.region) regionSet.add(entry.region);
            if (entry.zeit_kategorie) zeitSet.add(entry.zeit_kategorie);
        });

        populateDropdown("filter-typ", typSet);
        populateDropdown("filter-region", regionSet);
        populateDropdown("filter-zeit", zeitSet);
    }
    
    /**
     * Erstellt einen Sortierrang basierend auf Jahrhundert und Periode (Anfang/Mitte/Ende).
     * @param {string} category - Die Zeitkategorie (z.B. "Ende 13. Jh.").
     * @returns {number} - Der numerische Rang (z.B. 133 für Ende 13. Jh.).
     */
    function getSortRank(category) {
        // Versucht, die Jahrhundertzahl (z.B. 13) zu extrahieren
        const centuryMatch = category.match(/(\d{2})\.\s*Jh/);
        const century = centuryMatch ? parseInt(centuryMatch[1], 10) : 99; // Standard 99 für Unbekannt/Sonstige
        
        let periodRank = 0;
        if (category.includes("Anfang")) periodRank = 1;
        else if (category.includes("Mitte")) periodRank = 2;
        else if (category.includes("Ende")) periodRank = 3;

        // Erzeugt einen kombinierten Rang: Jahrhundert * 10 + Perioden-Rang
        // Bsp: Anfang 13. Jh. = 131, Mitte 13. Jh. = 132
        return century * 10 + periodRank;
    }


    function populateDropdown(elementId, set) {
        const select = document.getElementById(elementId);
        const placeholder = select.querySelector('option[value=""]').textContent;
        select.innerHTML = `<option value="">${placeholder}</option>`; // Placeholder beibehalten

        // Sortiert die Zeitkategorien nach dem neuen Ranking
        const sortedArray = Array.from(set).sort((a, b) => {
            const rankA = getSortRank(a);
            const rankB = getSortRank(b);

            // Spezialbehandlung für "Unbekannt" (Rank 990) und andere Randfälle
            if (rankA > 900 && rankB > 900) return a.localeCompare(b);
            if (rankA > 900) return 1;
            if (rankB > 900) return -1;
            
            return rankA - rankB;
        });

        sortedArray.forEach(item => {
            const option = document.createElement("option");
            option.value = item;
            option.textContent = item;
            select.appendChild(option);
        });
    }
    
    // Fügt eine neue Kategorie 'zeit_kategorie' basierend auf dem 'zeit'-Feld hinzu
    function kategorisiereAlleZeiten(data) {
        data.forEach(entry => {
            entry.zeit_kategorie = kategorisiereZeit(entry.zeit);
        });
    }

    /**
     * Kategorisiert eine Zeitangabe in "Anfang/Mitte/Ende [Jahrhundert]".
     * @param {string} zeitString - Die originale Zeitangabe (z.B. "vor 1493" oder "Ende 13. Jh.").
     * @returns {string} - Die neue Zeitkategorie (z.B. "Ende 15. Jh.").
     */
    function kategorisiereZeit(zeitString) {
        if (!zeitString) return "Unbekannt";

        const lowerZeit = zeitString.toLowerCase();
        let jahr = null;
        let century;
        let centuryName;

        // 1. Versucht, eine vierstellige Zahl zu finden (als Jahr)
        const jahrMatch = lowerZeit.match(/(\d{4})/);

        if (jahrMatch) {
            jahr = parseInt(jahrMatch[1], 10);
            
            // Setzt einen vernünftigen Rahmen für die Kategorisierung
            if (jahr < 1100) return "Vor 1100";
            if (jahr >= 1600) return "Ab 1600";

            century = Math.ceil(jahr / 100);
            centuryName = `${century}. Jh.`;

            const startOfPreviousCentury = (century - 1) * 100;
            const centennialPart = jahr - startOfPreviousCentury; // Bsp: 1475 -> 75

            // Dreiteilung des Jahrhunderts (ca. 33/34/33 Jahre)
            if (centennialPart >= 0 && centennialPart <= 32) {
                return `Anfang ${centuryName}`; 
            } else if (centennialPart >= 33 && centennialPart <= 66) {
                return `Mitte ${centuryName}`; 
            } else { // 67 to 99
                return `Ende ${centuryName}`; 
            }
        }

        // 2. Fallback für ungefähre Angaben (z.B. "Ende 13. Jh.")
        
        // Match "13. jh.", "14. jh.", etc.
        const centuryMatch = lowerZeit.match(/(\d{2})\.\s*jh/); 
        if (centuryMatch) {
            century = parseInt(centuryMatch[1], 10);
            centuryName = `${century}. Jh.`;
            
            if (lowerZeit.includes("anfang") || lowerZeit.includes("beginn")) {
                return `Anfang ${centuryName}`;
            } else if (lowerZeit.includes("mitte")) {
                return `Mitte ${centuryName}`;
            } else if (lowerZeit.includes("ende")) {
                return `Ende ${centuryName}`;
            } else {
                // Wenn nur "13. Jh." ohne Präzisierung gegeben ist
                return `Mitte ${centuryName} (ungefähr)`;
            }
        }
        
        // 3. Genereller Fallback
        return "Sonstige/Ungefähre Angabe";
    }


    /**
     * Zerlegt die freie Editionsangabe ("Grimm Bd. 1, S. 1–2") in Band und
     * Seite, damit beide als eigene Spalten exportiert werden können.
     * Diese Angaben liegen in den Daten nur als ein zusammenhängender
     * Text vor, nicht als getrennte Felder.
     */
    function extractBandSeite(stelle) {
        if (!stelle) return { band: "", seite: "" };
        const bandMatch = stelle.match(/Bd\.\s*(\d+)/);
        const seiteMatch = stelle.match(/S\.\s*(.+)$/);
        return {
            band: bandMatch ? bandMatch[1] : "",
            seite: seiteMatch ? seiteMatch[1].trim() : "",
        };
    }

    function exportToCSV(data, filename) {
        const headers = [
            "id", "titel", "ort", "region", "zeit", "zeit_kategorie", "typ",
            "koordinaten_lat", "koordinaten_lng", "schreiberinfo", "text", "Fussnoten",
            "edition_stelle", "band", "seite", "edition_notizen", "original_link"
        ];
        const csvRows = [headers.join(",")];

        data.forEach(entry => {
            // Textbereinigung für den Export (entfernt Markdown-Fußnoten und Zeilenumbrüche)
            const raw = entry.text || "";
            const inline = raw.replace(/\[\^(\d+)\]/g, "[$1]");
            const notes = [];
            const textClean = inline.replace(/^\[\^(\d+)\]:(.*)$/gm, (match, num, txt) => {
                notes.push(`${num}: ${txt.trim()}`);
                return "";
            }).replace(/\n/g, " ").trim();

            const stelle = entry.edition ? entry.edition.stelle : "";
            const { band, seite } = extractBandSeite(stelle);

            const row = [
                entry.id,
                entry.titel,
                entry.ort,
                entry.region,
                entry.zeit,
                entry.zeit_kategorie,
                entry.typ,
                entry.koordinaten ? entry.koordinaten.lat : "",
                entry.koordinaten ? entry.koordinaten.lng : "",
                entry.schreiberinfo || "",
                textClean.replace(/"/g, '""'), // Escape Anführungszeichen
                notes.join(" | ").replace(/"/g, '""'),
                stelle || "",
                band,
                seite,
                entry.edition ? (entry.edition.notizen || "").replace(/"/g, '""') : "",
                entry.original_link || ""
            ].map(v => `"${v}"`).join(","); // Alle Werte in Anführungszeichen setzen

            csvRows.push(row);
        });

        // Erzeugt eine CSV-Datei und löst den Download aus
        const blob = new Blob(["\uFEFF" + csvRows.join("\n")], { type: "text/csv;charset=utf-8;" });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
});
