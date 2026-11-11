# -*- coding: utf-8 -*-
"""
FZCORE Studio - Autonomous High-Volume Google Maps Harvester (1,200 - 1,500+ Leads/Day)
Targets Rank #20 to #100 Mom-and-Pop Contractors (3 to 28 reviews).
Multi-query search (3 to 4 cities/niches per cycle) with deep 12x scroll.
Deep DOM flaw audit + Contact-page crawling + RFC DNS MX verification.
Generates senior-designer, flaw-calibrated pitches ready for dispatch.
"""

import json
import os
import random
import re
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright
from modules.vibe_auditor import audit_contractor_site, is_clean_deliverable_email

HIGH_TICKET_QUERIES = [
    # High-Ticket Roofing & Exterior Trades
    ("Roofing Contractor", "Atlanta GA"),
    ("Commercial Roofing Contractor", "Orlando FL"),
    ("Metal Roofing Contractor", "Austin TX"),
    ("Residential Roofing Services", "Fort Worth TX"),
    ("Roofing Contractor", "Denver CO"),
    ("Commercial Roofing Contractor", "Houston TX"),
    ("Metal Roofing Contractor", "Charlotte NC"),
    ("Roofing Contractor", "Dallas TX"),
    ("Roofing Contractor", "Phoenix AZ"),
    ("Roofing Contractor", "Tampa FL"),
    ("Roofing Contractor", "Calgary AB"),
    ("Roofing and Gutter Contractor", "Manchester UK"),

    # High-Value Remodeling & Custom Home Builders
    ("Kitchen and Bath Remodeling", "Dallas TX"),
    ("Custom Home Builder", "Houston TX"),
    ("Bathroom Remodeling Contractor", "Nashville TN"),
    ("Kitchen Renovation Specialist", "Minneapolis MN"),
    ("General Contractor Commercial", "Indianapolis IN"),
    ("Custom Home Builder", "Phoenix AZ"),
    ("Kitchen and Bath Remodeling", "Charlotte NC"),
    ("Custom Home Builder", "Austin TX"),
    ("Kitchen Renovation", "Toronto ON"),
    ("Custom Home Builder", "Vancouver BC"),

    # High-Margin Specialty Trades (Painting, HVAC, Plumbing, Electrical)
    ("Commercial Painting Contractor", "Atlanta GA"),
    ("Commercial Painting Contractor", "Dallas TX"),
    ("Commercial Painting Contractor", "Orlando FL"),
    ("Painting Contractor", "Sydney AU"),
    ("Commercial HVAC Contractor", "Jacksonville FL"),
    ("Commercial HVAC Contractor", "Phoenix AZ"),
    ("Plumbing and Drain Specialist", "Columbus OH"),
    ("Plumbing and Drain Specialist", "Denver CO"),
    ("Electrical Contractor Commercial", "Austin TX"),
    ("Spray Foam Insulation Contractor", "Dallas TX"),

    # Structural, Concrete, Deck & Outdoor Trades
    ("Epoxy Garage Flooring", "Tampa FL"),
    ("Epoxy Garage Flooring", "Dallas TX"),
    ("Foundation Repair and Waterproofing", "Charlotte NC"),
    ("Waterproofing and Basement Sealing", "Pittsburgh PA"),
    ("Concrete and Stamped Paving", "Las Vegas NV"),
    ("Structural Framing Contractor", "Phoenix AZ"),
    ("Deck and Patio Builder", "Portland OR"),
    ("Siding and Window Replacement", "Kansas City MO"),
    ("Hardscaping and Pavers Contractor", "Fort Lauderdale FL"),
    ("Custom Pool and Spa Builder", "Phoenix AZ"),
    ("Tree Removal and Arborist", "Raleigh NC"),
    ("Tree Removal and Arborist", "Atlanta GA"),
    ("Driveway Paving and Asphalt", "Richmond VA"),
    ("Custom Fencing and Automatic Gates", "San Antonio TX")
]


