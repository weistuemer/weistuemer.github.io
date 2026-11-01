"""Teilt data.json (+ data_weitere.json) in einen schlanken Index und Detail-Häppchen für die schnelle Seite.
Aufruf im Repository-Hauptordner:  python3 baue_site_daten.py   ->  daten/index.json, daten/d_000.json ... """
import json,os,re,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else '.')
import region_gross
HERE=os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else '.'
os.chdir(HERE)
D=json.load(open('data.json',encoding='utf-8'))
if os.path.exists('data_weitere.json'): D+=json.load(open('data_weitere.json',encoding='utf-8'))
CH=250
# Großraum-Typisierung der Region (abgeleitetes Feld, nicht in data.json)
for w,rg in zip(D,region_gross.zuordnen(D)): w['region_gross']=rg
# Dubletten in beide Richtungen verknüpfen (dub_ids = Ids der Gegenstücke)
ROM={'I':1,'II':2,'III':3,'IV':4,'V':5,'VI':6}
byid={w['id']:w for w in D}
grimm=[]
for w in D:
    m=re.match(r'Grimm Bd\. (\d+), S\. (\d+)(?:–(\d+))?',(w.get('edition') or {}).get('stelle','') if isinstance(w.get('edition'),dict) else '')
    if w.get('quelle')=='Grimm' and m: grimm.append((int(m.group(1)),int(m.group(2)),int(m.group(3) or m.group(2)),w['id']))
dub={}
def verknuepfe(a,b):
    if a and b and a!=b:
        dub.setdefault(a,[]); dub.setdefault(b,[])
        if b not in dub[a]: dub[a].append(b)
        if a not in dub[b]: dub[b].append(a)
for w in D:
    for k in ('dublette_id','ueberschneidung_id'):
        if w.get(k) in byid: verknuepfe(w['id'],w[k])
    dv=w.get('dublette_von')
    if dv and not w.get('dublette_id'):
        m=re.search(r'Weisthümer (I{1,3}|IV|V|VI),? S\. (\d+)',dv)
        if m:
            bd,p=ROM[m.group(1)],int(m.group(2))
            for b,a1,a2,gid in grimm:
                if b==bd and a1<=p<=a2: verknuepfe(w['id'],gid); break
for w in D:
    if w['id'] in dub: w['dub_ids']=dub[w['id']]
os.makedirs('daten',exist_ok=True)
for f in os.listdir('daten'):
    if f.startswith('d_') or f=='index.json': os.remove(os.path.join('daten',f))
SLIM=['id','titel','ort','region','region_gross','dub_ids','zeit','typ','typ_norm','typ_form','quelle','sprache','koordinaten','koordinaten_status',
      'dublette_von','dublette_id','dublette_typ','ueberschneidung_mit','ueberschneidung_id','ueberschneidung_anteil','nr_edition','original_link']
idx=[];chunks=[{} for _ in range((len(D)+CH-1)//CH)]
for i,w in enumerate(D):
    c=i//CH
    s={k:w[k] for k in SLIM if k in w and w[k] not in (None,'',[])}
    ed=w.get('edition') if isinstance(w.get('edition'),dict) else {}
    s['edition']={'stelle':ed.get('stelle','')}
    gv=w.get('grimm_vorlage')
    if isinstance(gv,dict):
        s['grimm_vorlage']={'kategorie':gv.get('kategorie','')}
        if gv.get('referat'): s['grimm_vorlage']['referat']={'stufe':gv['referat'].get('stufe','')}
    orig=w.get('originale') or []
    arch=[o for o in orig if o.get('art')=='Archivüberlieferung' and not re.search('keine Original',o.get('zuordnung') or '')]
    s['_o']={'n':len(orig),'archiv':bool(arch),'digi':any(re.match('ja',o.get('digitalisat') or '') for o in arch),
             'ausf':any(re.search('Ausfertigung|Original',o.get('ueberlieferung') or '',re.I) and not re.search('Abschrift',o.get('ueberlieferung') or '',re.I) for o in arch),
             'sbb':any((o.get('art') or '').startswith('Druckvorlage') for o in orig)}
    s['c']=c
    idx.append(s)
    det={k:v for k,v in w.items() if k not in SLIM or k=='original_link'}
    det.pop('id',None); chunks[c][w['id']]=det
json.dump({'version':'0.9','chunks':len(chunks),'eintraege':idx},open('daten/index.json','w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
for c,d in enumerate(chunks): json.dump(d,open(f'daten/d_{c:03d}.json','w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(len(D),'Einträge;',len(chunks),'Häppchen; Index',round(os.path.getsize('daten/index.json')/1e6,1),'MB')
