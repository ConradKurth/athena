#!/usr/bin/env python3
"""Append round-N discovery JSON to prospects.csv WITHOUT clobbering existing rows.

Unlike build_csv.py (which rewrites prospects.csv from header each run), this
APPENDS new rows and dedups them against what's already in the CSV, on
normalized url / handle / name. Idempotent-ish: re-running with the same raw.json
adds nothing (all rows dedup out).

Usage: python3 append_prospects.py <raw.json> <outreach_dir> <date YYYY-MM-DD>
raw.json = {"prospects":[...]} or a bare list.
"""
import csv, json, re, sys, os
from collections import Counter

# Mirror build_csv.py's schema + slug so the two tools stay row-compatible.
COLS = ["id","name","segment","platform","url","handle","audience_size","location",
        "contact_name","role","contact_email","contact_method","outreach_type",
        "pitch_angle","stage","priority","source","source_detail","notes",
        "created_at","last_updated"]

def slug(s):
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return s[:60] or "prospect"

def norm_url(u):
    u = (u or "").strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    return u.rstrip("/")

def norm_handle(h):
    return (h or "").strip().lower().lstrip("@")

def norm_name(n):
    return re.sub(r"\s+", " ", (n or "").strip().lower())

def main():
    raw_path, odir, date = sys.argv[1], sys.argv[2], sys.argv[3]
    cpath = os.path.join(odir, "prospects.csv")

    existing_ids, e_urls, e_handles, e_names = set(), set(), set(), set()
    with open(cpath, newline="") as f:
        for r in csv.DictReader(f):
            existing_ids.add(r["id"])
            e_urls.add(norm_url(r["url"]))
            if r["handle"].strip():
                e_handles.add(norm_handle(r["handle"]))
            e_names.add(norm_name(r["name"]))

    data = json.load(open(raw_path))
    rows = data.get("prospects", data) if isinstance(data, dict) else data

    used_ids = set(existing_ids)
    added, skipped = [], []
    for p in rows:
        if not isinstance(p, dict):
            continue
        name = (p.get("name") or "").strip()
        url = (p.get("url") or "").strip()
        if not name or not url:
            skipped.append(("missing-name-or-url", name or url)); continue
        nu, nh, nn = norm_url(url), norm_handle(p.get("handle")), norm_name(name)
        if nu in e_urls or (nh and nh in e_handles) or nn in e_names:
            skipped.append(("dupe", name)); continue
        # accept — reserve its keys so later batch rows dedup against it too
        e_urls.add(nu); e_names.add(nn)
        if nh: e_handles.add(nh)

        seg = (p.get("segment") or "").strip()
        base = slug(name) + ("-" + seg.split("-")[-1] if seg else "")
        pid, i = base, 2
        while pid in used_ids:
            pid = f"{base}-{i}"; i += 1
        used_ids.add(pid)

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
            "outreach_type": (p.get("outreach_type") or "awareness").strip(),
            "pitch_angle": (p.get("pitch_angle") or "").strip(),
            "stage": "prospecting",
            "priority": (p.get("priority") or "P3").strip(),
            "source": (p.get("source") or "manual").strip(),
            "source_detail": (p.get("source_detail") or "").strip(),
            "notes": (p.get("notes") or "").strip(),
            "created_at": date, "last_updated": date,
        })
        added.append(r)

    # append rows (no header) — never rewrite the file
    with open(cpath, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writerows(added)

    # provenance rows appended to contacts.md
    with open(os.path.join(odir, "contacts.md"), "a") as f:
        for r in added:
            contact = r["contact_email"] or r["handle"] or r["url"]
            f.write(f"| {r['id']} | {contact} | {r['contact_method']} | {r['source']} | {date} |\n")

    # discovery report for this round
    by_seg = Counter(r["segment"] for r in added)
    by_pri = Counter(r["priority"] for r in added)
    wedge = Counter("uti" if "wedge=uti" in r["notes"].lower() else "compliant" for r in added)
    with_email = sum(1 for r in added if r["contact_email"])
    rep = [f"# Discovery report (append) — {date}", "",
           f"**Added:** {len(added)}  ·  **Skipped (dupe/invalid):** {len(skipped)}",
           f"**With a direct email:** {with_email} / {len(added)}",
           f"**Wedge tag:** compliant={wedge.get('compliant',0)} · uti={wedge.get('uti',0)}",
           f"**By priority:** " + " · ".join(f"{k}={by_pri.get(k,0)}" for k in ['P0','P1','P2','P3']),
           "", "## By segment", ""]
    for s, n in by_seg.most_common():
        rep.append(f"- {s}: {n}")
    os.makedirs(os.path.join(odir, "reports"), exist_ok=True)
    with open(os.path.join(odir, "reports", f"discovery-{date}.md"), "w") as f:
        f.write("\n".join(rep) + "\n")

    print(f"added {len(added)} | skipped {len(skipped)} | emails {with_email} | "
          f"compliant={wedge.get('compliant',0)} uti={wedge.get('uti',0)} | "
          + " ".join(f"{k}={by_pri.get(k,0)}" for k in ['P0','P1','P2','P3']))
    if skipped:
        print("skipped sample:", skipped[:12])

if __name__ == "__main__":
    main()
