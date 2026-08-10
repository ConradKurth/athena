#!/usr/bin/env python3
"""Render round-2 outreach emails from compliant templates + per-prospect personalization.

Inputs:
  - outreach/prospects.csv (for name/contact_name/email/segment of emailable round-2 rows)
  - .context/drafts/batch_<KEY>.json   (defines which template KEY each id belongs to)
  - .context/drafts/out_<KEY>.json      (personalization: [{id, opener, hook}])
Outputs:
  - outreach/drafts/round2-emails-2026-08-09.md   (human-reviewable, grouped)
  - outreach/drafts/round2-bodies/<id>.txt         (one plain-text body per email, for gmail-admin --body-file)
  - outreach/drafts/round2-send-manifest.csv       (id,email,subject,template,body_path)
Also runs a deterministic compliance scan over every rendered body and refuses to
emit a body that contains a banned claim term (prints offenders).
"""
import csv, json, glob, os, re, sys

ROOT = "/Users/conrad/conductor/workspaces/athena/port-au-prince"
os.chdir(ROOT)
DRAFTS = "outreach/drafts"
BODYDIR = f"{DRAFTS}/round2-bodies"
DATE = "2026-08-09"

SIG = "Thanks,\nConrad\nAthena UraGuard\nathenauraguard.com"

SUBJECT = {
    "A_creator":    "A dignity-first incontinence product for your community",
    "B_caregiver":  "A more comfortable option for the caregivers you reach",
    "P_podcast":    "Guest idea: incontinence, aging, and dignity",
    "E_publication":"A source + product for your incontinence & healthy-aging coverage",
    "C_community":  "A respectful partner idea for your community",
}

def body(key, cn, o, h):
    if key == "A_creator":
        return (f"Hi {cn},\n\n{o}\n\n"
                "I'm with Athena UraGuard. We make incontinence underwear and briefs, plus a thin liner "
                "that fits inside any of them for extra overnight dryness. It's physician-founded, built to "
                f"keep women dry and comfortable without the bulk. {h}\n\n"
                "If it fits your community, I'd love to send you a free set to try. No obligation, and I "
                "welcome an honest take. Can I mail you one?\n\n" + SIG)
    if key == "B_caregiver":
        return (f"Hi {cn},\n\n{o}\n\n"
                "I'm with Athena UraGuard. We make incontinence underwear and briefs, plus a thin liner that "
                "fits inside the brief someone already wears, for extra overnight dryness. It's "
                "physician-founded, and meant to make a hard part of caregiving a little easier. "
                f"{h}\n\n"
                "I'd be glad to send samples for you or the caregivers you reach. Would that help?\n\n" + SIG)
    if key == "P_podcast":
        return (f"Hi {cn},\n\n{o}\n\n"
                f"I run outreach for Athena UraGuard, a physician-founded incontinence brand. {h} I'd like to "
                "pitch a guest segment: our founder, or our medical author Dr. Jacqueline Krieger, MD, on "
                "managing incontinence with dignity, both for women in midlife and for families caring for "
                "aging parents. No product pitch, just a useful conversation.\n\n"
                "Worth a short call to see if it fits?\n\n" + SIG)
    if key == "E_publication":
        return (f"Hi {cn},\n\n{o}\n\n"
                "I run outreach for Athena UraGuard. Two things that might help your coverage. First, an "
                "expert source: our medical author Jacqueline Krieger, MD, can speak to incontinence, "
                "menopause, and healthy aging in women. Second, a product for roundups: a physician-founded "
                "incontinence line with a thin liner that sits inside any brief for extra overnight dryness. "
                f"{h}\n\n"
                "I can send samples or set up a source call, whenever suits your calendar.\n\n" + SIG)
    if key == "C_community":
        return (f"Hi {cn},\n\n{o}\n\n"
                "I'm with Athena UraGuard, a physician-founded incontinence line: underwear, briefs, and a "
                f"thin liner that fits inside any brief for extra overnight dryness. {h}\n\n"
                "I'd rather not drop a promo in the group. I'd like to partner with you properly, whether "
                "that's samples for members or a resource you can share. Who's the right person to talk to, "
                "and how do you prefer to work with brands?\n\n" + SIG)
    raise ValueError(key)

BANNED = re.compile(r"antibacter|antimicrob|bacteri|\b96\b|\bUTIs?\b|urinary|infection|\bprevents?\b|\bcures?\b|antiseptic|reduces? bacteria", re.I)

# Gate 2 (fail-closed): reject any em-dash, en-dash, or double-hyphen in a rendered body.
DASH = re.compile(r"[—–]|--")

# Gate 3 (advisory): WRITING.md AI-tell formula watchlist. Prints hits for manual review;
# does NOT block the render. Kept deliberately tight to the named formulas, not common words.
AITELL = re.compile("|".join([
    r"genuinely",
    r"real value",
    r"no[- ]shame",
    r"rare in this",
    r"rarely (?:talk|get|see|ment|rais|discuss)",
    r"the parts of this",
    r"\bnot just\b",
    r"\bnot only\b",
    r"\bisn't just\b",
    r"the kind of",
    r"the sort of",
    r"is exactly",
    r"exactly (?:the|what|why|who)",
    r"\btestament\b",
    r"showcas",
    r"underscore",
    r"serves as",
    r"stands as",
    r"one more",
    r"refreshingly",
    r"immediately (?:under|relev)",
    r"at the end of the day",
    r"when it comes to",
]), re.I)

