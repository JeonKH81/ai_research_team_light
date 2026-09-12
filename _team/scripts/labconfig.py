#!/usr/bin/env python3
"""연구실 설정(`_team/lab.yaml`)을 읽는다. 다른 도구들이 전부 이것을 거친다.

    python3 labconfig.py --meeting-due  # 오늘이 랩미팅 준비를 돌릴 날이면 exit 0, 아니면 1
    python3 labconfig.py --next-meeting # 다음 랩미팅 날짜(YYYY-MM-DD) 한 줄. 없으면 빈 줄

파일이 없거나 항목이 빠져 있으면 기본값으로 채운다 — 설정 없이도 돈다.
"""
import os, sys, datetime

TEAM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(TEAM, "lab.yaml")

PLANETS = [("Mercury", "수성"), ("Venus", "금성"), ("Terra", "지구"), ("Mars", "화성"),
           ("Jupiter", "목성"), ("Saturn", "토성"), ("Uranus", "천왕성"), ("Neptune", "해왕성"),
           ("Ceres", "세레스"), ("Pluto", "명왕성")]

DEFAULTS = {
    "lab_name": "AI Research Team",
    "pi": {"field": "", "institution": "", "contact_email": ""},
    "teams": {"scheme": "planets", "names": [{"name": n, "ko": k} for n, k in PLANETS]},
    "schedule": {
        "lab_meeting": {"enabled": True, "weekday": 1, "time": "07:00",
                        "interval_weeks": 1, "anchor": "2026-09-01"},
    },
    "ideation": {"enabled": True, "topics": []},
}


def _merge(base, over):
    if not isinstance(over, dict):
        return base
    out = dict(base)
    for k, v in over.items():
        out[k] = _merge(base[k], v) if isinstance(base.get(k), dict) and isinstance(v, dict) else v
    return out


def load():
    cfg = DEFAULTS
    try:
        import yaml
        with open(PATH, encoding="utf8") as f:
            cfg = _merge(DEFAULTS, yaml.safe_load(f) or {})
    except Exception:
        pass
    # 팀은 언제나 10개. 모자라면 행성으로 채우고 넘치면 자른다
    names = [x for x in (cfg["teams"].get("names") or []) if isinstance(x, dict) and x.get("name")]
    if cfg["teams"].get("scheme", "planets") == "planets" or not names:
        names = [{"name": n, "ko": k} for n, k in PLANETS]
    for i, (n, k) in enumerate(PLANETS):
        if i >= len(names):
            names.append({"name": n, "ko": k})
    cfg["teams"]["names"] = [{"name": str(x["name"]).strip(), "ko": str(x.get("ko") or x["name"]).strip()}
                             for x in names[:10]]
    return cfg


def hm(s, default):
    try:
        h, m = str(s).split(":")
        return int(h), int(m)
    except Exception:
        return default


def meeting_day(cfg, d):
    """d 가 회의 주의 회의 요일인가. 간격이 2주 이상이면 기준일과 같은 주기에 드는 주만 참."""
    m = cfg["schedule"]["lab_meeting"]
    if not m.get("enabled", True):
        return False
    if d.weekday() != int(m.get("weekday", 1)):
        return False
    n = max(1, int(m.get("interval_weeks", 1) or 1))
    if n == 1:
        return True
    try:
        a = datetime.date.fromisoformat(str(m.get("anchor")))
    except Exception:
        return True
    week = lambda x: (x - datetime.timedelta(days=x.weekday()))
    return ((week(d) - week(a)).days // 7) % n == 0


def next_meeting(cfg, now=None):
    now = now or datetime.datetime.now()
    m = cfg["schedule"]["lab_meeting"]
    if not m.get("enabled", True):
        return None
    hh, mm = hm(m.get("time"), (7, 0))
    d = now.date()
    for i in range(0, 8 * max(1, int(m.get("interval_weeks", 1) or 1))):
        c = d + datetime.timedelta(days=i)
        if meeting_day(cfg, c) and not (i == 0 and (now.hour, now.minute) >= (hh, mm)):
            return c
    return None


def main():
    cfg = load()
    if "--meeting-due" in sys.argv:
        sys.exit(0 if meeting_day(cfg, datetime.date.today()) else 1)
    if "--next-meeting" in sys.argv:
        n = next_meeting(cfg)
        print(n.isoformat() if n else "")
        return
    import json
    print(json.dumps(cfg, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
