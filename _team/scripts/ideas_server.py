#!/usr/bin/env python3
"""발굴 현황판 서버 — 화면에서 누른 판정을 카드에 받아 적는다.

파일로 연 화면(`file://`)은 저장을 못 한다. 일정 대시보드가 같은 이유로 작은 서버를 쓰고
있으므로 같은 방식을 따른다. 설치할 것은 없다 — 파이썬 표준 기능만 쓴다.

    python3 ideas_server.py        → http://localhost:8790

## 판정 셋

    채택   본격적인 연구 아이템으로 발전시킨다. 카드 단계를 adopted 로 바꾸고
           제안 큐에 프로젝트 등록 안건을 올린다 (실제 등록은 project-intake 가 한다)
    보류   좀 더 생각해 본다. 단계를 on-hold 로 바꾸고 되돌아볼 날짜를 적는다
    기각   연구에 적합하지 않다. 카드를 `_dropped/` 로 옮긴다 — 지우지 않는다

세 판정 모두 `_team/ideas/_decisions.tsv` 에 날짜·후보·판정·사유로 남는다.
되돌리려면 그 기록을 보고 카드를 되돌리면 된다.
"""
import http.server, socketserver, json, os, io, re, shutil, datetime, threading, subprocess

PORT = int(os.environ.get("IDEAS_PORT", 8790))
SCRIPTS = os.path.dirname(os.path.abspath(__file__))
TEAM = os.path.dirname(SCRIPTS)
IDEAS = os.path.join(TEAM, "ideas")
DROPPED = os.path.join(IDEAS, "_dropped")
LOG = os.path.join(IDEAS, "_decisions.tsv")
DECISIONS_MD = os.path.join(TEAM, "decisions.md")
_lock = threading.Lock()

DECISIONS = {
    "채택": ("adopted", "본격 연구로 발전"),
    "보류": ("on-hold", "더 생각해 본다"),
    "기각": ("dropped", "연구에 적합하지 않음"),
}


def card_path(cid):
    for f in os.listdir(IDEAS):
        if f.startswith(cid + "_") and f.endswith(".md"):
            return os.path.join(IDEAS, f)
    return None


def set_stage(path, stage, note, today):
    """카드의 단계 줄을 바꾸고 판정 기록을 덧붙인다. 나머지는 건드리지 않는다."""
    s = io.open(path, encoding="utf8").read()
    s2 = re.sub(r"^\|\s*단계\s*\|[^|]*\|$", "| 단계 | %s |" % stage, s, count=1, flags=re.M)
    if s2 == s:                      # 단계 줄이 없으면 표 첫 줄 뒤에 넣는다
        s2 = s.replace("| 항목 | 내용 |", "| 항목 | 내용 |\n| 단계 | %s |" % stage, 1)
    s2 = re.sub(r"^\|\s*최종 갱신\s*\|[^|]*\|$", "| 최종 갱신 | %s |" % today, s2, count=1, flags=re.M)
    s2 = s2.rstrip("\n") + "\n\n## 판정 — %s\n\n**%s** (연구책임자, 발굴 현황판에서)\n\n%s\n" % (
        today, stage, note or "(사유 없음)")
    tmp = path + ".tmp"
    io.open(tmp, "w", encoding="utf8").write(s2)
    os.replace(tmp, path)


def log_decision(today, cid, title, decision, note):
    new = not os.path.exists(LOG)
    with io.open(LOG, "a", encoding="utf8") as f:
        if new:
            f.write("date\tid\ttitle\tdecision\tnote\n")
        f.write("\t".join([today, cid, title.replace("\t", " "),
                           decision, (note or "").replace("\t", " ").replace("\n", " ")]) + "\n")