def clean_name(cn):
    cn = re.sub(r"\s*\([^)]*\)", "", cn).strip().strip(",").strip()
    return cn or "there"

def clean_opener(o, cn):
    o = o.strip()
    o = re.sub(r"^(hi|hello|hey)\b[^,\n—-]*[,—-]\s*", "", o, flags=re.I)  # drop leading "Hi X,"
    if cn and cn != "there":
        o = re.sub(r"^" + re.escape(cn) + r"\s*[—,:-]\s*", "", o)               # drop leading full name
        first = cn.split()[0]
        o = re.sub(r"^" + re.escape(first) + r"\s*[—,:-]\s*", "", o)             # drop leading first name
    return (o[:1].upper() + o[1:]) if o else o

def main():
    # id -> template key (from which batch file it's in)
    id2key = {}
    for f in glob.glob(".context/drafts/batch_*.json"):
        key = os.path.basename(f)[len("batch_"):-len(".json")]
        for r in json.load(open(f)):
            id2key[r["id"]] = key
    # personalization
    pers = {}
    for f in glob.glob(".context/drafts/out_*.json"):
        for r in json.load(open(f)):
            pers[r["id"]] = r
    # prospect fields
    prospects = {x["id"]: x for x in csv.DictReader(open("outreach/prospects.csv"))
                 if x["created_at"] == DATE and x["contact_email"].strip()}

    os.makedirs(BODYDIR, exist_ok=True)
    md = ["# Round-2 outreach emails — DRAFT (compliant / claim-free)", "",
          f"Generated {DATE}. Sender: conrad@athenauraguard.com. **Not sent.** Review, then push to Gmail drafts.",
          "Claims: dryness / dignity / form-factor / physician-founded only — no antibacterial / UTI / 96%.", ""]
    manifest = []
    offenders, dash_offenders, aitell_hits, missing = [], [], [], []
    by_key = {}
    for pid, x in prospects.items():
        key = id2key.get(pid)
        p = pers.get(pid)
        if not key or not p or not p.get("opener"):
            missing.append(pid); continue
        # Greet a real person only. With no contact_name (or a role placeholder),
        # fall back to "there" rather than greeting the org/publication by name.
        raw_cn = x["contact_name"].strip()
        cn = clean_name(raw_cn) if raw_cn else "there"
        if cn.lower() in {"editor", "editors", "editorial", "team", "admin", "the editor", "staff"}:
            cn = "there"
        o = clean_opener(p["opener"].strip(), cn)
        b = body(key, cn, o, p["hook"].strip())
        hit = BANNED.search(b)
        if hit:
            offenders.append((pid, hit.group(0))); continue
        dhit = DASH.search(b)
        if dhit:
            dash_offenders.append((pid, repr(dhit.group(0)))); continue
        for m in AITELL.finditer(b):
            aitell_hits.append((pid, m.group(0)))
        subj = SUBJECT[key]
        open(f"{BODYDIR}/{pid}.txt", "w").write(b + "\n")
        manifest.append({"id": pid, "email": x["contact_email"].strip(),
                         "subject": subj, "template": key, "body_path": f"{BODYDIR}/{pid}.txt"})
        by_key.setdefault(key, []).append((x, subj, b))

    for key in ["A_creator", "B_caregiver", "P_podcast", "E_publication", "C_community"]:
        items = by_key.get(key, [])
        if not items: continue
        md.append(f"\n## {key}  ({len(items)})\n")
        for x, subj, b in items:
            md.append(f"### {x['name']}  ·  `{x['contact_email']}`  ·  {x['priority']}")
            md.append(f"**Subject:** {subj}\n")
            md.append("```\n" + b + "\n```\n")

    open(f"{DRAFTS}/round2-emails-{DATE}.md", "w").write("\n".join(md) + "\n")
    with open(f"{DRAFTS}/round2-send-manifest.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "email", "subject", "template", "body_path"])
        w.writeheader(); w.writerows(manifest)

    print(f"rendered {len(manifest)} emails -> {DRAFTS}/round2-emails-{DATE}.md")
    print(f"  bodies: {BODYDIR}/  manifest: {DRAFTS}/round2-send-manifest.csv")
    if missing: print(f"  MISSING personalization ({len(missing)}):", missing[:10])

    # Gate 1: compliance
    if offenders:
        print(f"  !! COMPLIANCE HITS ({len(offenders)}) - NOT rendered:")
        for pid, term in offenders: print(f"     {pid}: '{term}'")
    else:
        print("  gate 1 compliance: clean (0 banned terms in rendered bodies)")

    # Gate 3: AI-tell watchlist (advisory)
    if aitell_hits:
        print(f"  gate 3 AI-tell (advisory, {len(aitell_hits)} hit(s), review manually):")
        for pid, phrase in aitell_hits: print(f"     {pid}: '{phrase}'")
    else:
        print("  gate 3 AI-tell: clean (0 watchlist phrases)")

    # Gate 2: dash scan (fail-closed) - reported last so it is the final line before abort
    if dash_offenders:
        print(f"  !! gate 2 DASH HITS ({len(dash_offenders)}) - NOT rendered, refusing:")
        for pid, ch in dash_offenders: print(f"     {pid}: {ch}")
        sys.exit(1)
    print("  gate 2 dash scan: clean (0 em/en/double-dash in rendered bodies)")

if __name__ == "__main__":
    main()