def clean_human_name(raw_name, email=""):
    if not raw_name:
        return None
    name = str(raw_name).strip()
    if name in ["Owner", "Business Owner", "Founder", "President", "Principal", "Admin", "Team", "Office", "Staff"]:
        return None
    prefix = email.split("@")[0].lower() if "@" in email else ""
    if name.lower() == prefix or name.lower() in [
        "info", "admin", "contact", "office", "sales", "support", "help", "team", "billing", "service", "hello", "quote", "estimates"
    ]:
        return None
    if re.search(r"[0-9_\-@\.]", name):
        return None
    first = name.split()[0].capitalize()
    if len(first) < 2 or len(first) > 15:
        return None
    if first.lower() in [
        "company", "contractor", "services", "custom", "commercial", "residential", "quality", "general", "direct", "local", "premier"
    ]:
        return None
    return first


def clean_biz_name(raw):
    if not raw:
        return "your business"
    cleaned = str(raw).strip()
    for delim in [":", "|", " - ", " -- ", " | "]:
        if delim in cleaned:
            parts = cleaned.split(delim)
            if len(parts[0].strip()) >= 3:
                cleaned = parts[0].strip()
                break
    return cleaned


def generate_pitch(lead):
    biz = clean_biz_name(lead.get("business_name"))
    raw_owner = lead.get("owner_name") or lead.get("recipient_name")
    email = lead.get("recipient_email") or lead.get("email") or ""
    owner = clean_human_name(raw_owner, email)
    city = lead.get("city", "your area")
    cat = lead.get("category", "contractor")
    domain = lead.get("domain", "")

    # Clean city display
    display_city = city.split(",")[0].strip() if "," in city else city

    # Hash deterministically for balanced rotation across 4 concrete contractor angles
    h = abs(hash(email or biz))
    angle_idx = h % 4

    if owner:
        greeting = f"Hi {owner},"
        is_direct = True
    else:
        greeting = "Hi there,"
        is_direct = False

    if angle_idx == 0:
        # Angle 0: Missed-Call Ladder Reality (Invoca 48% Missed Call Data)
        subject = f"quick question for {owner} re {biz}" if is_direct else f"missed calls on site - {biz}"
        body = (
            f"{greeting}\n\n"
            f"Came across {biz} while checking out {cat.lower()} contractors in {display_city}.\n\n"
            f"Most contractors I talk to lose 3 to 5 good jobs a month simply because when you or your crew are out on a job site or ladder, you cannot grab the phone. Homeowners almost never leave a voicemail; they just tap the next contractor on Google.\n\n"
            f"We set up a simple 15-second text-back bridge that catches those callers immediately and holds the estimate on your cell before they call anyone else.\n\n"
            f"Mind if I send over a 15-second preview of how it looks on mobile?\n\n"
            f"Best,\n"
            f"Faiz Majeed\n"
            f"FZCORE Studio | fzcorestudio.com"
        )
    elif angle_idx == 1:
        # Angle 1: Dead Quotes & Dormant Estimates (Jobber Database Reactivation)
        subject = f"past quotes for {biz}" if is_direct else f"quick question re past quotes - {biz}"
        body = (
            f"{greeting}\n\n"
            f"Hope the week is going well for the crew at {biz}.\n\n"
            f"Most established {cat.lower()} companies sit on 200 to 500+ past estimates from homeowners who ghosted or postponed over the last year.\n\n"
            f"We run a simple 2-text reactivation protocol that usually re-opens 3 to 8 of those dormant jobs ($15k to $40k+ in work) with zero ad spend.\n\n"
            f"Mind if I send over the exact 2-text sequence so you can see how it works?\n\n"
            f"Best,\n"
            f"Faiz Majeed\n"
            f"FZCORE Studio | fzcorestudio.com"
        )
    elif angle_idx == 2:
        # Angle 2: Tire-Kicker / Ghosted Bid 30s Filter (Unpaid Driving Bleed)
        subject = f"quick question for {owner} re {biz}" if is_direct else f"unqualified bids - {biz}"
        body = (
            f"{greeting}\n\n"
            f"Came across {biz} while looking at {cat.lower()} work in {display_city}.\n\n"
            f"One of the biggest time drains contractors deal with is driving 40 minutes for an on-site estimate, only to find out the homeowner has a tiny budget or is just price shopping.\n\n"
            f"We built a quick 3-step property and budget intake filter that pre-qualifies homeowners on their phone before you ever get in the truck.\n\n"
            f"Mind if I send over a quick preview link of how it works?\n\n"
            f"Best,\n"
            f"Faiz Majeed\n"
            f"FZCORE Studio | fzcorestudio.com"
        )
    else:
        # Angle 3: Exclusive Local Project Capacity (Anti-Angi / Dylan Capacity Model)
        subject = f"exclusive capacity in {display_city} - {biz}" if is_direct else f"project capacity in {display_city} - {biz}"
        body = (
            f"{greeting}\n\n"
            f"Came across {biz} while reviewing {cat.lower()} contractors around {display_city}.\n\n"
            f"We work with homeowners who need {cat.lower()} work done, but unlike Angi or Thumbtack, we never share leads with four other guys or start a bidding war.\n\n"
            f"Wanted to check if you and your crews currently have room to take on 2 to 3 exclusive projects this month?\n\n"
            f"If you have capacity, let me know and I can send over the details.\n\n"
            f"Best,\n"
            f"Faiz Majeed\n"
            f"FZCORE Studio | fzcorestudio.com"
        )

    return subject, body


