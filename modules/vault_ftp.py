# -*- coding: utf-8 -*-
"""
FZCORE Studio - Hostinger FTP Vault Synchronizer
Safely syncs approved pitches, sent ledgers, and suppression lists between
GitHub Actions cloud runners and Hostinger Private Cloud Storage.
"""

import ftplib
import io
import json
import os
import sys
from pathlib import Path

FTP_HOST = os.environ.get("FTP_SERVER", "82.197.83.123")
FTP_USER = os.environ.get("FTP_USERNAME", "u476907848")
REMOTE_DIR = "/domains/fzcorestudio.com/outbound_engine"


def get_ftp_connection():
    password = os.environ.get("FTP_PASSWORD")
    if not password:
        raise ValueError("CRITICAL: FTP_PASSWORD environment secret is not set!")

    ftp = ftplib.FTP(FTP_HOST, timeout=30)
    ftp.login(FTP_USER, password)
    ftp.set_pasv(True)
    return ftp


def download_vault_files(local_data_dir: Path):
    local_data_dir.mkdir(parents=True, exist_ok=True)
    ftp = get_ftp_connection()
    files_to_sync = [
        "approved_pitches.json",
        "sent_ledger.json",
        "suppression_list.json"
    ]

    downloaded = {}
    for filename in files_to_sync:
        remote_path = f"{REMOTE_DIR}/{filename}"
        bio = io.BytesIO()
        try:
            ftp.retrbinary(f"RETR {remote_path}", bio.write)
            bio.seek(0)
            data = json.loads(bio.read().decode("utf-8", errors="ignore"))
            local_file = local_data_dir / filename
            with open(local_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            downloaded[filename] = len(data) if isinstance(data, (list, dict)) else 0
            print(f"[FTP Sync] Downloaded {filename} ({downloaded[filename]} items)")
        except Exception as e:
            print(f"[FTP Sync] Warning on {filename}: {e}")
            local_file = local_data_dir / filename
            if not local_file.exists():
                fallback_data = [] if filename != "sent_ledger.json" else {}
                with open(local_file, "w", encoding="utf-8") as f:
                    json.dump(fallback_data, f, indent=2)

    ftp.quit()
    return downloaded


def upload_vault_file(local_file_path: Path, remote_filename: str):
    if not local_file_path.exists():
        print(f"[FTP Sync] File {local_file_path} does not exist, skipping upload.")
        return False

    ftp = get_ftp_connection()
    remote_path = f"{REMOTE_DIR}/{remote_filename}"
    try:
        with open(local_file_path, "rb") as f:
            ftp.storbinary(f"STOR {remote_path}", f)
        print(f"[FTP Sync] Successfully uploaded {remote_filename} to Hostinger Private Vault.")
        ftp.quit()
        return True
    except Exception as e:
        print(f"[FTP Sync] Error uploading {remote_filename}: {e}")
        try:
            ftp.quit()
        except Exception:
            pass
        return False
