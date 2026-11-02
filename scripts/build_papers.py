"""data/publications.bib -> data/papers.json (papers, themes, co-authorship edges).

Run from the repository root:  python scripts/build_papers.py
Citation counts are NOT generated here: edit data/citations.csv by hand (key,citations,title).
New bib entries need a theme in THEME below; preprints of a published paper go in MERGE.
"""
import itertools, json, re, unicodedata, csv, os

ROOT = os.path.join(os.path.dirname(__file__), "..")
src = open(os.path.join(ROOT, "data", "publications.bib"), encoding="utf-8").read()

THEMES = [
    dict(id="polar", label="Polarization & echo chambers", color="#60A5FA", ax=0.30, ay=0.34),
    dict(id="mis", label="Misinformation & news", color="#FB923C", ax=0.64, ay=0.32),
    dict(id="algo", label="Algorithms & online behaviour", color="#A78BFA", ax=0.56, ay=0.74),
    dict(id="clim", label="Climate discourse", color="#4ADE80", ax=0.11, ay=0.66),
    dict(id="mob", label="Human mobility", color="#22D3EE", ax=0.86, ay=0.70),
    dict(id="cult", label="Culture & language complexity", color="#F472B6", ax=0.30, ay=0.80),
    dict(id="other", label="Other", color="#94A3B8", ax=0.90, ay=0.20),
]
REMOVE = {"galeazzi2022opinion", "galeazzi2018reputation"}  # PhD and MSc theses
MERGE = {  # preprint -> published version of the same work
    "cinelli2020echo": "cinelli2021echo", "bonaccorsi2020evidence": "bonaccorsi2020economic",
    "falkenberg2021growing": "falkenberg2022growing", "etta2021news": "etta2022comparing",
    "etta2020information": "etta2022comparing", "torricelli2023hurricanes": "torricelli2023does",
    "baqir2023beyond": "baqir2025unveiling", "baqir2023social": "baqir2026beyond",
    "baqir2023news": "baqir2024news", "di2024sampled": "di2026sampled",
    "szamely2024easy": "szamely2025easy", "di2024characterizing": "di2025ideological",
    "loru2024sets": "loru2025ideology", "di2025decoding": "di2026decoding",
    "falkenberg2025towards": "falkenberg2026toward",
}
THEME = {
    "cinelli2021echo": "polar", "flamino2023political": "polar", "loru2025ideology": "polar",
    "di2025ideological": "polar", "falkenberg2026toward": "polar", "baqir2026beyond": "polar",
    "di2026sampled": "polar", "di2026platform": "polar",
    "cinelli2020covid": "mis", "cinelli2022conspiracy": "mis", "cinelli2020limited": "mis",
    "galeazzi2024unveiling": "mis", "etta2022comparing": "mis", "baqir2024news": "mis",
    "etta2022covid": "mis", "santoro2023analyzing": "mis", "szamely2025easy": "mis", "valensise2021lack": "mis",
    "falkenberg2022growing": "clim", "torricelli2023does": "clim",
    "alipour2024cross": "algo", "galeazzi2026revealing": "algo", "baqir2025unveiling": "algo",
    "sartori2025insights": "algo", "valensise2019drifts": "algo",
    "bonaccorsi2020economic": "mob", "galeazzi2021human": "mob",
    "valensise2021entropy": "cult", "di2026decoding": "cult", "fracaro2026disc": "cult", "amadori2025involvement": "cult",
    "gentil2017deep": "other", "galeazzi2021reputation": "other", "galeazzi2021ecological": "other",
}
# strongest co-authorship links that tie otherwise separate themes into one network
EXTRA_BRIDGES = [("falkenberg2022growing", "loru2025ideology"), ("torricelli2023does", "loru2025ideology"),
                 ("cinelli2020covid", "bonaccorsi2020economic")]
TITLE_FIX = {"from Sinatra to swift": "from Sinatra to Swift", "interests on reddit": "interests on Reddit"}

def unlatex(s):
    for a, b in (("{\\`o}", "ò"), ("{\\'a}", "á"), ('{\\"o}', "ö"), ("{\\`a}", "à")):
        s = s.replace(a, b)
    return s.replace("{", "").replace("}", "").replace("Niccolo'", "Niccolò")

