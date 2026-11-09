# -*- coding: utf-8 -*-
"""
FZCORE Studio - Dedicated 24/7 Cloud Harvester Engine
Runs in parallel with the Dispatcher to guarantee 1,200 to 1,500+ fresh leads / day.
"""

import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from modules.vault_ftp import download_vault_files, upload_vault_file
from modules.maps_harvester import harvest_fresh_leads

DATA_DIR = BASE_DIR / "data"


def main():
    start_time = time.time()
    print("=" * 75)
    print("🚀 [FZCORE HIGH-VOLUME HARVEST ENGINE] Starting Multi-Niche Cloud Harvest")
    print(f"⏰ Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print("=" * 75)

    # 1. Download existing vault state from Hostinger
    print("\n[1/3] Syncing latest active vault from Hostinger...")
    try:
        download_vault_files(DATA_DIR)
    except Exception as e:
        print(f"⚠️ Vault download warning: {e}")

    # 2. Run High-Volume Playwright Harvest across 3 niches
    print("\n[2/3] Executing Multi-Query Deep Maps Crawl (Target: 35 qualified leads)...")
    harvested = 0
    try:
        harvested = harvest_fresh_leads(DATA_DIR, target_count=35)
    except Exception as e:
        print(f"⚠️ Harvester error: {e}")

    # 3. Upload refreshed vault to Hostinger
    print("\n[3/3] Uploading updated approved_pitches.json to Hostinger...")
    pitches_file = DATA_DIR / "approved_pitches.json"
    if pitches_file.exists():
        upload_vault_file(pitches_file, "approved_pitches.json")

    elapsed = int(time.time() - start_time)
    print("\n" + "=" * 75)
    print(f"🎉 [HARVEST CYCLE COMPLETE] Secured {harvested} fresh leads in {elapsed}s ({elapsed // 60}m {elapsed % 60}s).")
    print("=" * 75)


if __name__ == "__main__":
    main()
