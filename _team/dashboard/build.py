#!/usr/bin/env python3
"""현황판 빌드 — source.html 에 폰트를 심어 게시본을 만든다.

`source.html`은 폰트 자리를 `@@FONT@@` 표시로 비워 둔 원본이다(428K).
게시본은 Pretendard 2MB를 base64로 박아 넣은 것(3MB)이라 편집용으로 쓰지 않는다.
**고칠 때는 언제나 source.html 을 고친다.**

  build.py            dist/lab-dashboard.html 생성
  build.py --check    구조만 검사하고 파일은 만들지 않는다

게시는 사람이 한다 — 세션에서 Artifact 도구로 `dist/lab-dashboard.html`을 올린다.
주소는 고정이며 같은 파일을 다시 올리면 같은 주소가 갱신된다.
"""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace"); _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import os, re, sys, base64, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "source.html")
FONT = os.path.join(HERE, "assets", "Pretendard.woff2")
DIST = os.path.join(HERE, "dist", "lab-dashboard.html")

VOID = {"br", "link", "meta", "img", "hr", "input", "path", "rect", "line",
        "circle", "ellipse", "use", "polygon", "stop", "polyline", "i"}


def check(html):
    """게시 전 최소 검사 — 닫히지 않은 태그와 깨진 JS는 눈으로 안 잡힌다."""
    problems = []
    body = html.split("</style>", 1)[1] if "</style>" in html else html
    body = body.split("<script>")[0]
    stack, bad = [], []
    for m in re.finditer(r"<(/?)([a-zA-Z][\w-]*)([^>]*?)(/?)>", body):
        cl, tag, _, self_close = m.groups()
        tag = tag.lower()
        if tag in VOID or self_close == "/":
            continue
        if cl:
            if not stack or stack[-1] != tag:
                bad.append(tag)
            else:
                stack.pop()
        else:
            stack.append(tag)
    if stack:
        problems.append("닫히지 않은 태그: " + ", ".join(stack[:5]))
    if bad:
        problems.append("짝이 안 맞는 닫는 태그: " + ", ".join(bad[:5]))
    for marker in ('id="view-main"', 'id="view-detail"', "const TEAMS", "const MATES"):
        if marker not in html:
            problems.append(f"필수 요소 없음: {marker}")
    if "[hidden]{display:none!important}" not in html:
        problems.append("[hidden] 규칙 없음 — 팀 상세 화면이 안 열린다")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    html = open(SRC, encoding="utf8").read()
    problems = check(html)
    if problems:
        for p in problems:
            print("  ✗", p)
        sys.exit("구조 검사 실패 — 게시하지 마라.")
    print("구조 검사 통과")
    if a.check:
        return

    if "@@FONT@@" not in html:
        sys.exit("source.html 에 @@FONT@@ 자리가 없다.")
    out = html.replace("@@FONT@@", base64.b64encode(open(FONT, "rb").read()).decode())
    os.makedirs(os.path.dirname(DIST), exist_ok=True)
    open(DIST, "w", encoding="utf8").write(out)
    print(f"{os.path.relpath(DIST, HERE)} · {len(out.encode()) / 1048576:.2f} MB")


if __name__ == "__main__":
    main()
