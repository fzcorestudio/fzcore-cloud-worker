# -*- coding: utf-8 -*-
"""
FZCORE Studio - 24/7 Autonomous Cloud Engine Orchestrator
Master Entrypoint executed by GitHub Actions Cloud Runner on schedule.
Calibrated for 1,000 Emails / 24 Hours with Subdomain Interleaving.
"""

import os
import sys
import time
from pathlib import Path

# Ensure modules in path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from modules.vault_ftp import download_vault_files, upload_vault_file
from modules.inbox_monitor import scan_all_mailboxes
from modules.safe_dispatcher import dispatch_batch
from modules.maps_harvester import harvest_fresh_leads

DATA_DIR = BASE_DIR / "data"
MAILBOXES_FILE = DATA_DIR / "mailboxes.json"


def main():
    start_time = time.time()
    print("=" * 75)
    print("🚀 [FZCORE 24/7 CLOUD WORKER] Starting Autonomous Cycle (1,000 Emails / Day Target)")
    print(f"⏰ Cloud Runner Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print("=" * 75)

    # 1. Sync Latest State from Hostinger Private FTP Vault
    print("\n[Step 1/5] Syncing latest state from Hostinger Vault...")
    try:
        download_vault_files(DATA_DIR)
    except Exception as e:
        print(f"⚠️ Vault download warning: {e}")

    # 2. Monitor Fleet Inboxes & Forward Real Human Client Replies
    print("\n[Step 2/5] Scanning 50 Fleet Mailboxes for Inbound Replies & Bounces...")
    try:
        new_replies, new_bounces = scan_all_mailboxes(MAILBOXES_FILE, DATA_DIR)
        print(f"   -> Results: {new_replies} human replies forwarded | {new_bounces} bounces quarantined.")
    except Exception as e:
        print(f"⚠️ Inbox monitor error: {e}")

    # 3. Safe Outbound Dispatch (18 Fresh Pitches + 7 Direct-Owner Follow-Ups = 25 / cycle -> 1,200 / 24 hr)
    print("\n[Step 3/5] Dispatching Safe Outbound Pitches (18 Fresh + 7 Follow-Ups = 25 / cycle | 1,200 / 24 hr)...")
    try:
        fresh_sent, fu_sent = dispatch_batch(MAILBOXES_FILE, DATA_DIR, max_fresh=18, max_followups=7)
        print(f"   -> Results: {fresh_sent} fresh pitches + {fu_sent} follow-ups delivered.")
    except Exception as e:
        print(f"⚠️ Dispatch error: {e}")

    # 4. Continuous Playwright Maps Harvester (20 fresh verified leads / cycle)
    print("\n[Step 4/5] Harvesting Fresh Rank #20-#100 Leads via Headless Playwright (Target: 20)...")
    try:
        harvested_count = harvest_fresh_leads(DATA_DIR, target_count=20)
        print(f"   -> Results: {harvested_count} fresh qualified leads secured & added to queue.")
    except Exception as e:
        print(f"⚠️ Harvester error: {e}")

    # 5. Sync Updated State Back to Hostinger Private Vault
    print("\n[Step 5/5] Uploading updated databases back to Hostinger Vault...")
    for fn in ["approved_pitches.json", "sent_ledger.json", "suppression_list.json"]:
        local_fp = DATA_DIR / fn
        if local_fp.exists():
            upload_vault_file(local_fp, fn)

    elapsed = int(time.time() - start_time)
    print("\n" + "=" * 75)
    print(f"🏁 [CYCLE COMPLETE] Completed in {elapsed}s ({elapsed // 60}m {elapsed % 60}s). Cloud runner safely exiting.")
    print("=" * 75)


if __name__ == "__main__":
    main()
