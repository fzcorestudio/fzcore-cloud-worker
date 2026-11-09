# -*- coding: utf-8 -*-
"""
FZCORE Studio - Automated 24/7 Cloud Inbox Monitor & Real Human Reply Forwarder
Rules:
1. NEVER auto-reply with an AI bot (preserves senior agency human trust).
2. Instant alert to FORWARD_TARGET_EMAIL (nmstationer@gmail.com) on every real prospect reply with Reply-To header.
3. Auto-quarantines delivery failures (bounces) and bot auto-responders into suppression_list.json.
"""

import email
from email.header import decode_header
import imaplib
import json
import os
import re
import smtplib
import ssl
import sys
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid, parseaddr
from pathlib import Path

IMAP_HOST = "imap.hostinger.com"
SMTP_HOST = "smtp.hostinger.com"
SMTP_PORT = 465

BOT_SUBJECT_TRIGGERS = [
    "out of office", "automatic reply", "autoreply", "auto-reply", "away from office",
    "delivery status notification", "failure notice", "undeliverable", "mail delivery failed",
    "undelivered mail", "returned mail", "ticket created", "request received", "case #"
]

BOT_DOMAINS = {
    "zendesk.com", "freshdesk.com", "intuit.com", "booksy.com", "jobber.com",
    "housecallpro.com", "thumbtack.com", "angi.com", "yelp.com", "mailchannels.net"
}


def clean_header(val):
    if not val:
        return ""
    decoded_parts = decode_header(val)
    out = []
    for part, enc in decoded_parts:
        if isinstance(part, bytes):
            try:
                out.append(part.decode(enc or "utf-8", errors="ignore"))
            except Exception:
                out.append(part.decode("latin1", errors="ignore"))
        else:
            out.append(str(part))
    return "".join(out).strip()


def get_body_text(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdisp = str(part.get("Content-Disposition", ""))
            if ctype == "text/plain" and "attachment" not in cdisp:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body = payload.decode(charset, errors="ignore")
                        break
                except Exception:
                    pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                body = payload.decode(charset, errors="ignore")
        except Exception:
            pass
    return body.strip()


def forward_human_reply(prospect_name, prospect_email, received_in, subject, body_text, target_email, sender_box, sender_pass):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🔥 CLIENT REPLY: {prospect_name} ({prospect_email}) -> {received_in}"
        msg["From"] = f"FZCORE Leads <{sender_box}>"
        msg["To"] = target_email
        msg["Reply-To"] = prospect_email
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain="fzcorestudio.com")

        plain_text = f"""🔥 CLIENT REPLY RECEIVED!

Prospect: {prospect_name} <{prospect_email}>
Received in Fleet Box: {received_in}
Subject: {subject}

-------------------- CLIENT MESSAGE --------------------
{body_text}
--------------------------------------------------------

👉 Tap 'Reply' in your email client to respond directly to {prospect_email}!
"""
        paras = "".join(f"<p style='margin:0 0 12px 0;'>{p.replace(chr(10), '<br>')}</p>" for p in body_text.split("\n\n")) if body_text else "<p>No body text</p>"
        html_text = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 20px; color: #111827; background: #f9fafb;">
  <div style="max-width: 650px; margin: 0 auto; background: #ffffff; border-radius: 8px; border: 1px solid #e5e7eb; padding: 24px;">
    <div style="border-bottom: 2px solid #10b981; padding-bottom: 12px; margin-bottom: 16px;">
      <span style="font-size: 11px; font-weight: 700; color: #059669; text-transform: uppercase; letter-spacing: 0.05em;">Hot Inbound Lead</span>
      <h2 style="margin: 4px 0 0 0; font-size: 18px; color: #111827;">Reply from {prospect_name}</h2>
    </div>
    <table style="width: 100%; font-size: 13px; margin-bottom: 20px; color: #4b5563;">
      <tr><td style="font-weight: 600; width: 110px;">Prospect:</td><td>{prospect_name} &lt;<a href="mailto:{prospect_email}">{prospect_email}</a>&gt;</td></tr>
      <tr><td style="font-weight: 600;">Fleet Mailbox:</td><td>{received_in}</td></tr>
      <tr><td style="font-weight: 600;">Subject:</td><td>{subject}</td></tr>
    </table>
    <div style="background: #f3f4f6; border-left: 4px solid #3b82f6; padding: 16px; border-radius: 4px; font-size: 14px; line-height: 1.6; color: #1f2937;">
      {paras}
    </div>
    <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid #e5e7eb; font-size: 13px; color: #6b7280;">
      Hit <strong>Reply</strong> to respond directly to <strong>{prospect_email}</strong>.
    </div>
  </div>
