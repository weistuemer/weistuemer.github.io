"""Erzeugt editionen.html (Überblick über die Editionen: Umfang, Zeit, Raum) und daten/punkte.json
aus data.json (+ data_weitere.json). Aufruf im Repository-Hauptordner:  python3 baue_editionsseite.py
Alle Zahlen werden aus den Daten berechnet; Beschreibungstexte stehen unten in ED."""
import json, os, re, html, statistics, collections, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else '.')
import region_gross
HERE = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else '.'
os.chdir(HERE)
D = json.load(open('data.json', encoding='utf-8'))
if os.path.exists('data_weitere.json'):
    D += json.load(open('data_weitere.json', encoding='utf-8'))
os.makedirs('daten', exist_ok=True)
for _w, _g in zip(D, region_gross.zuordnen(D)): _w['region_gross'] = _g

# ---- Beschreibungen (Reihenfolge = Reihenfolge auf der Seite) ----
ED = [
 dict(key='Grimm', farbe='#1b6ca8', kurz='Grimm',
  titel='Jacob Grimm, Weisthümer',
  bib='Jacob Grimm (Hg.), <i>Weisthümer</i>, Bd. 1–6, Göttingen 1840–1869 (Bd. 7, das Register, ist nicht enthalten).',
  text='Die große Sammlung ländlicher Rechtsweisungen im gesamten deutschsprachigen Raum und darüber hinaus. '
       'Sie ist die Grundlage der Datenbank und der Maßstab für alle weiteren Editionen. Grimm druckt vielfach nach Abschriften '
       'und älteren Drucken, gelegentlich auch nur Auszüge oder Referate; das steht in den Feldern „Grimms Vorlage“ und „Referat/Auszug“. '
       'Lateinische und französische Stücke sind noch nicht als solche markiert.'),
 dict(key='ÖW', farbe='#c0392b', kurz='ÖW',
  titel='Österreichische Weisthümer',
  bib='<i>Österreichische Weisthümer</i>, hg. von der Kaiserlichen Akademie der Wissenschaften in Wien, Bd. 1 (Salzburg, 1870), '
      'Bd. 2–5 (Tirol, 1875–1888/91), Bd. 6 (Steiermark/Kärnten, 1881), Bd. 7–8 (Niederösterreich, 1886 und 1896).',
  text='Die systematische österreichische Fortsetzung der Grimmschen Sammlung, nach Landschaften gegliedert und aus Archivquellen '
       'neu gesammelt. Die Bände geben die Überlieferung in der Regel mit Handschriftenbeschreibung und Lesarten. '
       'Aufgenommen sind die Bände 1 bis 8 der Reihe.'),
 dict(key='Wintterlin', farbe='#2e8b57', kurz='Wintterlin',
  titel='Wintterlin, Württembergische ländliche Rechtsquellen',
  bib='Friedrich Wintterlin (Bearb.), <i>Württembergische ländliche Rechtsquellen</i>, Bd. 1 (1910) und Bd. 2 (1922).',
  text='Dorfordnungen, Ehehaften und Weistümer aus Württemberg (Mittelwürttemberg, Ostwürttemberg/Ries u. a.). '
       'Wo die Edition nur Überschrift und Fußnoten druckt (z. B. Jebenhausen), ist der Text leer.'),
 dict(key='Hardt', farbe='#8e5ea2', kurz='Hardt',
  titel='Hardt, Luxemburger Weisthümer',
  bib='Hardt, <i>Luxemburger Weisthümer, als Nachlese zu Jacob Grimm’s Weisthümern</i>, Luxemburg 1870.',
  text='Nachlese zu Grimm für das Herzogtum Luxemburg. Ein Teil der Stücke (Notariatsinstrumente) ist französisch oder lateinisch; '
       '26 Stücke aus Hardts Anhang stammen aus Grimm und sind als Dubletten gekennzeichnet.'),
 dict(key='Loersch', farbe='#d98c00', kurz='Loersch',
  titel='Loersch, Weistümer der Rheinprovinz (Kurtrier)',
  bib='Hugo Loersch (Hg.), <i>Weistümer der Rheinprovinz</i>, Kurtrier, 1900.',
  text='Weistümer aus dem Erzstift Kurtrier (Ämter u. a. Boppard, Koblenz, Oberwesel, Bergpflege). '
       'Der Herausgeber nennt bei einem Teil der Stücke die Druckstellen bei Grimm.'),
 dict(key='Chlumecky', farbe='#555555', kurz='Chlumecky',
  titel='Chlumecky, Mähren',
  bib='Chlumecky, Mähren (in der Datenbank als „Chlumecky o. J.“ zitiert).',
  text='Eine kleine Gruppe von Dorfrügungen aus dem Gebiet um Znaim (Urbau, Kallendorf u. a., Grundherrschaft Kloster Bruck), mit Verweisen des Herausgebers auf Grimms Rechtsalterthümer.'),
 dict(key='Rein', farbe='#00a5a5', kurz='Rein',
  titel='Rein, Uerdinger Weisthümer',
  bib='Rein, <i>Uerdinger Weisthümer</i>, 1854.',
  text='Drei Stücke zu Hof und Land Uerdingen am Niederrhein, alle 1454.'),
]

