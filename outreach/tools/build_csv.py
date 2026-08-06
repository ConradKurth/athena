#!/usr/bin/env python3
"""Convert discovery raw JSON -> prospects.csv (append), contacts.md rows, and a discovery report.

Usage: python3 build_csv.py <raw.json> <outreach_dir> <date YYYY-MM-DD>
raw.json = {"prospects":[...]} or a bare list.
Deterministic: slug ids, proper CSV escaping (csv module), blank-fill, stage/date stamps.
Idempotent-ish: rewrites prospects.csv from header each run (source of truth = raw.json).
"""
import csv, json, re, sys, os
from collections import Counter

COLS = ["id","name","segment","platform","url","handle","audience_size","location",
        "contact_name","role","contact_email","contact_method","outreach_type",
        "pitch_angle","stage","priority","source","source_detail","notes",
        "created_at","last_updated"]

def slug(s):
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return s[:60] or "prospect"

def main():
    raw_path, odir, date = sys.argv[1], sys.argv[2], sys.argv[3]
    data = json.load(open(raw_path))
    rows = data.get("prospects", data) if isinstance(data, dict) else data

    used = set()
    out = []
    for p in rows:
        if not isinstance(p, dict):
            continue
        name = (p.get("name") or "").strip()
        url = (p.get("url") or "").strip()
        if not name or not url:
            continue
        seg = (p.get("segment") or "").strip()
        base = slug(name) + ("-" + seg.split("-")[-1] if seg else "")
        pid = base
        i = 2
        while pid in used:
            pid = f"{base}-{i}"; i += 1
        used.add(pid)
        r = {c: "" for c in COLS}
        r.update({
            "id": pid, "name": name, "segment": seg,
            "platform": (p.get("platform") or "").strip(),
            "url": url, "handle": (p.get("handle") or "").strip(),
            "audience_size": (p.get("audience_size") or "").strip(),
            "location": (p.get("location") or "").strip(),
            "contact_name": (p.get("contact_name") or "").strip(),
            "role": (p.get("role") or "").strip(),
            "contact_email": (p.get("contact_email") or "").strip(),
            "contact_method": (p.get("contact_method") or "research-needed").strip(),
            "outreach_type": (p.get("outreach_type") or "").strip(),
            "pitch_angle": (p.get("pitch_angle") or "").strip(),
            "stage": "prospecting",
            "priority": (p.get("priority") or "P3").strip(),
            "source": (p.get("source") or "manual").strip(),
            "source_detail": (p.get("source_detail") or "").strip(),
            "notes": (p.get("notes") or "").strip(),
            "created_at": date, "last_updated": date,
        })
        out.append(r)

    # write prospects.csv
    with open(os.path.join(odir, "prospects.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(out)

    # contacts.md provenance table (append rows under existing header)
    prov = []
    for r in out:
        contact = r["contact_email"] or r["handle"] or r["url"]
        prov.append(f"| {r['id']} | {contact} | {r['contact_method']} | {r['source']} | {date} |")
    cpath = os.path.join(odir, "contacts.md")
    with open(cpath, "a") as f:
        f.write("\n".join(prov) + "\n")

    # report
    by_type = Counter(r["outreach_type"] for r in out)
    by_seg = Counter(r["segment"] for r in out)
    by_pri = Counter(r["priority"] for r in out)
    with_email = sum(1 for r in out if r["contact_email"])
    rep = [f"# Discovery report — {date}", "",
           f"**Total prospects:** {len(out)}",
           f"**By type:** awareness={by_type.get('awareness',0)} · b2b={by_type.get('b2b',0)}",
           f"**With a direct email:** {with_email} / {len(out)}",
           f"**By priority:** " + " · ".join(f"{k}={by_pri.get(k,0)}" for k in ['P0','P1','P2','P3']),
           "", "## By segment", ""]
    for s, n in by_seg.most_common():
        rep.append(f"- {s}: {n}")
    with open(os.path.join(odir, "reports", f"discovery-{date}.md"), "w") as f:
        f.write("\n".join(rep) + "\n")

    print(f"wrote {len(out)} rows | awareness={by_type.get('awareness',0)} b2b={by_type.get('b2b',0)} | emails={with_email} | P0={by_pri.get('P0',0)} P1={by_pri.get('P1',0)} P2={by_pri.get('P2',0)} P3={by_pri.get('P3',0)}")

if __name__ == "__main__":
    main()
