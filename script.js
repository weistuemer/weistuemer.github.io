document.addEventListener("DOMContentLoaded", function () {
    let dataset = [];
    // Globale Variablen für Karte und Marker-Gruppe
    let map;
    let markers = L.markerClusterGroup({ chunkedLoading: true }); // Marker Cluster Group für bessere Performance

    const md = window.markdownit({ html: true }).use(window.markdownitFootnote);

    // Schnelle Ladeweise (ab Version 0.8): erst ein schlanker Index, die Volltexte
    // und Detailangaben kommen in Häppchen (daten/d_NNN.json) – zuerst die Häppchen,
    // die gerade angezeigt werden, danach der Rest im Hintergrund.
    const PAGE = 50;                 // so viele Einträge pro "Mehr anzeigen"
    const VERSION = "0.8";
    let nChunks = 0, nChunksGeladen = 0;
    const chunkPromises = {};
    let currentList = [], shown = 0, currentHighlight = null;

    fetch("daten/index.json?v=" + VERSION)
        .then(response => response.json())
        .then(idx => {
            dataset = idx.eintraege;
            nChunks = idx.chunks;
            kategorisiereAlleZeiten(dataset);
            dataset.forEach(e => {
                e._s = [e.titel, e.ort, e.region, e.zeit, e.typ, e.typ_norm, e.quelle, e.nr_edition,
                        e.edition && e.edition.stelle, e.dublette_von, e.ueberschneidung_mit].filter(Boolean).join(" \n ");
            });
            populateDropdowns(dataset);
            displayResults(dataset);
            initializeMap(dataset);
            ladeRestImHintergrund();
        });

    function ensureChunk(c) {
        if (!chunkPromises[c]) {
            const nr = String(c).padStart(3, "0");
            chunkPromises[c] = fetch("daten/d_" + nr + ".json?v=" + VERSION)
                .then(r => r.json())
                .then(det => {
                    dataset.forEach(e => {
                        if (e.c === c && det[e.id]) {
                            Object.assign(e, det[e.id]);
                            e._t = (e.text || "") + " \n " + (e.schreiberinfo || "") + " \n " +
                                   (e.edition && e.edition.notizen || "") + " \n " + JSON.stringify(e.originale || []);
                            e._d = true;
                        }
                    });
                    nChunksGeladen++;
                    aktualisiereLadeHinweis();
                });
        }
        return chunkPromises[c];
    }

    function ladeRestImHintergrund() {
        // nacheinander laden, damit Seite und Suche reaktionsfähig bleiben
        let c = 0;
        const next = () => {
            if (c >= nChunks) {
                if (searchInput.value.trim()) performSearch();   // Suche mit vollständigem Volltext wiederholen
                return;
            }
            ensureChunk(c++).then(() => setTimeout(next, 0));
        };
        next();
    }

    function loadAllChunks() {
        const arr = [];
        for (let c = 0; c < nChunks; c++) arr.push(ensureChunk(c));
        return Promise.all(arr);
    }

    function aktualisiereLadeHinweis() {
        const el = document.getElementById("lade-hinweis");
        if (!el) return;
        if (nChunksGeladen >= nChunks) { el.textContent = ""; return; }
        el.textContent = searchInput.value.trim()
            ? `Volltext wird noch geladen (${nChunksGeladen}/${nChunks}) – die Suche berücksichtigt bisher nur die geladenen Texte.`
            : "";
    }

    // Freitextsuche: Index-Felder immer, Volltext und Detailangaben, sobald geladen
    function matchesQuery(entry, regex) {
        return regex.test(entry._s) || (entry._d && regex.test(entry._t));
    }

    const searchInput = document.getElementById("search-input");
    const resetButton = document.getElementById("reset-search-btn");
    
    // Event-Listener für Sucheingabe und Filter
    let suchTimer = null;
    searchInput.addEventListener("input", () => { clearTimeout(suchTimer); suchTimer = setTimeout(performSearch, 250); });
    document.getElementById("filter-typ").addEventListener("change", performSearch);
    document.getElementById("filter-region").addEventListener("change", performSearch);
    document.getElementById("filter-zeit").addEventListener("change", performSearch);
    document.getElementById("filter-vorlage").addEventListener("change", performSearch);
    document.getElementById("filter-original").addEventListener("change", performSearch);
    document.getElementById("filter-referat").addEventListener("change", performSearch);
    document.getElementById("filter-edition").addEventListener("change", performSearch);
    document.getElementById("filter-sprache").addEventListener("change", performSearch);

    // Zusatzfilter: Grimms Vorlage und Überlieferung (Originale)
    function matchesExtraFilters(entry) {
        const fv = document.getElementById("filter-vorlage").value;
        const fo = document.getElementById("filter-original").value;
        const fe = document.getElementById("filter-edition").value;
        const fs = document.getElementById("filter-sprache").value;
        const quelle = entry.quelle || "Grimm";
        if (fe && fe !== "ohne_dubletten" && quelle !== fe) return false;
        if (fe === "ohne_dubletten" && entry.dublette_von) return false;
        if (fs && (entry.sprache || "deutsch") !== fs) return false;
        if (fv && !(entry.grimm_vorlage && entry.grimm_vorlage.kategorie === fv)) return false;
        const fr = document.getElementById("filter-referat").value;
        const ref = entry.grimm_vorlage && entry.grimm_vorlage.referat;
        if (fr === "verdacht" && !(ref && ref.stufe === "verdacht")) return false;
        if (fr === "verdacht_moeglich" && !ref) return false;
        if (fr === "ohne" && ref) return false;
        const o = entry._o || { n: 0, archiv: false, digi: false, ausf: false, sbb: false };
        if (fo === "archiv" && !o.archiv) return false;
        if (fo === "archiv_digi" && !o.digi) return false;
        if (fo === "ausfertigung" && !o.ausf) return false;
        if (fo === "sbb" && !o.sbb) return false;
        if (fo === "keine" && o.n > 0) return false;
        return true;
    }


    if (resetButton) {
        resetButton.addEventListener("click", () => {
            searchInput.value = "";
            document.getElementById("filter-typ").value = "";
            document.getElementById("filter-region").value = "";
            document.getElementById("filter-zeit").value = "";
            document.getElementById("filter-vorlage").value = "";
            document.getElementById("filter-original").value = "";
            document.getElementById("filter-referat").value = "";
            document.getElementById("filter-edition").value = "";
            document.getElementById("filter-sprache").value = "";
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

        loadAllChunks().then(() => {   // für den Export werden alle Volltexte gebraucht
            const filteredForExport = dataset.filter(entry => {
                const okQuery = !currentQuery || matchesQuery(entry, regex);
                const matchesTyp = !filterTyp || entry.typ_norm === filterTyp;
                const matchesRegion = !filterRegion || entry.region === filterRegion;
                const matchesZeit = !filterZeit || entry.zeit_kategorie === filterZeit;
                return okQuery && matchesTyp && matchesRegion && matchesZeit && matchesExtraFilters(entry);
            });
            exportToCSV(filteredForExport, "weistuemer_export.csv");
        });
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

        // 2. Neue Marker hinzufügen (gesammelt; Popup erst beim Klick erzeugen)
        const neue = [];
        filteredData.forEach(entry => {
            if (entry.koordinaten && entry.koordinaten.lat && entry.koordinaten.lng) {
                const marker = L.marker([entry.koordinaten.lat, entry.koordinaten.lng]);
                marker.bindPopup(() => `
                    <b>${entry.titel}</b><br>
                    Ort: ${entry.ort}<br>
                    Zeit: ${entry.zeit || 'Unbekannt'}<br>
                    Typ: ${entry.typ_norm || entry.typ || 'Unbekannt'}<br>
                    <button onclick="window.filterByLocation('${(entry.ort || '').replace(/'/g, "\\'")}')" style="margin-top: 5px; cursor: pointer;">Nur diesen Ort anzeigen</button>
                `);
                neue.push(marker);
            }
        });
        markers.addLayers(neue);

        // 3. Karte auf die Marker zentrieren (optional)
        if (neue.length > 0) {
            // Begrenzungen aus den Koordinaten berechnen (chunkedLoading füllt die Gruppe erst nach und nach)
            map.fitBounds(L.latLngBounds(neue.map(m => m.getLatLng())), { padding: [50, 50], maxZoom: 10 });
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
        document.getElementById("filter-vorlage").value = "";
        document.getElementById("filter-original").value = "";
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
            const okQuery = !query || matchesQuery(entry, regex);

            // 2. Filter-Überprüfung
            const matchesTyp = !filterTyp || entry.typ_norm === filterTyp;
            const matchesRegion = !filterRegion || entry.region === filterRegion;
            const matchesZeit = !filterZeit || entry.zeit_kategorie === filterZeit;

            return okQuery && matchesTyp && matchesRegion && matchesZeit && matchesExtraFilters(entry);
        });

        // Die Karte mit den gefilterten Ergebnissen aktualisieren
        updateMapMarkers(filtered);
        
        // Die Ergebnisse unter der Karte anzeigen; bei nicht-leerer Suche
        // wird der Suchterm in den Treffern farbig hervorgehoben
        const highlightRegex = query ? new RegExp(query, "gi") : null;
        displayResults(filtered, highlightRegex);
    }

    /**
     * Markiert alle Treffer des Suchmusters in den Textknoten eines
     * DOM-Elements mit <mark class="treffer">. Es werden nur Textknoten
     * angefasst, nicht HTML-Tags oder Attribute (Links, Fußnoten usw.
     * bleiben intakt). Treffer, die über mehrere Textknoten hinweg laufen
     * (z. B. über ein <u>-Tag), werden nicht markiert.
     */
    function highlightMatches(root, regex) {
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        const textNodes = [];
        while (walker.nextNode()) textNodes.push(walker.currentNode);

        textNodes.forEach(node => {
            const text = node.nodeValue;
            regex.lastIndex = 0;
            let match;
            let last = 0;
            let frag = null;
            while ((match = regex.exec(text)) !== null) {
                if (match[0].length === 0) { // z. B. Muster wie "x*" -- Endlosschleife vermeiden
                    regex.lastIndex++;
                    continue;
                }
                if (!frag) frag = document.createDocumentFragment();
                frag.appendChild(document.createTextNode(text.slice(last, match.index)));
                const mark = document.createElement("mark");
                mark.className = "treffer";
                mark.textContent = match[0];
                frag.appendChild(mark);
                last = match.index + match[0].length;
            }
            if (frag) {
                frag.appendChild(document.createTextNode(text.slice(last)));
                node.parentNode.replaceChild(frag, node);
            }
        });
    }
    
    // =========================================================
    // RESTLICHE HELFERFUNKTIONEN
    // =========================================================

    function displayResults(data, highlightRegex) {
        currentList = data;
        currentHighlight = highlightRegex || null;
        shown = 0;
        const resultsDiv = document.getElementById("results");
        resultsDiv.innerHTML = `<p>Gefundene Einträge: <b>${data.length}</b> <span id="lade-hinweis" style="color:#a60"></span></p><div id="result-liste"></div><div id="mehr-wrap"></div>`;
        aktualisiereLadeHinweis();
        zeigeNaechsteSeite();
    }

    function zeigeNaechsteSeite() {
        const liste = document.getElementById("result-liste");
        const wrap = document.getElementById("mehr-wrap");
        const bis = Math.min(shown + PAGE, currentList.length);
        for (let i = shown; i < bis; i++) liste.appendChild(renderItem(currentList[i]));
        shown = bis;
        wrap.innerHTML = "";
        if (shown < currentList.length) {
            const btn = document.createElement("button");
            btn.textContent = `Mehr anzeigen (${shown} von ${currentList.length})`;
            btn.style.cssText = "margin:1em 0;padding:.5em 1.2em;cursor:pointer;font-size:1em;";
            btn.addEventListener("click", zeigeNaechsteSeite);
            wrap.appendChild(btn);
        }
    }

    function renderItem(entry) {
        const resultItem = document.createElement("div");
        resultItem.className = "result-item";
        const hl = currentHighlight;
        const fill = () => {
            resultItem.innerHTML = itemHtml(entry);
            if (hl) highlightMatches(resultItem, hl);
        };
        if (entry._d) fill();
        else {
            resultItem.innerHTML = `<div class="result-header"><h3>${entry.titel}</h3><p>Ort: <b>${entry.ort || 'N/A'}</b> | Zeit: <b>${entry.zeit || 'N/A'}</b></p></div><div class="result-body"><p><i>Text wird geladen …</i></p></div>`;
            ensureChunk(entry.c).then(fill);
        }
        return resultItem;
    }

    function itemHtml(entry) {
        const htmlText = md.render(entry.text || "");
        return `
                <div class="result-header">
                    <h3>${entry.titel}</h3>
                    <p>
                        Ort: <b>${entry.ort || 'N/A'}</b> | 
                        Region: <b>${entry.region || 'N/A'}</b> | 
                        Zeit: <b>${entry.zeit || 'N/A'}</b> |
                        Typ: <b>${entry.typ_norm || entry.typ || 'N/A'}</b>${(entry.typ_form || []).length ? ' (' + entry.typ_form.join(', ') + ')' : ''}${entry.typ && entry.typ !== entry.typ_norm ? ' <span class="vorlage-methode" title="Angabe in der Datenbank (Original)">[Angabe: ' + esc(entry.typ) + ']</span>' : ''}
                    </p>
                </div>
                <div class="result-body">
                    ${htmlText}
                </div>
                <div class="result-details">
                    ${entry.edition && entry.edition.stelle ? `<p>Quelle: ${entry.edition.stelle}${entry.nr_edition ? ' (Nr. ' + esc(entry.nr_edition) + ')' : ''}</p>` : ''}
                    ${entry.dublette_von ? (entry.quelle === 'Hardt' ? `<p><i>Dublette: Hardt übernimmt dieses Stück aus ${entry.dublette_von}.</i></p>` : `<p><i>Dublette: Text weitgehend identisch mit ${entry.dublette_von} (automatisch erkannt, ungeprüft).</i></p>`) : ''}
                    ${entry.ueberschneidung_mit ? `<p><i>Teilweise Überschneidung mit ${entry.ueberschneidung_mit} (Textübereinstimmung ${Math.round((entry.ueberschneidung_anteil || 0) * 100)} %, automatisch erkannt, ungeprüft).</i></p>` : ''}
                    ${entry.koordinaten_status && entry.koordinaten_status !== 'automatisch' ? `<p><i>Koordinate: ${entry.koordinaten_status}.</i></p>` : ''}
                    ${entry.sprache && entry.sprache !== 'deutsch' ? `<p>Sprache: ${entry.sprache}</p>` : ''}
                    ${entry.edition && entry.edition.notizen ? `<p>Anmerkungen: ${entry.edition.notizen}</p>` : ''}
                    ${entry.schreiberinfo ? `<p>Schreiberinfo: ${entry.schreiberinfo}</p>` : ''}
                    ${entry.original_link ? `<p><a href="${entry.original_link}" target="_blank">Original-Link</a></p>` : ''}
                    ${renderVorlage(entry)}
                    ${renderOriginale(entry)}
                </div>
            `;
    }

    function esc(s) {
        return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    function renderVorlage(entry) {
        const gv = entry.grimm_vorlage;
        if (!gv) return "";
        let html = `<p>Grimms Vorlage: <b>${esc(gv.kategorie)}</b>`;
        if (gv.kindlinger) html += ` – ${esc(gv.kindlinger)}`;
        if (gv.beleg) html += `<br><span class="vorlage-beleg">Beleg: „…${esc(gv.beleg)}…“</span>`;
        html += ` <span class="vorlage-methode">(${esc(gv.methode || "")})</span></p>`;
        if (gv.referat) {
            const r = gv.referat;
            const lbl = r.stufe === "verdacht" ? "Verdacht: Referat/Auszug statt Wortlaut" : "möglicherweise Referat/Auszug";
            html += `<p class="vorlage-referat"><b>${lbl}</b> – ${esc((r.merkmale || []).join("; "))}`;
            if (r.geprueft) html += `<br><span class="vorlage-beleg">Geprüft: ${esc(r.geprueft)}</span>`;
            html += ` <span class="vorlage-methode">(${esc(r.methode || "")}; Sprachstand daher evtl. jünger als die Datierung)</span></p>`;
        }
        return html;
    }

    function renderOriginale(entry) {
        const list = entry.originale || [];
        if (!list.length) return "";
        const rows = list.map(o => `
            <tr>
                <td>${esc(o.art)}</td>
                <td>${esc(o.archiv)}${o.signatur && !String(o.signatur).startsWith(o.archiv) ? "<br>" + esc(o.signatur) : (o.signatur && o.signatur !== o.archiv ? "<br>" + esc(String(o.signatur).slice(String(o.archiv).length).trim()) : "")}</td>
                <td>${esc(o.titel)}</td>
                <td>${esc(o.datierung)}</td>
                <td>${esc(o.ueberlieferung)}</td>
                <td>${esc(o.zuordnung)}</td>
                <td>${esc(o.digitalisat)}</td>
                <td>${o.link ? `<a href="${esc(o.link)}" target="_blank">Link</a>` : ""}${o.link_alt ? ` · <a href="${esc(o.link_alt)}" target="_blank">Alt.</a>` : ""}${o.anmerkung ? `<br><small>${esc(o.anmerkung)}</small>` : ""}</td>
            </tr>`).join("");
        return `
            <details class="originale">
                <summary>Überlieferung / Originale (${list.length}) – dirty, automatisch zugeordnet</summary>
                <div class="originale-wrap"><table class="originale-tabelle">
                    <thead><tr><th>Art</th><th>Archiv / Signatur</th><th>Titel (Verzeichnung)</th><th>Datierung</th><th>Überlieferung</th><th>Zuordnung</th><th>Digitalisat</th><th>Link</th></tr></thead>
                    <tbody>${rows}</tbody>
                </table></div>
            </details>`;
    }

    function populateDropdowns(data) {
        const typSet = new Set();
        const regionSet = new Set();
        const zeitSet = new Set();

        data.forEach(entry => {
            if (entry.typ_norm) typSet.add(entry.typ_norm);
            if (entry.region) regionSet.add(entry.region);
            if (entry.zeit_kategorie) zeitSet.add(entry.zeit_kategorie);
        });

        populateDropdown("filter-typ", typSet);
        populateDropdown("filter-region", regionSet);
        populateDropdown("filter-zeit", zeitSet);

        const vorlageSet = new Set();
        data.forEach(entry => { if (entry.grimm_vorlage && entry.grimm_vorlage.kategorie) vorlageSet.add(entry.grimm_vorlage.kategorie); });
        const sel = document.getElementById("filter-vorlage");
        Array.from(vorlageSet).sort().forEach(v => {
            const opt = document.createElement("option"); opt.value = v; opt.textContent = v; sel.appendChild(opt);
        });
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
            // Lange Werte kürzen (Breite des Auswahlfelds), voller Wert im Tooltip
            option.textContent = item.length > 40 ? item.slice(0, 38).trim() + "…" : item;
            option.title = item;
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

        // 2. Fallback für ungefähre Angaben (z.B. "Ende 13. Jh." oder
        // ausgeschrieben "13. Jahrhundert")

        // Match "13. jh.", "14. jh.", aber auch "13. jahrhundert" usw.
        const centuryMatch = lowerZeit.match(/(\d{2})\.\s*(?:jh|jahrhundert)/);
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
            "id", "titel", "ort", "region", "zeit", "zeit_kategorie", "typ", "typ_norm", "typ_form",
            "koordinaten_lat", "koordinaten_lng", "schreiberinfo", "text", "Fussnoten",
            "quelle", "sprache", "edition_stelle", "band", "seite", "edition_notizen", "original_link",
            "grimm_vorlage", "grimm_vorlage_beleg", "kindlinger", "referat_verdacht", "anzahl_originale", "originale"
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
                entry.typ_norm || "",
                (entry.typ_form || []).join("; "),
                entry.koordinaten ? entry.koordinaten.lat : "",
                entry.koordinaten ? entry.koordinaten.lng : "",
                entry.schreiberinfo || "",
                textClean.replace(/"/g, '""'), // Escape Anführungszeichen
                notes.join(" | ").replace(/"/g, '""'),
                entry.quelle || "Grimm",
                entry.sprache || "deutsch",
                stelle || "",
                band,
                seite,
                entry.edition ? (entry.edition.notizen || "").replace(/"/g, '""') : "",
                entry.original_link || "",
                entry.grimm_vorlage ? entry.grimm_vorlage.kategorie : "",
                entry.grimm_vorlage ? (entry.grimm_vorlage.beleg || "").replace(/"/g, '""') : "",
                entry.grimm_vorlage ? (entry.grimm_vorlage.kindlinger || "") : "",
                (entry.grimm_vorlage && entry.grimm_vorlage.referat) ? entry.grimm_vorlage.referat.stufe : "",
                (entry.originale || []).length,
                (entry.originale || []).map(o => [o.art, o.archiv, o.signatur, o.datierung, o.ueberlieferung, o.zuordnung, o.digitalisat, o.link].join(" / ")).join(" || ").replace(/"/g, '""')
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
