# -*- coding: utf-8 -*-
"""
FZCORE Studio - Safe 24/7 Cloud SMTP Dispatcher & Follow-Up Engine
Features:
- Subdomain round-robin load distribution.
- Humanized anti-spam pacing (45 to 80 seconds randomized jitter).
- Zero duplicate sends (persistent unified sent ledger).
- Strict Direct-Owner Follow-Ups (100% skips generic info@/contact@/booksy).
"""

import email
import json
import os
import random
import re
import smtplib
import ssl
import sys
import time
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from pathlib import Path

SMTP_HOST = "smtp.hostinger.com"
SMTP_PORT = 465

GENERIC_COMPANY_PREFIXES = {
    "info", "contact", "admin", "office", "support", "help", "sales",
    "service", "services", "inquiries", "inquiry", "hello", "team",
    "frontdesk", "billing", "reception", "receptionist", "mail", "general",
    "quotes", "quote", "estimates", "estimate", "booking", "bookings",
    "info.desk", "contactus", "customerservice", "customersupport", "helpdesk",
    "orders", "jobs", "careers", "press", "media", "marketing", "accounting",
    "dispatch", "studio", "studios", "exams", "exam", "intake", "leads",
    "notifications", "news", "legal", "law", "desk", "enquiries", "enquiry"
}

PLATFORM_DOMAINS = {
    "booksy.com", "yelp.com", "thumbtack.com", "angi.com", "houzz.com",
    "homeadvisor.com", "bark.com", "checkatrade.com", "trustpilot.com"
}


def is_generic_company_email(email_addr: str) -> bool:
    if not email_addr or "@" not in email_addr:
        return True
    email_clean = email_addr.strip().lower()
    parts = email_clean.split("@")
    if len(parts) != 2:
        return True
    prefix, domain = parts[0].strip(), parts[1].strip()

    if domain in PLATFORM_DOMAINS:
        return True

    if prefix in GENERIC_COMPANY_PREFIXES:
        return True

    subparts = re.split(r"[._\-+]", prefix)
    for p in subparts:
        if p in GENERIC_COMPANY_PREFIXES:
            return True

    for g in GENERIC_COMPANY_PREFIXES:
        if prefix.startswith(g):
            return True

    return False