def make_proposal(today, cid, title, note):
    """채택은 프로젝트가 되는 일이다. 등록 자체는 사람이 project-intake 로 한다 —
    여기서는 '이것을 등록해야 한다'를 제안 큐에 올려 잊히지 않게 한다."""
    with io.open(DECISIONS_MD, "a", encoding="utf8") as f:
        f.write("\n| %s | %s %s — **채택** (발굴 현황판에서) | 발굴 | %s · 다음: 총괄팀장 창에서 `/project-intake` 로 등록 |\n"
                % (today, cid, title.replace("|", "·"), (note or "(사유 없음)").replace("|", "·").replace("\n", " ")))
    return
    io.open(os.devnull, "w", encoding="utf8").write(
        "---\nid: %s_adopt-%s\nteam: 발굴\nkind: 승인\nurgency: none\nreversible: yes\n"
        "decision: 채택\ndecided_on: %s\nnote: 발굴 현황판에서 연구책임자가 채택함\n---\n\n"
        "# %s %s — 채택됨. 프로젝트로 등록해야 한다\n\n"
        "연구책임자가 %s 발굴 현황판에서 **채택**으로 판정했다.\n\n"
        "%s\n\n## 남은 일\n\n"
        "1. `project-intake` 로 정식 등록 — 미배정 팀(Ceres·Pluto) 중 하나에 배정\n"
        "2. `registry.yaml` 에 프로젝트 추가, `PROJECT.md` 카드 작성\n"
        "3. 카드(`_team/ideas/%s_*.md`)의 단계를 adopted 로 둔 채 색인에 남긴다\n"
        % (today, cid, today, cid, title, today, (note or "").strip() or "(사유 없음)", cid))


def regenerate():
    try:
        subprocess.run(["python3", os.path.join(SCRIPTS, "ideation_dashboard.py")],
                       capture_output=True, timeout=60)
    except Exception:
        pass


def decide(cid, decision, note):
    if decision not in DECISIONS:
        return {"ok": False, "error": "모르는 판정: %s" % decision}
    path = card_path(cid)
    if not path:
        return {"ok": False, "error": "카드를 찾지 못했다: %s" % cid}
    today = datetime.date.today().isoformat()
    stage, _ = DECISIONS[decision]
    title = ""
    m = re.search(r"^#\s+I\d+\s+(.*)$", io.open(path, encoding="utf8").read(), re.M)
    if m:
        title = m.group(1).strip()

    with _lock:
        set_stage(path, stage, note, today)
        if decision == "기각":
            os.makedirs(DROPPED, exist_ok=True)
            dst = os.path.join(DROPPED, os.path.basename(path))
            shutil.move(path, dst)
        if decision == "채택":
            make_proposal(today, cid, title, note)
        log_decision(today, cid, title, decision, note)
    regenerate()
    return {"ok": True, "id": cid, "decision": decision, "stage": stage}


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=IDEAS, **kw)

    def log_message(self, *a):
        pass

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", ""):
            self.path = "/dashboard.html"
        # 서체는 현황판 폴더에 있다. 서버는 상위 폴더로 못 나가므로 여기서 직접 내준다.
        if self.path == "/Pretendard.woff2":
            p = os.path.join(TEAM, "dashboard", "assets", "Pretendard.woff2")
            if os.path.exists(p):
                self.send_response(200)
                self.send_header("Content-Type", "font/woff2")
                self.send_header("Content-Length", str(os.path.getsize(p)))
                self.send_header("Cache-Control", "max-age=86400")
                self.end_headers()
                try:
                    with open(p, "rb") as fh:
                        shutil.copyfileobj(fh, self.wfile)
                except (BrokenPipeError, ConnectionResetError):
                    pass          # 브라우저가 중간에 끊은 것. 서버는 계속 간다
                return
        return super().do_GET()

    def do_POST(self):
        if self.path != "/decide":
            return self._json(404, {"ok": False, "error": "없는 주소"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            d = json.loads(self.rfile.read(n).decode("utf8"))
        except Exception as e:
            return self._json(400, {"ok": False, "error": "읽지 못했다: %s" % e})
        return self._json(200, decide(str(d.get("id", "")), str(d.get("decision", "")),
                                      d.get("note", "")))


def main():
    os.makedirs(IDEAS, exist_ok=True)
    regenerate()
    # 한 번에 하나만 처리하면 요청 하나가 끊길 때 서버 전체가 멈춘다.
    # 2026-09-07 실제로 그랬다 — 브라우저가 2MB 서체를 받다 끊자 Broken pipe 로 서버가 죽었다.
    class Server(socketserver.ThreadingTCPServer):
        daemon_threads = True
        allow_reuse_address = True

        def handle_error(self, request, client_address):
            # 연결이 끊기는 것은 사고가 아니다. 브라우저는 늘 이렇게 한다.
            import sys as _s
            t = _s.exc_info()[0]
            if t in (BrokenPipeError, ConnectionResetError):
                return
            super().handle_error(request, client_address)

    with Server(("127.0.0.1", PORT), Handler) as httpd:
        print("발굴 현황판 → http://localhost:%d  (판정이 카드에 바로 기록된다)" % PORT)
        print("멈추려면 Ctrl+C")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