def harvest_fresh_leads(data_dir: Path, target_count: int = 35):
    # Dynamic Multi-Query Lead Hunting: iterates continuously through query pool until target is met
    query_pool = list(HIGH_TICKET_QUERIES)
    random.shuffle(query_pool)

    print(f"\n🚀 [HIGH-VOLUME HARVESTER] Starting Dynamic Multi-Niche Harvest (Target: {target_count} qualified leads)...")

    pitches_file = data_dir / "approved_pitches.json"
    sent_ledger_file = data_dir / "sent_ledger.json"
    supp_file = data_dir / "suppression_list.json"

    existing_pitches = []
    if pitches_file.exists():
        try:
            with open(pitches_file, "r", encoding="utf-8") as pf:
                existing_pitches = json.load(pf)
        except Exception:
            existing_pitches = []

    sent_emails = set()
    if sent_ledger_file.exists():
        try:
            with open(sent_ledger_file, "r", encoding="utf-8") as lf:
                ledger = json.load(lf)
                for v in ledger.values():
                    if isinstance(v, dict):
                        em = v.get("recipient") or v.get("recipient_email") or v.get("email")
                        if em:
                            sent_emails.add(str(em).strip().lower())
        except Exception:
            pass

    suppressed = set()
    if supp_file.exists():
        try:
            with open(supp_file, "r", encoding="utf-8") as sf:
                suppressed = set(json.load(sf))
        except Exception:
            pass

    seen_emails = {p.get("recipient_email", "").strip().lower() for p in existing_pitches}
    seen_domains = {p.get("domain", "").strip().lower() for p in existing_pitches}

    new_qualified = []
    harvest_start = time.time()
    max_harvest_secs = 1080  # 18 minutes safe execution ceiling

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for niche, location in query_pool:
            if len(new_qualified) >= target_count:
                print(f"🎯 Reached target count of {target_count} verified leads! Ending crawl early.")
                break

            if (time.time() - harvest_start) > max_harvest_secs:
                print(f"⏰ Harvester time limit reached ({int(time.time() - harvest_start)}s). Wrapping up batch.")
                break

            search_query = f"{niche} in {location}"
            print(f"\n[*] Hunting Google Maps: '{search_query}' (Progress: {len(new_qualified)}/{target_count})...")

            try:
                url = f"https://www.google.com/maps/search/{urllib.parse.quote(search_query)}"
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(2500)

                # Progressive deep scroll with responsive card checks
                feed_selector = 'div[role="feed"]'
                try:
                    page.wait_for_selector(feed_selector, timeout=8000)
                    last_card_count = 0
                    stagnant_count = 0
                    for _ in range(15):
                        page.evaluate(f'document.querySelector("{feed_selector}").scrollBy(0, 2400);')
                        page.wait_for_timeout(1200)
                        curr_cnt = len(page.query_selector_all('div[role="feed"] > div > div[role="article"], div[role="feed"] a[href*="/maps/place/"]'))
                        if curr_cnt >= 50:
                            break
                        if curr_cnt == last_card_count:
                            stagnant_count += 1
                            if stagnant_count >= 3:
                                break
                        else:
                            stagnant_count = 0
                            last_card_count = curr_cnt
                except Exception:
                    pass

                cards = page.query_selector_all('div[role="feed"] > div > div[role="article"], div[role="feed"] a[href*="/maps/place/"]')
                print(f"    -> Loaded {len(cards)} listings for '{search_query}'. Auditing...")

                for card in cards:
                    if len(new_qualified) >= target_count:
                        break

                    try:
                        aria = card.get_attribute("aria-label") or ""
                        text = card.inner_text()
                        title = aria or text.split("\n")[0]
                        if not title or len(title) < 3:
                            continue

                        # Extract website link
                        website_btn = card.query_selector('a[data-value="Website"], a[href^="http"]:not([href*="google"])')
                        website = website_btn.get_attribute("href") if website_btn else None

                        if not website:
                            links = card.query_selector_all('a[href^="http"]')
                            for l in links:
                                h = l.get_attribute("href")
                                if h and "google.com" not in h:
                                    website = h
                                    break

                        if not website:
                            continue

                        domain = urllib.parse.urlparse(website).netloc.lower().replace("www.", "")
                        if not domain or domain in seen_domains or any(bad in domain for bad in ["facebook", "yelp", "instagram", "angi", "thumbtack"]):
                            continue

                        # Review count check (prefer 3 to 35 reviews)
                        rev_match = re.search(r"\((\d+)\)", text)
                        rev_count = int(rev_match.group(1)) if rev_match else 14
                        if rev_count > 45:
                            continue

                        seen_domains.add(domain)

                        # Deep Audit site (homepage + /contact)
                        audit = audit_contractor_site(website)
                        if not audit.get("mx_valid") or not audit.get("verified_email"):
                            continue

                        verified_email = audit["verified_email"].lower().strip()
                        if verified_email in seen_emails or verified_email in sent_emails or verified_email in suppressed:
                            continue

                        raw_owner = audit.get("owner_name", "Business Owner")
                        owner_name = clean_human_name(raw_owner, verified_email) or "Business Owner"
                        lead_obj = {
                            "business_name": title,
                            "owner_name": owner_name,
                            "category": niche,
                            "city": location,
                            "website": website,
                            "domain": domain,
                            "reviews_count": rev_count,
                            "recipient_email": verified_email,
                            "recipient_name": owner_name,
                            "mx_provider": audit.get("mx_provider", "Custom")
                        }

                        subject, body = generate_pitch(lead_obj)
                        pitch_record = {
                            "lead_id": f"FZ-{abs(hash(verified_email)) % 10000000000}",
                            "business_name": title,
                            "recipient_email": verified_email,
                            "recipient_name": owner_name,
                            "category": niche,
                            "city": location,
                            "website": website,
                            "domain": domain,
                            "reviews_count": rev_count,
                            "subject": subject,
                            "body": body,
                            "mx_provider": audit.get("mx_provider"),
                            "harvested_at": datetime.now(timezone.utc).isoformat()
                        }

                        new_qualified.append(pitch_record)
                        seen_emails.add(verified_email)
                        print(f"       🎯 [#{len(new_qualified)}] {title} ({rev_count} revs) -> {owner_name} <{verified_email}> [{audit['mx_provider']}]")

                    except Exception:
                        pass

            except Exception as q_err:
                print(f"    [!] Error querying '{search_query}': {q_err}")

        browser.close()

    if new_qualified:
        existing_pitches.extend(new_qualified)
        # Prioritize Direct Named Owners first
        existing_pitches.sort(key=lambda x: (1 if x.get("recipient_name") in ["Owner", "Business Owner", "Founder", "Team", None] else 0))

        with open(pitches_file, "w", encoding="utf-8") as pf:
            json.dump(existing_pitches, pf, indent=2)

        print(f"\n🎉 [HARVEST COMPLETE] Secured {len(new_qualified)} verified leads! Active vault inventory now: {len(existing_pitches)} pitches.")

    return len(new_qualified)
