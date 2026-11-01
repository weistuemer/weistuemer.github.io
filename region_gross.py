"""Gröbere Regionstypisierung (Feld region_gross) für die Weistümer-Datenbank.
Regel 1: Das früheste Schlüsselwort in der Regionsangabe bestimmt den Großraum.
Regel 2: Ohne Treffer wird der Großraum aus den Koordinaten der räumlich nächsten, bereits zugeordneten Einträge abgeleitet.
Regel 3: Sonst „Ohne Angabe“."""
import re, math, collections
R = [
 ('Westfalen und Niedersachsen', ['westfalen','niedersachsen','lüneburg','hildesheim','harz','stedinger','oldenburg','bremen','braunschweig','calenberg','hannover','weser','aller','verden','hadeln','ocker und leine','an der aue']),
 ('Niederrhein und Maas', ['niederrhein','rheinland','jülich','köln','geldern','ruhr und maas','rhein, ruhr und maas','aachen','kempen','bonn','zülpich','düren']),
 ('Eifel, Hunsrück und Hochwald', ['eifel','hundsrück','hunsrück','hunsrueck','idarwald','prüm','hochwald']),
 ('Mosel und Kurtrier', ['untermosel','obermosel','mosel','trier','kurtrier']),
 ('Luxemburg und Lothringen', ['luxemburg','lothringen']),
 ('Saar, Nahe und Pfalz', ['saar','saargau','saargebiet','tholey','blieskastel','zweibrücken','alsenz','speier','merzig','pfalz','westrich','queich','nahegau','nahe','sponheim','leiningen','speyer']),
 ('Mittelrhein, Westerwald und Lahn', ['westerwald','lahn, rhein, sieg','dietz','nassau','limburg','pellenz','rheingau','rheinhessen','mainz','onesheim','onsheim','wied','ysenburg','mittelrhein']),
 ('Hessen und Wetterau', ['wetterau','hessen','fulda','hanau','dreieich','seligenstadt','taunus','main, rhein, lahn','schlüchtern']),
 ('Rhein-Main-Neckar (Odenwald)', ['neckar, main','odenwald','bergstraße','babenhausen']),
 ('Franken', ['franken','rieneck','würzburg','bamberg','spessart']),
 ('Thüringen und Sachsen', ['thüringen','sachsen']),
 ('Württemberg und Schwaben', ['württemberg','schwaben','ries','huisheim','hohenlohe','löwenstein','neresheim','öttingen']),
 ('Baden und Schwarzwald', ['schwarzwald','breisgau','baden','oberrhein','markgräflerland','kinzigtal','wiesental','klettgau','stühlingen','bodensee','ortenau','säckingen']),
 ('Elsass', ['elsass','elsasz','unterelsass','oberelsass']),
 ('Schweiz', ['zürich','thurgau','aargau','schwyz','st. gallen','st gallen','sankt gallen','basel','waadt','bern','luzern','lucern','zug','graubünden','toggenburg','unterwalden','solothurn','schaffhausen','prättigau','sarganserland','rheintal','rheinthal','schweiz','neuenburg','biel','tessenberg','schafhausen','uri','glarus','freiburg im üechtland','wallis']),
 ('Altbayern', ['baiern','bayern','peitingau','oberbayern','niederbayern','oberpfalz']),
 ('Tirol und Salzburg', ['tirol','salzburg','burggrafenamt','vinschgau','pinzgau','pongau','pustertal']),
 ('Niederösterreich', ['niederösterreich','österreich']),
 ('Steiermark und Kärnten', ['steiermark','kärnten']),
 ('Mähren', ['mähren']),
]
ALLE = [n for n, _ in R] + ['Ohne Angabe']
KW = []
for n, ks in R:
    for k in ks:
        pat = re.compile((r'(?<![a-zäöüß])' + re.escape(k) + r'(?![a-zäöüß])') if len(k) <= 4 else re.escape(k))
        KW.append((n, pat))
def nach_label(label):
    l = (label or '').lower()
    best = None
    for n, p in KW:
        m = p.search(l)
        if m and (best is None or m.start() < best[0] or (m.start() == best[0] and len(m.group()) > best[2])):
            best = (m.start(), n, len(m.group()))
    return best[1] if best else None
def koord(e):
    k = e.get('koordinaten')
    return (k['lat'], k['lng']) if isinstance(k, dict) and k.get('lat') else None
def zuordnen(D, k=7):
    out = [nach_label(e.get('region')) for e in D]
    ref = [(koord(e), o) for e, o in zip(D, out) if o and koord(e)]
    for i, (e, o) in enumerate(zip(D, out)):
        if o: continue
        p = koord(e)
        if not p: out[i] = 'Ohne Angabe'; continue
        ds = sorted(((p[0]-q[0])**2 + ((p[1]-q[1])*0.65)**2, g) for q, g in ref)[:k]
        c = collections.Counter()
        for d, g in ds: c[g] += 1 / (0.01 + d)
        out[i] = c.most_common(1)[0][0]
    return out
if __name__ == '__main__':
    import json
    D = json.load(open('data.json')) + json.load(open('data_weitere.json'))
    ol = [nach_label(e.get('region')) for e in D]
    og = zuordnen(D)
    print('per Label', sum(1 for o in ol if o), 'per Koordinate/Rest', sum(1 for o in ol if not o))
    print(collections.Counter(og).most_common())
    un = collections.Counter((e.get('region') or '', og[i]) for i, e in enumerate(D) if not ol[i])
    print(un.most_common(25))
