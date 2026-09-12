#!/usr/bin/env python3
"""문헌 수집기 — 발굴팀의 눈. LLM을 쓰지 않는다.

매일 돌면서 연구실의 관심 영역에서 **새로 나온 것만** 골라낸다.
판정은 하지 않는다 — 무엇이 새로 나왔는지만 정확히 알려주고, 해석은 발굴팀(LLM)이 한다.

이 분리가 중요한 이유: 수집을 LLM에게 시키면 검색이 재현되지 않고, 본 것을 또 보고,
없는 논문을 만들어낸다. 수집은 결정적이어야 한다.

  discover.py                 관심 영역 전체를 훑는다 (기본 7일)
  discover.py --days 30       기간 지정
  discover.py --topic llm-med 한 영역만
  discover.py --watch         감시 목록(진행 연구·후보 주제)만 — 선행권 위협 탐지
  discover.py --dry           _seen.tsv 를 갱신하지 않는다 (시험용)

출력: `_team/ideas/_incoming/YYYY-MM-DD.md` — 새 항목만. 없으면 파일을 만들지 않는다.
중복 제거: `_team/ideas/_seen.tsv` (id, 최초 확인일)

API는 전부 키가 필요 없다: PubMed E-utilities · medRxiv · arXiv · ClinicalTrials.gov v2.
LLM 방법론은 학술지보다 arXiv가 몇 달 빠르므로 그쪽을 먼저 본다.
"""
import os, sys, io, json, time, argparse, datetime, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from collections import OrderedDict
from pathlib import Path

TEAM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IDEAS = os.path.join(TEAM, "ideas")
INCOMING = os.path.join(IDEAS, "_incoming")
SEEN = os.path.join(IDEAS, "_seen.tsv")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
UA = "AI-Research-Team/1.0 (lab literature monitor%s)" % (("; mailto:" + os.environ["LAB_CONTACT_EMAIL"]) if os.environ.get("LAB_CONTACT_EMAIL") else "")

# 관심 영역 — _team/lab.yaml 의 ideation.topics 가 있으면 그것을 쓰고, 없으면 아래 본보기 둘.
DEFAULT_TOPICS = OrderedDict([
    ("llm-med-meta", {
        "label": "LLM × 의학 — 메타연구·비임상",
        "pubmed": '("large language model*"[tiab] OR "LLM"[tiab] OR ChatGPT[tiab] OR GPT-4[tiab]) '
                  'AND (benchmark*[tiab] OR evaluation[tiab] OR reproducib*[tiab] OR hallucinat*[tiab] '
                  'OR "peer review"[tiab] OR citation*[tiab] OR "systematic review"[tiab] OR reporting[tiab])',
        "medrxiv": ["large language model", "LLM", "GPT"],
        "arxiv": '(cat:cs.CL OR cat:cs.AI OR cat:cs.LG) AND '
                 '(abs:medical OR abs:clinical OR abs:medicine OR abs:biomedical OR abs:healthcare)',
    }),
    ("example-field", {
        "label": "(본보기) 내 전공 × 인공지능 — 심전도 예",
        "pubmed": '(electrocardiogra*[tiab] OR ECG[tiab] OR EKG[tiab]) '
                  'AND ("deep learning"[tiab] OR "artificial intelligence"[tiab] OR "machine learning"[tiab]) '
                  'AND (screening[tiab] OR detect*[tiab] OR diagnos*[tiab])',
        "medrxiv": ["electrocardiogram deep learning", "AI-ECG"],
        "arxiv": '(cat:eess.SP OR cat:cs.LG OR cat:cs.CV) AND (abs:electrocardiogram OR abs:ECG)',
    }),
])


def _topics_from_config():
    try:
        import labconfig
        cfg = labconfig.load()
        out = OrderedDict()
        for t in cfg["ideation"].get("topics") or []:
            if not t.get("key") or not (t.get("pubmed") or t.get("medrxiv") or t.get("arxiv")):
                continue
            d = {"label": t.get("label") or t["key"]}
            if t.get("pubmed"): d["pubmed"] = t["pubmed"]
            if t.get("medrxiv"): d["medrxiv"] = list(t["medrxiv"])
            if t.get("arxiv"): d["arxiv"] = t["arxiv"]
            out[t["key"]] = d
        return out
    except Exception:
        return OrderedDict()


TOPICS = _topics_from_config() or DEFAULT_TOPICS


