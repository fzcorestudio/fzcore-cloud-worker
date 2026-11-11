# -*- coding: utf-8 -*-
"""
FZCORE Studio - Hostinger Vault Pitch Upgrader & Sanitizer
1. Downloads approved_pitches.json and sent_ledger.json from Hostinger FTP.
2. Removes non-contractor niches (lawyers, doctors, accountants, clinics).
3. Cleans recipient names (eliminates 'bwalker', 'admin', 'info', numbers).
4. Re-generates all contractor pitches using the 4 Top 1% Concrete Contractor Angles:
   - Angle 0: Missed-Call Ladder Reality (15s auto text bridge)
   - Angle 1: Dead Quotes & Dormant Estimates ($0 ad spend 2-text reactivation)
   - Angle 2: Tire-Kicker / Ghosted Bid 30s Filter (pre-qualifies before driving)
   - Angle 3: Exclusive Local Project Capacity (Dylan capacity model / Anti-Angi)
5. Enforces ZERO arbitrary price tags and ZERO em dashes.
6. Re-uploads the refreshed approved_pitches.json back to Hostinger FTP.
"""

import ftplib
import io
import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from modules.maps_harvester import clean_human_name, generate_pitch

FTP_HOST = "82.197.83.123"
FTP_USER = "u476907848"
FTP_PASS = "Faizmajeed@171385"

BAD_KEYWORDS = [
    "law", "legal", "attorney", "dentist", "dentistry", "chiro", "chiropract",
    "medspa", "tax", "accountant", "accounting", "clinic", "vet", "doctor",
    "hospital", "plastic surgery", "aesthetics clinic"
]


def run_migration():
    print("=" * 70)
    print("🚀 [VAULT MIGRATION] Starting Vault Pitch Sanitization & Upgrade")
    print("=" * 70)

    print("\n[1/4] Connecting to Hostinger FTP and downloading vault state...")
    ftp = ftplib.FTP(FTP_HOST, FTP_USER, FTP_PASS, timeout=15)
    
    bio_p = io.BytesIO()
    ftp.retrbinary("RETR domains/fzcorestudio.com/outbound_engine/approved_pitches.json", bio_p.write)
    
    bio_s = io.BytesIO()
    ftp.retrbinary("RETR domains/fzcorestudio.com/outbound_engine/sent_ledger.json", bio_s.write)
    
    bio_p.seek(0)
    pitches = json.loads(bio_p.read().decode("utf-8"))
    
    bio_s.seek(0)
    ledger = json.loads(bio_s.read().decode("utf-8"))

    sent_emails = set()
    for v in ledger.values():
        if isinstance(v, dict):
            em = v.get("recipient") or v.get("recipient_email") or v.get("email")
            if em:
                sent_emails.add(str(em).strip().lower())

    print(f"   -> Vault state: {len(pitches)} pitches in vault, {len(sent_emails)} sent in ledger.")

    print("\n[2/4] Sanitizing and regenerating pitches with 4 Top 1% Concrete Angles...")
    upgraded = []
    skipped_sent = 0
    skipped_bad_niche = 0
    em_dash_detected = 0

    for p in pitches:
        em = (p.get("recipient_email") or p.get("email") or "").strip().lower()
        if not em or em in sent_emails:
            skipped_sent += 1
            continue

        text_check = (p.get("business_name", "") + " " + p.get("category", "") + " " + p.get("domain", "")).lower()
        if any(b in text_check for b in BAD_KEYWORDS):
            skipped_bad_niche += 1
            continue

        raw_owner = p.get("recipient_name") or p.get("owner_name")
        clean_name = clean_human_name(raw_owner, em) or "Business Owner"
        p["recipient_name"] = clean_name
        p["owner_name"] = clean_name

        # Regenerate pitch with the new 4 angles
        subj, body = generate_pitch(p)
        if "\u2014" in subj or "\u2014" in body:
            em_dash_detected += 1
            subj = subj.replace("\u2014", " - ")
            body = body.replace("\u2014", " - ")

        p["subject"] = subj
        p["body"] = body

        upgraded.append(p)

    # Prioritize verified Direct Named Owners first
    upgraded.sort(key=lambda x: (1 if x.get("recipient_name") in ["Owner", "Business Owner", "Founder", "Team", None] else 0))
    named_count = sum(1 for p in upgraded if p.get("recipient_name") not in ["Owner", "Business Owner", "Founder", "Team", None])

    print(f"   -> Skipped already sent: {skipped_sent}")
    print(f"   -> Skipped non-contractor niches: {skipped_bad_niche}")
    print(f"   -> Upgraded legitimate contractor pitches ready: {len(upgraded)}")
    print(f"   -> Direct Named Owners prioritized first: {named_count}")
    print(f"   -> Em dashes caught and cleaned: {em_dash_detected}")

    # Inspect samples
    print("\n[3/4] Validating upgraded pitch samples:")
    for idx in [0, 50, 200, 400]:
        if idx < len(upgraded):
            s = upgraded[idx]
            print(f"\n--- Sample #{idx}: {s.get('business_name')} | Recipient: {s.get('recipient_name')} <{s.get('recipient_email')}> ---")
            print(f"Subject: {s.get('subject')}")
            print("Body:")
            for line in s.get("body", "").split("\n"):
                print(f"  {line}")

    print("\n[4/4] Uploading upgraded approved_pitches.json to Hostinger FTP...")
    out_bytes = json.dumps(upgraded, indent=2, ensure_ascii=False).encode("utf-8")
    bio_out = io.BytesIO(out_bytes)
    ftp.storbinary("STOR domains/fzcorestudio.com/outbound_engine/approved_pitches.json", bio_out)
    ftp.quit()

    # Also save local backup copy in data/
    local_data = BASE_DIR / "data"
    local_data.mkdir(parents=True, exist_ok=True)
    with open(local_data / "approved_pitches.json", "w", encoding="utf-8") as f:
        json.dump(upgraded, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print(f"🎉 [MIGRATION COMPLETE] Active Hostinger vault now has {len(upgraded)} pristine, high-converting contractor pitches.")
    print("=" * 70)


if __name__ == "__main__":
    run_migration()