</body>
</html>"""

        msg.attach(MIMEText(plain_text, "plain", "utf-8"))
        msg.attach(MIMEText(html_text, "html", "utf-8"))

        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx, timeout=15) as s:
            s.login(sender_box, sender_pass)
            s.sendmail(sender_box, [target_email], msg.as_string())
        print(f"   🚀 FORWARDED lead reply from {prospect_email} to {target_email} successfully!")
        return True
    except Exception as e:
        print(f"   ❌ Error forwarding reply from {prospect_email}: {e}")
        return False


def scan_all_mailboxes(mailboxes_file: Path, data_dir: Path):
    target_email = os.environ.get("FORWARD_TARGET_EMAIL", "nmstationer@gmail.com")
    default_pass = os.environ.get("SUBDOMAIN_MAIL_PASS")
    warren_pass = os.environ.get("WARREN_MAIL_PASS") or default_pass

    if not default_pass:
        print("[!] SUBDOMAIN_MAIL_PASS is not set. Cannot authenticate IMAP.")
        return 0, 0

    if not mailboxes_file.exists():
        print(f"[!] Mailboxes file not found at {mailboxes_file}")
        return 0, 0

    with open(mailboxes_file, "r", encoding="utf-8") as f:
        boxes = json.load(f)

    supp_file = data_dir / "suppression_list.json"
    suppressed = set()
    if supp_file.exists():
        try:
            with open(supp_file, "r", encoding="utf-8") as sf:
                suppressed = set(json.load(sf))
        except Exception:
            pass

    seen_file = data_dir / "seen_incoming_mids.json"
    seen_mids = set()
    if seen_file.exists():
        try:
            with open(seen_file, "r", encoding="utf-8") as smf:
                seen_mids = set(json.load(smf))
        except Exception:
            pass

    replied_file = data_dir / "replied_leads.json"
    replied_leads = set()
    if replied_file.exists():
        try:
            with open(replied_file, "r", encoding="utf-8") as rf:
                replied_leads = set(json.load(rf))
        except Exception:
            pass

    new_bounces = 0
    new_human_replies = 0

    print(f"[*] Scanning {len(boxes)} fleet mailboxes for incoming replies & bounces...")

    for box in boxes:
        user_email = box["user"]
        box_pass = warren_pass if user_email == "warren@desk.fzcorestudio.com" else default_pass

        try:
            m = imaplib.IMAP4_SSL(IMAP_HOST, 993, timeout=10)
            m.login(user_email, box_pass)
            status, _ = m.select("INBOX", readonly=True)
            if status != "OK":
                m.logout()
                continue

            status, msg_nums = m.search(None, "ALL")
            if status != "OK" or not msg_nums[0]:
                m.logout()
                continue

            id_list = msg_nums[0].split()
            # Check last 15 messages in inbox
            for mid in id_list[-15:]:
                res, data = m.fetch(mid, "(RFC822.HEADER BODY.PEEK[])")
                if res != "OK" or not data or not data[0]:
                    continue

                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)

                msg_id = clean_header(msg.get("Message-ID", ""))
                if msg_id and msg_id in seen_mids:
                    continue

                from_hdr = clean_header(msg.get("From", ""))
                subject = clean_header(msg.get("Subject", ""))
                auto_sub = clean_header(msg.get("Auto-Submitted", "")).lower()

                parsed_name, parsed_addr = parseaddr(from_hdr)
                sender_addr = parsed_addr.strip().lower()
                sender_dom = sender_addr.split("@")[-1] if "@" in sender_addr else ""

                if not sender_addr or sender_addr == user_email.lower():
                    continue

                # 1. Detection: Delivery Status Failure / Bounce
                is_bounce = False
                if any(b in subject.lower() for b in ["delivery status notification", "failure notice", "undeliverable", "mail delivery failed"]):
                    is_bounce = True
                if "mailer-daemon" in sender_addr or "postmaster" in sender_addr:
                    is_bounce = True

                if is_bounce:
                    body = get_body_text(msg)
                    # Extract original failed recipient
                    m_fail = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', body)
                    if m_fail:
                        failed_em = m_fail.group(1).lower().strip()
                        if failed_em != user_email.lower() and "@" in failed_em:
                            suppressed.add(failed_em)
                            new_bounces += 1
                            print(f"   🚨 Auto-Quarantined Bounce: {failed_em} (bounced to {user_email})")
                    if msg_id:
                        seen_mids.add(msg_id)
                    continue

                # 2. Detection: Automated Bot / Auto-Responder
                is_bot = False
                if auto_sub in ["auto-replied", "auto-generated"]:
                    is_bot = True
                if any(t in subject.lower() for t in BOT_SUBJECT_TRIGGERS):
                    is_bot = True
                if sender_dom in BOT_DOMAINS:
                    is_bot = True

                if is_bot:
                    suppressed.add(sender_addr)
                    if msg_id:
                        seen_mids.add(msg_id)
                    print(f"   🤖 Auto-Quarantined Bot: {sender_addr} ('{subject[:40]}')")
                    continue

                # 3. Detection: Verified Real Human Prospect Reply!
                body = get_body_text(msg)
                if len(body) > 10:
                    print(f"\n🌟 REAL HUMAN CLIENT REPLY DETECTED!")
                    print(f"   From:    {parsed_name} <{sender_addr}>")
                    print(f"   Box:     {user_email}")
                    print(f"   Subject: {subject}")

                    ok = forward_human_reply(
                        prospect_name=parsed_name or "Client",
                        prospect_email=sender_addr,
                        received_in=user_email,
                        subject=subject,
                        body_text=body,
                        target_email=target_email,
                        sender_box=user_email,
                        sender_pass=box_pass
                    )
                    if ok:
                        new_human_replies += 1
                        replied_leads.add(sender_addr)

                if msg_id:
                    seen_mids.add(msg_id)

            m.logout()
        except Exception as box_err:
            pass

    # Save state
    with open(supp_file, "w", encoding="utf-8") as sf:
        json.dump(sorted(list(suppressed)), sf, indent=2)
    with open(seen_file, "w", encoding="utf-8") as smf:
        json.dump(list(seen_mids), smf, indent=2)
    with open(replied_file, "w", encoding="utf-8") as rf:
        json.dump(sorted(list(replied_leads)), rf, indent=2)

    print(f"[*] Inbox Scan Complete. New Human Replies Forwarded: {new_human_replies} | New Bounces Quarantined: {new_bounces}")
    return new_human_replies, new_bounces