def venue(e):
    j = e.get("journal") or e.get("booktitle") or e.get("publisher") or ""
    if "arXiv" in j: return "arXiv preprint", True
    if j == "OSF": return "OSF preprint", True
    for k, v in (("GLOBECOM", "IEEE GLOBECOM"), ("MedComNet", "IEEE MedComNet"), ("Applied Computing", "ACM SAC"),
                 ("EMNLP", "Findings of EMNLP"), ("NDSS", "NDSS")):
        if k in j: return v, False
    return {"Proceedings of the National Academy of Sciences": "PNAS", "Scientific reports": "Scientific Reports",
            "PloS one": "PLOS ONE", "IEEE Transactions on Computational Social Systems": "IEEE TCSS"}.get(j, j), False

def author(a):
    a = unlatex(a).strip()
    if a == "others": return None
    last, first = [x.strip() for x in a.split(",", 1)] if "," in a else (a.split()[-1], " ".join(a.split()[:-1]))
    if last == "Morales": last, first = "De Francisci Morales", "Gianmarco"
    if last == "Sasso": last, first = "Lo Sasso", "Andrea"
    key = unicodedata.normalize("NFKD", (last + " " + first[:1]).lower()).encode("ascii", "ignore").decode()
    initials = " ".join(p[0] + "." for p in first.replace("-", " ").split() if p and p[0].isalpha())
    return key, (initials + " " + last).strip()

papers = []
for m in re.finditer(r"@(\w+)\{([^,]+),(.*?)\n\}", src, re.S):
    k, body = m.group(2).strip(), m.group(3)
    e = dict((a.lower(), b.strip()) for a, b in re.findall(r"(\w+)=\{(.*)\},?\s*$", body, re.M))
    if k in REMOVE or k in MERGE: continue
    assert k in THEME, "add a theme for " + k
    v, pre = venue(e)
    auth = [author(a) for a in e["author"].split(" and ")]
    etal = any(a is None for a in auth)
    auth = [a for a in auth if a]
    t = unlatex(e["title"])
    for a, b in TITLE_FIX.items(): t = t.replace(a, b)
    papers.append(dict(key=k, t=t, au=[a[1] for a in auth], etal=etal, v=v, yr=int(e["year"]), pre=pre,
                       theme=THEME[k], _keys={a[0] for a in auth} - {"galeazzi a"}))

idx = {p["key"]: i for i, p in enumerate(papers)}
def jac(a, b):
    A, B = papers[a]["_keys"], papers[b]["_keys"]
    return len(A & B) / len(A | B) if A and B else 0.0
edges = []
for a, b in itertools.combinations(range(len(papers)), 2):
    if "other" in (papers[a]["theme"], papers[b]["theme"]): continue  # 'Other' papers stay single nodes
    j, same = jac(a, b), papers[a]["theme"] == papers[b]["theme"]
    if (same and j >= 0.2) or (not same and j >= 0.5):
        edges.append([a, b, round(j, 2), 0 if same else 1])
# keep every theme in one piece: join loose papers to the theme's most cited one
cites = {}
cpath = os.path.join(ROOT, "data", "citations.csv")
if os.path.exists(cpath):
    for r in csv.DictReader(open(cpath, encoding="utf-8")):
        if r["citations"].strip(): cites[r["key"]] = int(r["citations"])
for th in {p["theme"] for p in papers} - {"other"}:
    ids = [i for i, p in enumerate(papers) if p["theme"] == th]
    hub = max(ids, key=lambda i: (cites.get(papers[i]["key"], 0), -papers[i]["yr"]))
    adj = {i: set() for i in ids}
    for a, b, j, x in edges:
        if not x and a in adj: adj[a].add(b); adj[b].add(a)
    seen, todo = {hub}, [hub]
    while todo:
        u = todo.pop()
        for w in adj[u] - seen: seen.add(w); todo.append(w)
    for i in ids:
        if i in seen: continue
        edges.append([min(i, hub), max(i, hub), 0, 0]); adj[i].add(hub)
        todo = [i]; seen.add(i)
        while todo:
            u = todo.pop()
            for w in adj[u] - seen: seen.add(w); todo.append(w)
for a, b in EXTRA_BRIDGES:
    i, j = sorted((idx[a], idx[b]))
    if not any(e[0] == i and e[1] == j for e in edges):
        edges.append([i, j, round(jac(i, j), 2), 1])
for p in papers: del p["_keys"]
json.dump(dict(themes=THEMES, papers=papers, edges=edges), open(os.path.join(ROOT, "data", "papers.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=0)
print(len(papers), "papers,", len(edges), "edges")