# ---- Hilfsfunktionen ----
def jahr(z):
    z = z or ''
    m = re.search(r'\b(1[1-9]\d\d)\b', z)
    if m: return int(m.group(1))
    m = re.search(r'(Anfang|Mitte|Ende)?\s*(\d{1,2})\.\s*Jh', z)
    if m:
        c = int(m.group(2)); off = {'Anfang': 12, 'Mitte': 50, 'Ende': 88}.get(m.group(1), 50)
        return (c - 1) * 100 + off
    return None
BINS = [('vor 1300', 0, 1300), ('14. Jh.', 1300, 1400), ('15. Jh.', 1400, 1500), ('16. Jh.', 1500, 1600),
        ('17. Jh.', 1600, 1700), ('18. Jh.', 1700, 1800), ('ab 1800', 1800, 3000)]
def region(e):
    return e.get('region_gross') or '–'
fmt = lambda n: f'{n:,}'.replace(',', '.')
esc = html.escape

# ---- Statistik ----
stat = {}
for ed in ED:
    es = [e for e in D if e.get('quelle') == ed['key']]
    s = dict(n=len(es))
    s['dub'] = sum(1 for e in es if e.get('dublette_von'))
    s['ueb'] = sum(1 for e in es if e.get('ueberschneidung_mit') and not e.get('dublette_von'))
    s['woerter'] = sum(len((e.get('text') or '').split()) for e in es)
    s['leer'] = sum(1 for e in es if not (e.get('text') or '').strip())
    s['orte'] = len({(e.get('ort') or '').strip() for e in es if e.get('ort')})
    s['koord'] = sum(1 for e in es if isinstance(e.get('koordinaten'), dict) and e['koordinaten'].get('lat'))
    js = [j for j in (jahr(e.get('zeit')) for e in es) if j]
    s['datiert'] = len(js)
    if js:
        js.sort(); q = lambda p: js[min(len(js) - 1, int(p * len(js)))]
        s['min'], s['p10'], s['med'], s['p90'], s['max'] = js[0], q(.1), int(statistics.median(js)), q(.9), js[-1]
    s['bins'] = [sum(1 for j in js if a <= j < b) for _, a, b in BINS]
    s['regionen'] = collections.Counter(region(e) for e in es)
    s['sprache'] = collections.Counter(e.get('sprache') or 'deutsch' for e in es)
    s['ref'] = sum(1 for e in es if isinstance(e.get('grimm_vorlage'), dict) and e['grimm_vorlage'].get('referat'))
    lat = [e['koordinaten']['lat'] for e in es if isinstance(e.get('koordinaten'), dict) and e['koordinaten'].get('lat')]
    lng = [e['koordinaten']['lng'] for e in es if isinstance(e.get('koordinaten'), dict) and e['koordinaten'].get('lat')]
    if lat: s['box'] = (min(lat), max(lat), min(lng), max(lng))
    stat[ed['key']] = s
gesamt = sum(s['n'] for s in stat.values())

# ---- Punktedatei für die Karte ----
pts = []
for i, ed in enumerate(ED):
    for e in D:
        if e.get('quelle') != ed['key']: continue
        k = e.get('koordinaten')
        if isinstance(k, dict) and k.get('lat'):
            pts.append([round(k['lat'], 4), round(k['lng'], 4), i, (e.get('ort') or '')[:40], (e.get('zeit') or '')[:24]])
