#!/usr/bin/env python3
"""Render the round-1b remaining-email awareness prospects.

These 18 rows were created in round 1 (created_at != the round-2 date) but never
had compliant email drafts made. This script reuses render_round2_emails.py's
templates, signature, subject map, and all three gates (compliance / dash /
AI-tell), but selects prospects by id membership in batch_round1b.json (NOT by
date) and writes round1b-* outputs so the round-2 manifest and its 75 staged
drafts are left untouched.

Inputs:
  .context/drafts/batch_round1b.json   { id: template_key }
  .context/drafts/out_round1b.json      [ {id, opener, hook} ]
Outputs:
  outreach/drafts/round1b-emails-<DATE>.md
  outreach/drafts/round1b-bodies/<id>.txt
  outreach/drafts/round1b-send-manifest.csv
"""
import csv, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_round2_emails as R  # noqa: E402  (reuse shared logic + gates)

os.chdir(R.ROOT)
DRAFTS = R.DRAFTS
# Parametric so the same renderer serves round1b (default) and round1c etc.
PREFIX = os.environ.get("R1B_PREFIX", "round1b")
BATCH_FILE = os.environ.get("R1B_BATCH", ".context/drafts/batch_round1b.json")
OUT_FILE = os.environ.get("R1B_OUT", ".context/drafts/out_round1b.json")
BODYDIR = f"{DRAFTS}/{PREFIX}-bodies"
DATE = R.DATE  # generation-date label only

def main():
    id2key = json.load(open(BATCH_FILE))
    pers = {r["id"]: r for r in json.load(open(OUT_FILE))}
    prospects = {x["id"]: x for x in csv.DictReader(open("outreach/prospects.csv"))
                 if x["id"] in id2key}

    os.makedirs(BODYDIR, exist_ok=True)
    manifest, offenders, dash_off, aitell, missing, by_key = [], [], [], [], [], {}
    for pid, key in id2key.items():
        x, p = prospects.get(pid), pers.get(pid)
        if not x or not p or not p.get("opener"):
            missing.append(pid); continue
        # email comes from prospects.csv, or (round1c) from the out-file where research found it
        email = (x.get("contact_email", "") or "").strip() or (p.get("email", "") or "").strip()
        if not email:
            missing.append(pid); continue
        raw = x["contact_name"].strip()
        cn = R.clean_name(raw) if raw else "there"
        # multi-name contact (e.g. "A / B / C" or "A & B") usually maps to a general
        # inbox / co-hosts -> greet generically rather than with a long name string
        if "/" in cn or "&" in cn:
            cn = "there"
        cn = cn.split(",")[0].strip() or "there"   # drop trailing credentials ("Rachel Rubin, MD")
        if cn.lower() in {"editor", "editors", "editorial", "team", "admin", "the editor", "staff"}:
            cn = "there"
        if p.get("greet"):                          # explicit override (e.g. org-name contact -> "there")
            cn = p["greet"]
        o = R.clean_opener(p["opener"].strip(), cn)
        b = R.body(key, cn, o, p["hook"].strip())
        hit = R.BANNED.search(b)
        if hit:
            offenders.append((pid, hit.group(0))); continue
        dhit = R.DASH.search(b)
        if dhit:
            dash_off.append((pid, repr(dhit.group(0)))); continue
        for m in R.AITELL.finditer(b):
            aitell.append((pid, m.group(0)))
        subj = R.SUBJECT[key]
        open(f"{BODYDIR}/{pid}.txt", "w").write(b + "\n")
        manifest.append({"id": pid, "email": email,
                         "subject": subj, "template": key, "body_path": f"{BODYDIR}/{pid}.txt"})
        by_key.setdefault(key, []).append((x, subj, b))

    md = [f"# {PREFIX} email drafts — {DATE} (compliant / claim-free)", "",
          "Compliant email drafts. **Not sent.** Review, then push.",
          "Claims: dryness / dignity / form-factor / physician-founded only.", ""]
    for key in ["A_creator", "B_caregiver", "P_podcast", "E_publication", "C_community"]:
        items = by_key.get(key, [])
        if not items:
            continue
        md.append(f"\n## {key}  ({len(items)})\n")
        for x, subj, b in items:
            md.append(f"### {x['name']}  ·  `{x['contact_email']}`  ·  {x['priority']}")
            md.append(f"**Subject:** {subj}\n")
            md.append("```\n" + b + "\n```\n")
    open(f"{DRAFTS}/{PREFIX}-emails-{DATE}.md", "w").write("\n".join(md) + "\n")
    with open(f"{DRAFTS}/{PREFIX}-send-manifest.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "email", "subject", "template", "body_path"])
        w.writeheader(); w.writerows(manifest)

    print(f"rendered {len(manifest)} {PREFIX} emails -> {DRAFTS}/{PREFIX}-send-manifest.csv")
    if missing:
        print(f"  MISSING personalization ({len(missing)}):", missing)
    print("  gate 1 compliance:", f"HITS {offenders}" if offenders else "clean")
    print("  gate 3 AI-tell:", f"{len(aitell)} advisory hit(s): {aitell}" if aitell else "clean")
    if dash_off:
        print(f"  !! gate 2 DASH HITS - refusing: {dash_off}")
        sys.exit(1)
    print("  gate 2 dash scan: clean")

if __name__ == "__main__":
    main()