def dispatch_batch(mailboxes_file: Path, data_dir: Path, max_fresh: int = 4, max_followups: int = 3):
    default_pass = os.environ.get("SUBDOMAIN_MAIL_PASS")
    warren_pass = os.environ.get("WARREN_MAIL_PASS") or default_pass

    if not default_pass:
        print("[!] SUBDOMAIN_MAIL_PASS is not set. Cannot authenticate SMTP.")
        return 0, 0

    if not mailboxes_file.exists():
        print(f"[!] Mailboxes file not found at {mailboxes_file}")
        return 0, 0

    with open(mailboxes_file, "r", encoding="utf-8") as f:
        mailboxes = json.load(f)

    sent_ledger_file = data_dir / "sent_ledger.json"
    sent_ledger = {}
    if sent_ledger_file.exists():
        try:
            with open(sent_ledger_file, "r", encoding="utf-8") as lf:
                sent_ledger = json.load(lf)
        except Exception:
            sent_ledger = {}

    sent_emails = set()
    for v in sent_ledger.values():
        if isinstance(v, dict):
            em = v.get("recipient") or v.get("recipient_email") or v.get("email")
            if em:
                sent_emails.add(str(em).strip().lower())

    supp_file = data_dir / "suppression_list.json"
    suppressed = set()
    if supp_file.exists():
        try:
            with open(supp_file, "r", encoding="utf-8") as sf:
                suppressed = set(json.load(sf))
        except Exception:
            pass

    pitches_file = data_dir / "approved_pitches.json"
    if not pitches_file.exists():
        print("[!] approved_pitches.json not found in data directory.")
        return 0, 0

    with open(pitches_file, "r", encoding="utf-8") as pf:
        all_pitches = json.load(pf)

    # Filter uncontacted
    pending = []
    for p in all_pitches:
        em = (p.get("recipient_email") or p.get("decision_maker", {}).get("verified_email") or p.get("email") or "").strip().lower()
        dom = em.split("@")[-1] if "@" in em else ""
        if not em or em in sent_emails or em in suppressed or dom in suppressed:
            continue
        pending.append(p)

    print(f"[*] Dispatcher Queue: {len(pending)} uncontacted leads available in active vault.")

    fresh_sent = 0
    box_idx = random.randint(0, len(mailboxes) - 1)

    ctx = ssl.create_default_context()

    # 1. Fresh Pitches Dispatch
    for lead in pending:
        if fresh_sent >= max_fresh:
            break

        recipient_email = (lead.get("recipient_email") or lead.get("email") or "").strip().lower()
        recipient_name = lead.get("recipient_name", "Business Owner")
        business_name = lead.get("business_name", "your business")
        subject = lead.get("subject", "quick question")
        body_text = lead.get("body", "")
        lead_id = lead.get("lead_id", f"FZ-{int(time.time())}")

        if not recipient_email or not body_text:
            continue

        box = mailboxes[box_idx % len(mailboxes)]
        box_idx += 1
        sender_email = box["user"]
        sender_name = box.get("name", "Faiz Majeed")
        sender_title = box.get("title", "Founder & Principal")
        box_pass = warren_pass if sender_email == "warren@desk.fzcorestudio.com" else default_pass
        subdomain = sender_email.split("@")[-1]

        msg_id = make_msgid(domain=subdomain)
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{sender_name} <{sender_email}>"
        msg["To"] = f"{recipient_name} <{recipient_email}>"
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = msg_id

        sig_html = f"""<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 13px; color: #18181b; padding-top: 14px; margin-top: 14px; border-top: 1px solid #e5e7eb;"><strong>{sender_name}</strong><br><span style="color: #6b7280; font-size: 12px;">{sender_title} · FZCORE Studio</span><br><a href="https://fzcorestudio.com" style="color: #111827; text-decoration: none; font-weight: 600;">fzcorestudio.com</a></div>"""
        paras = "".join(f'<p style="margin: 0 0 14px 0; font-size: 14px; line-height: 1.55; color: #111827;">{p.replace(chr(10), "<br>")}</p>' for p in body_text.split("\n\n"))
        body_html = f"""<!DOCTYPE html><html><body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 14px; color: #111827;">{paras}<p style="margin: 0 0 4px 0; font-size: 14px; color: #111827;">Best,</p>{sig_html}</body></html>"""

        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        try:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx, timeout=15) as server:
                server.login(sender_email, box_pass)
                server.sendmail(sender_email, [recipient_email], msg.as_string())

            sent_ledger[lead_id] = {
                "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "recipient": recipient_email,
                "sender": sender_email,
                "sender_name": sender_name,
                "business": business_name,
                "subject": subject,
                "message_id": msg_id
            }
            sent_emails.add(recipient_email)
            fresh_sent += 1
            print(f"   ✅ [PITCH DELIVERED] To: {recipient_name} <{recipient_email}> ({business_name}) via {sender_email}")

            if fresh_sent < max_fresh:
                sleep_sec = random.uniform(50, 75)
                print(f"   ⏳ Pacing cooldown: {int(sleep_sec)}s before next send...")
                time.sleep(sleep_sec)

        except Exception as send_err:
            print(f"   ❌ Delivery Failed to {recipient_email}: {send_err}")
            if any(code in str(send_err) for code in ["550", "551", "552", "553", "554", "User unknown"]):
                suppressed.add(recipient_email)
                print(f"   🚨 Auto-quarantined dead recipient: {recipient_email}")
            time.sleep(10)

    # 2. Due Follow-Up #1 Bumps (Direct Named Owners Only)
    fu_sent = 0
    now = datetime.now()

    for lid, rec in list(sent_ledger.items()):
        if fu_sent >= max_followups:
            break

        if not isinstance(rec, dict) or rec.get("followup_sent"):
            continue

        target_email = rec.get("recipient", "").strip().lower()
        if not target_email or target_email in suppressed:
            continue

        if is_generic_company_email(target_email):
            continue

        sent_time_str = rec.get("sent_at", "")
        try:
            sent_dt = datetime.strptime(sent_time_str, "%Y-%m-%d %H:%M:%S")
            if (now - sent_dt) < timedelta(days=3):
                continue
        except Exception:
            continue

        sender_box = rec.get("sender", "")
        sender_name = rec.get("sender_name", "Faiz Majeed")
        orig_subject = rec.get("subject", "quick question")
        biz_name = rec.get("business", "your business")
        orig_mid = rec.get("message_id", "")
        box_pass = warren_pass if sender_box == "warren@desk.fzcorestudio.com" else default_pass

        fu_subject = f"Re: {orig_subject}" if not orig_subject.lower().startswith("re:") else orig_subject

        bump_plain = (
            f"Hey there,\n\n"
            f"Quick bump on this in case you were on a job when it came in.\n\n"
            f"Put together that quick 20-second preview of how the instant mobile package selector would look for {biz_name}.\n\n"
            f"Mind if I send the preview link over?\n\n"
            f"Best,\n"
            f"{sender_name}\n"
            f"FZCORE Studio | fzcorestudio.com\n"
        )
        sig_html = f"""<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 13px; color: #18181b; padding-top: 14px; margin-top: 14px; border-top: 1px solid #e5e7eb;"><strong>{sender_name}</strong><br><span style="color: #6b7280; font-size: 12px;">Founder · FZCORE Studio</span><br><a href="https://fzcorestudio.com" style="color: #111827; text-decoration: none; font-weight: 600;">fzcorestudio.com</a></div>"""
        bump_html = f"""<!DOCTYPE html><html><body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 14px; color: #111827;"><p>Hey there,</p><p>Quick bump on this in case you were on a job when it came in.</p><p>Put together that quick 20-second preview of how the instant mobile package selector would look for <strong>{biz_name}</strong>.</p><p>Mind if I send the preview link over?</p><p>Best,</p>{sig_html}</body></html>"""

        msg = MIMEMultipart("alternative")
        msg["Subject"] = fu_subject
        msg["From"] = f"{sender_name} <{sender_box}>"
        msg["To"] = target_email
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain="fzcorestudio.com")
        if orig_mid:
            msg["In-Reply-To"] = orig_mid
            msg["References"] = orig_mid

        msg.attach(MIMEText(bump_plain, "plain", "utf-8"))
        msg.attach(MIMEText(bump_html, "html", "utf-8"))

        try:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx, timeout=15) as server:
                server.login(sender_box, box_pass)
                server.sendmail(sender_box, [target_email], msg.as_string())

            rec["followup_sent"] = True
            rec["followup_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            fu_sent += 1
            print(f"   📬 [FOLLOW-UP #1 DELIVERED] To: {target_email} ({biz_name}) via {sender_box}")

            if fu_sent < max_followups:
                sleep_sec = random.uniform(50, 75)
                print(f"   ⏳ Follow-up pacing cooldown: {int(sleep_sec)}s...")
                time.sleep(sleep_sec)

        except Exception as fu_err:
            print(f"   ❌ Follow-up failed to {target_email}: {fu_err}")
            time.sleep(10)

    # Save state
    with open(sent_ledger_file, "w", encoding="utf-8") as lf:
        json.dump(sent_ledger, lf, indent=2)
    with open(supp_file, "w", encoding="utf-8") as sf:
        json.dump(sorted(list(suppressed)), sf, indent=2)

    print(f"[*] Dispatch Cycle Complete: {fresh_sent} fresh pitches + {fu_sent} follow-up bumps delivered.")
    return fresh_sent, fu_sent