json.dump({'editionen': [{'kurz': ed['kurz'], 'farbe': ed['farbe']} for ed in ED], 'punkte': pts},
          open('daten/punkte.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

# ---- HTML ----
def balken(s, farbe):
    mx = max(s['bins']) or 1
    zeilen = []
    for (lab, _, _), v in zip(BINS, s['bins']):
        w = round(100 * v / mx)
        zeilen.append(f'<div class="zl"><span class="zlab">{lab}</span><span class="zbar"><i style="width:{w}%;background:{farbe}"></i></span><span class="zn">{fmt(v)}</span></div>')
    return '\n'.join(zeilen)

def zeitsatz(s):
    if not s.get('datiert'): return 'Keine maschinell auswertbaren Jahresangaben.'
    return (f'Datierbar sind {fmt(s["datiert"])} von {fmt(s["n"])} Einträgen ({round(100*s["datiert"]/s["n"])} %). '
            f'Die Hälfte dieser Stücke liegt vor {s["med"]}, '
            f'80 % liegen zwischen {s["p10"]} und {s["p90"]}; die äußersten Datierungen sind {s["min"]} und {s["max"]}.')

zeilen_tab = []
karten = []
for ed in ED:
    s = stat[ed['key']]
    if not s['n']: continue
    top = s['regionen'].most_common(6)
    reg = ', '.join(f'{esc(r)} ({fmt(n)})' for r, n in top)
    if len(s['regionen']) > len(top): reg += f' und {len(s["regionen"]) - len(top)} weitere'
    zeitspanne = ('–' if not s.get('p10') else (str(s['p10']) if s['p10']==s['p90'] else f'{s["p10"]}–{s["p90"]}'))
    zeilen_tab.append(f'<tr><td><span class="pkt" style="background:{ed["farbe"]}"></span><a href="#{ed["key"]}">{esc(ed["kurz"])}</a></td>'
                      f'<td class="num">{fmt(s["n"])}</td><td class="num">{fmt(round(s["woerter"], -3))}</td>'
                      f'<td class="num">{fmt(s["orte"])}</td><td>{zeitspanne}</td><td>{esc(top[0][0]) if top else ""}</td></tr>')
    extra = []
    if s['dub']: extra.append(f'{fmt(s["dub"])} Einträge sind als Dublette zu Grimm gekennzeichnet')
    if s['ueb']: extra.append(f'{fmt(s["ueb"])} überschneiden sich teilweise mit Grimm')
    if s['leer']: extra.append(f'{fmt(s["leer"])} {"Eintrag hat" if s["leer"]==1 else "Einträge haben"} keinen Text (nur Überschrift und Fußnoten)')
    if s['ref']: extra.append(f'{fmt(s["ref"])} Stücke sind als Referat/Auszug verdächtig')
    spr = {k: v for k, v in s['sprache'].items() if k != 'deutsch'}
    if spr and ed['key'] != 'Grimm': extra.append('Sprache: ' + ', '.join(f'{k} {v}' for k, v in spr.items()))
    box = ''
    if s.get('box'):
        b = s['box']; box = f' Die Koordinaten reichen von {b[0]:.1f}° bis {b[1]:.1f}° N und von {b[2]:.1f}° bis {b[3]:.1f}° O.'
    karten.append(f'''<section class="ed" id="{ed["key"]}">
<h2><span class="pkt" style="background:{ed["farbe"]}"></span>{esc(ed["titel"])}</h2>
<p class="bib">{ed["bib"]}</p>
<p>{ed["text"]}</p>
<div class="zwei">
<div><h3>Umfang</h3>
<p>{fmt(s["n"])} Einträge mit rund {fmt(round(s["woerter"], -3))} Wörtern an {fmt(s["orte"])} verschiedenen Ortsnamen.
{"Koordinaten liegen für " + fmt(s["koord"]) + " Einträge vor." if s["koord"] else ""}{box}</p>
{"<ul>" + "".join(f"<li>{x}</li>" for x in extra) + "</ul>" if extra else ""}
<h3>Raum</h3><p>Großräume (abgeleitet aus dem Feld „Region“): {reg}.</p></div>
<div><h3>Zeit</h3><p class="klein">{zeitsatz(s)}</p>
<div class="zeit">{balken(s, ed["farbe"])}</div></div>
</div>
</section>''')

seite = f'''<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Die Editionen der Weistümer-Datenbank</title>
<link rel="stylesheet" href="style.css?v=0.9">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<style>
 .wrap{{max-width:980px;margin:0 auto;padding:0 16px 40px;text-align:left}}
 .wrap table{{border-collapse:collapse;width:100%;margin:12px 0}}
 .wrap th,.wrap td{{padding:6px 8px;border-bottom:1px solid #ccc;text-align:left;vertical-align:top}}
 .wrap td.num{{text-align:right;font-variant-numeric:tabular-nums}}
 .pkt{{display:inline-block;width:.8em;height:.8em;border-radius:50%;margin-right:.45em;vertical-align:baseline}}
 .ed{{margin:34px 0;padding-top:6px;border-top:2px solid #ddd}}
 .bib{{font-size:.93em;color:#555}}
 .zwei{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}
 @media(max-width:720px){{.zwei{{grid-template-columns:1fr}}}}
 .klein{{font-size:.92em}}
 .zl{{display:grid;grid-template-columns:5.5em 1fr 3.2em;align-items:center;gap:8px;margin:3px 0;font-size:.9em}}
 .zbar{{background:#eee;height:.9em;border-radius:3px;overflow:hidden}} .zbar i{{display:block;height:100%}}
 .zn{{text-align:right;font-variant-numeric:tabular-nums}}
 #emap{{height:460px;border:1px solid #bbb;margin:10px 0}}
 .leg label{{margin-right:16px;white-space:nowrap;cursor:pointer}}
 .hinw{{font-size:.9em;color:#555}}
</style>
</head>
<body>
<div class="header flex-header">
  <img src="schreiber.png" alt="Twingherrenstreit" class="header-image">
  <div><h1>Weistümer-Datenbank</h1><p>Die Editionen im Überblick</p></div>
</div>
<main class="wrap">
<p><a href="index.html">← zur Datenbank</a> · <a href="hinweise.html">ℹ Hinweise</a></p>
<p>Die Datenbank vereint {fmt(gesamt)} Einträge aus {sum(1 for s in stat.values() if s["n"])} gemeinfreien Weistumseditionen des 19. und frühen 20. Jahrhunderts.
Grundlage ist Jacob Grimms <i>Weisthümer</i>; die übrigen Editionen ergänzen sie räumlich (Österreich, Württemberg, Luxemburg, Kurtrier, Niederrhein, Mähren)
und ermöglichen den Vergleich verschiedener Editionen derselben Textsorte. Die Tabelle und die Seiten unten werden aus dem aktuellen Datenbestand berechnet.</p>

<table>
<thead><tr><th>Edition</th><th class="num">Einträge</th><th class="num">Wörter (ca.)</th><th class="num">Orte</th><th>Zeit (80 % der datierbaren Stücke)</th><th>größte Region</th></tr></thead>
<tbody>
{chr(10).join(zeilen_tab)}
<tr><td><b>Gesamt</b></td><td class="num"><b>{fmt(gesamt)}</b></td><td class="num"><b>{fmt(round(sum(s["woerter"] for s in stat.values()), -3))}</b></td><td></td><td></td><td></td></tr>
</tbody></table>

<h2>Räumliche Verteilung</h2>
<div class="leg" id="leg"></div>
<div id="emap"></div>
<p class="hinw">Jeder Punkt ist ein Eintrag mit Koordinate (automatisch zugeordnet, teils ungeprüft). Einträge ohne Koordinate fehlen auf der Karte.</p>

{chr(10).join(karten)}

<h2>Hinweise zu den Zahlen</h2>
<p class="hinw">Wortzahlen sind aus dem transkribierten Text gezählt und daher Näherungswerte. Die Jahresangaben werden aus dem Feld „Zeit“ maschinell gelesen
(erste vierstellige Jahreszahl, sonst die Mitte des genannten Jahrhunderts) und sind nur ein Anhaltspunkt: Bei Abschriften steht oft das Jahr der Aufzeichnung, nicht das der Weisung.
Alle Texte außer Grimm (Bd. 1–6) und Hardt wurden mit der Claude-API (Vision) transkribiert und sind noch nicht korrekturgelesen.</p>
</main>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
fetch('daten/punkte.json?v=0.9').then(r=>r.json()).then(d=>{{
  const map=L.map('emap',{{preferCanvas:true}}).setView([49.5,10],5);
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{attribution:'© OpenStreetMap'}}).addTo(map);
  const gruppen=d.editionen.map(()=>L.layerGroup().addTo(map));
  d.punkte.forEach(p=>{{
    const c=d.editionen[p[2]].farbe;
    L.circleMarker([p[0],p[1]],{{radius:4,color:c,weight:1,fillColor:c,fillOpacity:.6}}).bindTooltip(p[3]+(p[4]?' ('+p[4]+')':'')).addTo(gruppen[p[2]]);
  }});
  const leg=document.getElementById('leg');
  const n=d.editionen.map(()=>0); d.punkte.forEach(p=>n[p[2]]++);
  d.editionen.forEach((e,i)=>{{
    if(!n[i]) return;
    const l=document.createElement('label');
    l.innerHTML='<input type="checkbox" checked> <span class="pkt" style="background:'+e.farbe+'"></span>'+e.kurz+' ('+n[i]+')';
    l.querySelector('input').addEventListener('change',ev=>{{ev.target.checked?gruppen[i].addTo(map):map.removeLayer(gruppen[i]);}});
    leg.appendChild(l);
  }});
}});
</script>
</body></html>'''
open('editionen.html', 'w', encoding='utf-8').write(seite)
print('editionen.html', round(len(seite) / 1000), 'kB;', len(pts), 'Punkte')