# 못 가져온 곳을 기억해 둔다. 실패를 '신규 없음'과 구별하기 위해서다.
#
# 2026-09-05 확인: 맥미니의 새벽 수집이 9/1 이후 매일 '신규 없음'이었는데,
# 같은 도구를 노트북에서 돌리면 121건이 나왔다. 실패해도 빈손과 똑같이 보고해서
# 일주일 동안 아무도 몰랐다. 발굴팀이 멈춘 것을 '새 논문이 없나 보다'로 읽고 있었다.
FAILED = []


def fetch(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf8", "replace"))
        except Exception as e:
            last = e
            if i == tries - 1:
                host = urllib.parse.urlsplit(url).netloc
                FAILED.append((host, type(e).__name__, str(e)[:90]))
                return None
            time.sleep(2 * (i + 1))
    return None


# ---------- 원천별 수집 ----------
def pubmed(query, days, retmax=40):
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    q = urllib.parse.quote(query)
    js = fetch(f"{base}esearch.fcgi?db=pubmed&term={q}&reldate={days}&datetype=edat"
               f"&retmode=json&retmax={retmax}&sort=date")
    ids = ((js or {}).get("esearchresult") or {}).get("idlist") or []
    if not ids:
        return []
    time.sleep(0.4)
    su = fetch(f"{base}esummary.fcgi?db=pubmed&id={','.join(ids)}&retmode=json")
    res = []
    for pid in ids:
        d = ((su or {}).get("result") or {}).get(pid)
        if not d:
            continue
        res.append({"id": "pmid:" + pid, "title": (d.get("title") or "").strip().rstrip("."),
                    "date": d.get("epubdate") or d.get("pubdate", ""),
                    "venue": d.get("source", ""),
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pid}/"})
    return res


def medrxiv(terms, days, cap=60):
    """medRxiv는 주제 검색 API가 없다. 날짜 구간을 받아 제목으로 거른다."""
    end = datetime.date.today()
    start = end - datetime.timedelta(days=days)
    out, cursor = [], 0
    low = [t.lower() for t in terms]
    while cursor < 900:
        js = fetch(f"https://api.biorxiv.org/details/medrxiv/{start}/{end}/{cursor}")
        coll = (js or {}).get("collection") or []
        if not coll:
            break
        for p in coll:
            blob = (p.get("title", "") + " " + p.get("abstract", "")).lower()
            if any(t in blob for t in low):
                out.append({"id": "doi:" + p.get("doi", ""), "title": (p.get("title") or "").strip(),
                            "date": p.get("date", ""), "venue": "medRxiv",
                            "url": "https://doi.org/" + p.get("doi", "")})
        cursor += 100
        if len(out) >= cap:
            break
        time.sleep(0.3)
    return out[:cap]


def arxiv(query, days, cap=60, scan=150):
    """arXiv Atom API. LLM 방법론은 학술지보다 여기가 몇 달 빠르다.

    `submittedDate` 범위 필터는 쓰지 않는다 — 최근 구간에서 결과가 거의 0으로 무너진다
    (2026-09-01 확인: 같은 질의가 범위 있으면 1건, 없으면 14,140건).
    최신순으로 받아 날짜는 이쪽에서 자른다.
    """
    url = ("https://export.arxiv.org/api/query?search_query=%s"
           "&sortBy=submittedDate&sortOrder=descending&max_results=%d"
           % (urllib.parse.quote(query, safe=":[]"), scan))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=45) as r:
            root = ET.fromstring(r.read())
    except Exception as exc:
        FAILED.append(("export.arxiv.org", type(exc).__name__, str(exc)[:90]))
        return []
    ns = {"a": "http://www.w3.org/2005/Atom"}
    cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    out = []
    for e in root.findall("a:entry", ns):
        pub = (e.findtext("a:published", "", ns) or "")[:10]
        if pub < cutoff:
            break                       # 최신순이므로 여기서 끝내면 된다
        aid = (e.findtext("a:id", "", ns) or "").rsplit("/", 1)[-1]
        if not aid:
            continue
        out.append({"id": "arxiv:" + aid.split("v")[0],
                    "title": " ".join((e.findtext("a:title", "", ns) or "").split()),
                    "date": pub, "venue": "arXiv",
                    "url": "https://arxiv.org/abs/" + aid})
        if len(out) >= cap:
            break
    return out


def trials(term, days, cap=20):
    since = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    q = urllib.parse.quote(term)
    js = fetch("https://clinicaltrials.gov/api/v2/studies"
               f"?query.term={q}&filter.advanced=AREA%5BLastUpdatePostDate%5DRANGE%5B{since}%2CMAX%5D"
               f"&pageSize={cap}&fields=NCTId,BriefTitle,LastUpdatePostDate,OverallStatus")
    out = []
    for st in ((js or {}).get("studies") or []):
        ps = st.get("protocolSection", {})
        idm = ps.get("identificationModule", {})
        stm = ps.get("statusModule", {})
        nct = idm.get("nctId", "")
        out.append({"id": "nct:" + nct, "title": idm.get("briefTitle", ""),
                    "date": (stm.get("lastUpdatePostDateStruct") or {}).get("date", ""),
                    "venue": "ClinicalTrials.gov · " + (stm.get("overallStatus") or ""),
                    "url": f"https://clinicaltrials.gov/study/{nct}"})
    return out


# ---------- 중복 제거 ----------
# ---------- 우리 것 걸러내기 ----------
OURS_PATH = os.path.join(IDEAS, "_ours.yaml")
_OURS = None
OURS_HITS = []


def load_ours():
    """우리 연구실이 낸 것들. 없으면 빈 목록 — 거르지 않는다."""
    global _OURS
    if _OURS is not None:
        return _OURS
    _OURS = {"dois": [], "repos": [], "registrations": [], "titles": [], "authors": []}
    try:
        cur = None
        for line in Path(OURS_PATH).read_text(encoding="utf8").splitlines():
            t = line.split("#")[0].rstrip()
            if not t.strip():
                continue
            if not t.startswith((" ", "-")) and t.endswith(":"):
                cur = t[:-1].strip()
            elif t.strip().startswith("- ") and cur in _OURS:
                _OURS[cur].append(t.strip()[2:].strip().strip('"\''))
    except OSError:
        pass
    return _OURS


def is_ours(r):
    """이 문헌이 우리가 낸 것인가. 식별자와 제목으로 본다."""
    o = load_ours()
    hay = " ".join([str(r.get("id", "")), str(r.get("url", "")), str(r.get("title", ""))]).lower()
    for key in ("dois", "repos", "registrations"):
        for v in o[key]:
            if v.lower() in hay:
                return v
    title = str(r.get("title", "")).lower()
    for v in o["titles"]:
        if v.lower() in title:
            return v
    return None


def drop_ours(rows):
    """우리 것을 빼고 돌려준다. 뺀 것은 기억해 뒀다가 알린다 —
    조용히 빼면 '왜 안 잡히지'가 되고, 그대로 두면 자기 논문을 경쟁 연구로 보고한다."""
    out = []
    for r in rows:
        m = is_ours(r)
        if m:
            OURS_HITS.append((r.get("title", "")[:70], m))
        else:
            out.append(r)
    return out



def load_seen():
    s = set()
    if os.path.exists(SEEN):
        for line in Path(SEEN).read_text(encoding="utf8").splitlines():
            p = line.split("\t")
            if p:
                s.add(p[0])
    return s


def save_seen(new_ids):
    os.makedirs(IDEAS, exist_ok=True)
    first = not os.path.exists(SEEN)
    with open(SEEN, "a", encoding="utf8") as f:
        if first:
            f.write("id\tfirst_seen\n")
        today = datetime.date.today().isoformat()
        for i in sorted(new_ids):
            f.write(f"{i}\t{today}\n")


def load_watchlist():
    p = os.path.join(IDEAS, "_watchlist.yaml")
    if not os.path.exists(p):
        return []
    try:
        import yaml
        return (yaml.safe_load(open(p, encoding="utf8")) or {}).get("watch", [])
    except Exception:
        return []


def report_failures():
    """못 읽은 원천을 사람이 읽을 수 있게 알린다."""
    import collections as _c
    by = _c.Counter(h for h, _, _ in FAILED)
    if not FAILED:
        return                                   # 실패가 없으면 경고도 없다
    print("⚠ 자료를 받아오지 못한 곳 %d건:" % len(FAILED))
    for host, n in by.most_common():
        why = next(m for h, t, m in FAILED if h == host)
        print("   %-34s %2d회 실패 — %s" % (host, n, why))
    print("   → 그 컴퓨터에서 바깥 인터넷이 막혀 있거나 상대 쪽이 거부하는 것이다.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--topic")
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    seen = load_seen()
    groups, fresh = OrderedDict(), set()

    if a.watch:
        for w in load_watchlist():
            hits = []
            if w.get("pubmed"):
                hits += pubmed(w["pubmed"], a.days, retmax=25)
            if w.get("trials"):
                hits += trials(w["trials"], a.days)
            if w.get("medrxiv"):
                hits += medrxiv(w["medrxiv"], a.days, cap=25)
            if w.get("arxiv"):
                hits += arxiv(w["arxiv"], a.days, cap=25)
            hits = drop_ours(hits)
            new = [h for h in hits if h["id"] not in seen and h["id"] not in fresh]
            if new:
                groups["[감시] %s — %s" % (w.get("owner", "?"), w.get("why", ""))] = new
                fresh |= {h["id"] for h in new}
    else:
        if a.topic and a.topic not in TOPICS:
            ap.error("모르는 관심 영역: %s (가능: %s)" % (a.topic, ", ".join(TOPICS)))
        items = TOPICS.items() if not a.topic else [(a.topic, TOPICS[a.topic])]
        for key, t in items:
            hits = []
            if t.get("pubmed"):
                hits += pubmed(t["pubmed"], a.days)
            if t.get("medrxiv"):
                hits += medrxiv(t["medrxiv"], a.days)
            if t.get("arxiv"):
                hits += arxiv(t["arxiv"], a.days)
            if t.get("trials"):
                hits += trials(t["trials"], a.days)
            hits = drop_ours(hits)
            new = [h for h in hits if h["id"] not in seen and h["id"] not in fresh]
            if new:
                groups[t["label"]] = new
                fresh |= {h["id"] for h in new}

    if not fresh:
        if OURS_HITS:
            print("우리 것 %d건은 뺐다 (`_ours.yaml`)." % len(OURS_HITS))
        if FAILED:
            report_failures()
            print("신규 없음 — 다만 위 원천을 못 읽었으므로 '없다'고 단정할 수 없다.")
        else:
            print("신규 없음 — 파일을 만들지 않는다. (모든 원천 정상)")
        return

    if a.dry:
        report_failures()
        print("미리보기: 신규 %d건 — 파일과 수집 이력은 바꾸지 않았다." % len(fresh))
        for label, rows in groups.items():
            print("  %s: %d건" % (label, len(rows)))
        return

    os.makedirs(INCOMING, exist_ok=True)
    today = datetime.date.today().isoformat()
    path = os.path.join(INCOMING, f"{today}{'_watch' if a.watch else ''}.md")
    # 하루에 두 번 이상 돌 수 있다. 그때 앞서 모은 것을 덮어쓰면 조용히 사라진다 —
    # 2026-09-05 에 실제로 감시 70건이 2건으로 줄었다. 그래서 이어 붙인다.
    exists = os.path.exists(path)
    with open(path, "a" if exists else "w", encoding="utf8") as f:
        if exists:
            f.write(f"\n\n---\n\n## 추가 수집 — {datetime.datetime.now():%H:%M} (최근 {a.days}일)\n\n")
            f.write(f"**{len(fresh)}건** 더 모았다. 위쪽은 앞선 회차의 것이다.\n\n")
        else:
            f.write(f"# 신규 문헌 — {today} (최근 {a.days}일{', 감시 목록' if a.watch else ''})\n\n")
            f.write(f"총 **{len(fresh)}건**. 이미 본 것은 제외했다(`_seen.tsv` {len(seen)}건 기준).\n\n")
        for label, rows in groups.items():
            f.write(f"## {label} — {len(rows)}건\n\n")
            for r in rows:
                f.write(f"- **{r['title']}**  \n  {r['venue']} · {r['date']} · [{r['id']}]({r['url']})\n")
            f.write("\n")
    if not a.dry:
        save_seen(fresh)
    if FAILED:
        report_failures()
    if OURS_HITS:
        print("우리 것 %d건은 뺐다 (`_ours.yaml`):" % len(OURS_HITS))
        for t, why in OURS_HITS[:5]:
            print("   %s  ← %s" % (t, why))
    print(f"신규 {len(fresh)}건 → {os.path.relpath(path, TEAM)}")
    for label, rows in groups.items():
        print(f"  {label}: {len(rows)}건")


if __name__ == "__main__":
    main()
