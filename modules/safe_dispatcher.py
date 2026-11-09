# -*- coding: utf-8 -*-
"""
FZCORE Studio - Safe 24/7 Cloud SMTP Dispatcher & Follow-Up Engine
Optimized for 1,000 Emails / 24 Hours with Subdomain Interleaving:
- Interleaved Subdomain Round-Robin (never hits the same subdomain twice consecutively).
- Automatic Subdomain Failover on 451 ratelimit.
- Direct Named Owners prioritized at the top of the queue.
- Follow-ups strictly restricted to Direct Named Owners (zero generic inboxes).
- 45 to 65 seconds randomized human anti-spam pacing.
"""

from collections import defaultdict
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


def build_interleaved_mailbox_pool(mailboxes):
    """Interleaves mailboxes across different subdomains so no consecutive sends hit the same subdomain."""
    subdom_map = defaultdict(list)
    for b in mailboxes:
        u = b["user"]
        dom = u.split("@")[-1]
        subdom_map[dom].append(b)

    interleaved = []
    max_len = max(len(v) for v in subdom_map.values()) if subdom_map else 0
    subdom_keys = list(subdom_map.keys())
    random.shuffle(subdom_keys)

    for i in range(max_len):
        for k in subdom_keys:
            if i < len(subdom_map[k]):
                interleaved.append(subdom_map[k][i])

    return interleaved


def dispatch_batch(mailboxes_file: Path, data_dir: Path, max_fresh: int = 14, max_followups: int = 7):
    default_pass = os.environ.get("SUBDOMAIN_MAIL_PASS")
    warren_pass = os.environ.get("WARREN_MAIL_PASS") or default_pass

    if not default_pass:
        print("[!] SUBDOMAIN_MAIL_PASS is not set. Cannot authenticate SMTP.")
        return 0, 0

    if not mailboxes_file.exists():
        print(f"[!] Mailboxes file not found at {mailboxes_file}")
        return 0, 0

    with open(mailboxes_file, "r", encoding="utf-8") as f:
        raw_mailboxes = json.load(f)

    # Interleave mailboxes across all 10 subdomains
    mailbox_pool = build_interleaved_mailbox_pool(raw_mailboxes)

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

    # Prioritize Direct Named Owners first (Tier A)
    pending.sort(key=lambda x: (1 if x.get("recipient_name") in ["Owner", "Business Owner", "Founder"] else 0))

    direct_count = sum(1 for p in pending if p.get("recipient_name") not in ["Owner", "Business Owner", "Founder"])
    print(f"[*] Dispatcher Queue: {len(pending)} uncontacted leads available ({direct_count} Direct Named Owners prioritized first).")

    fresh_sent = 0
    pool_idx = random.randint(0, len(mailbox_pool) - 1)
    cooling_subdomains = set()

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

        # Find next available mailbox from a non-cooling subdomain
        chosen_box = None
        for _ in range(len(mailbox_pool)):
            candidate_box = mailbox_pool[pool_idx % len(mailbox_pool)]
            pool_idx += 1
            cand_subdom = candidate_box["user"].split("@")[-1]
            if cand_subdom not in cooling_subdomains:
                chosen_box = candidate_box
                break

        if not chosen_box:
            print("[!] All active subdomains are currently cooling down. Pausing batch.")
            break

        sender_email = chosen_box["user"]
        sender_name = chosen_box.get("name", "Faiz Majeed")
        sender_title = chosen_box.get("title", "Founder & Principal")
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

        delivery_ok = False
        for attempt in range(1, 3):
            try:
                with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx, timeout=15) as server:
                    server.login(sender_email, box_pass)
                    server.sendmail(sender_email, [recipient_email], msg.as_string())
                delivery_ok = True
                break
            except Exception as send_err:
                err_str = str(send_err)
                if "451" in err_str and "hostinger_out_ratelimit" in err_str:
                    cooling_subdomains.add(subdomain)
                    print(f"   ⚠️ Subdomain {subdomain} hit temporary hourly ratelimit. Cooling down for this cycle.")
                    break
                elif any(code in err_str for code in ["550", "551", "552", "553", "554", "User unknown"]):
                    suppressed.add(recipient_email)
                    print(f"   🚨 Auto-quarantined dead recipient: {recipient_email}")
                    break
                else:
                    if attempt < 2:
                        time.sleep(3)

        if delivery_ok:
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
            print(f"   ✅ [PITCH {fresh_sent}/{max_fresh}] To: {recipient_name} <{recipient_email}> ({business_name}) via {sender_email}")

            if fresh_sent < max_fresh:
                sleep_sec = random.uniform(45, 65)
                print(f"   ⏳ Anti-Spam Pacing: Cooling down for {int(sleep_sec)}s before next send...")
                time.sleep(sleep_sec)

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
        fu_subdom = sender_box.split("@")[-1]

        if fu_subdom in cooling_subdomains:
            continue

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
            print(f"   📬 [FOLLOW-UP {fu_sent}/{max_followups}] To: {target_email} ({biz_name}) via {sender_box}")

            if fu_sent < max_followups:
                sleep_sec = random.uniform(45, 65)
                print(f"   ⏳ Follow-up pacing: Cooling down for {int(sleep_sec)}s...")
                time.sleep(sleep_sec)

        except Exception as fu_err:
            err_fu = str(fu_err)
            if "451" in err_fu and "hostinger_out_ratelimit" in err_fu:
                cooling_subdomains.add(fu_subdom)
            elif any(code in err_fu for code in ["550", "551", "552", "553", "554", "User unknown"]):
                suppressed.add(target_email)
            print(f"   ❌ Follow-up note on {target_email}: {fu_err}")

    # Save state
    with open(sent_ledger_file, "w", encoding="utf-8") as lf:
        json.dump(sent_ledger, lf, indent=2)
    with open(supp_file, "w", encoding="utf-8") as sf:
        json.dump(sorted(list(suppressed)), sf, indent=2)

    print(f"[*] Dispatch Cycle Complete: {fresh_sent} fresh pitches + {fu_sent} follow-up bumps delivered.")
    return fresh_sent, fu_sent
