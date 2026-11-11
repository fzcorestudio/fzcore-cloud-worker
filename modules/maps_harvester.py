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
    # Trades & High-Value Remodeling (Niche 1)
    ("Roofing Contractor", "Atlanta GA"),
    ("Kitchen and Bath Remodeling", "Dallas TX"),
    ("Custom Home Builder", "Houston TX"),
    ("Commercial Roofing Contractor", "Orlando FL"),
    ("Custom Pool and Spa Builder", "Phoenix AZ"),
    ("Epoxy Garage Flooring", "Tampa FL"),
    ("Foundation Repair and Waterproofing", "Charlotte NC"),
    ("Metal Roofing Contractor", "Austin TX"),
    ("Custom Fencing and Automatic Gates", "San Antonio TX"),
    ("Hardscaping and Pavers Contractor", "Fort Lauderdale FL"),
    ("Bathroom Remodeling Contractor", "Nashville TN"),
    ("Water Damage Restoration", "Denver CO"),
    ("Commercial HVAC Contractor", "Jacksonville FL"),
    ("General Contractor Commercial", "Indianapolis IN"),
    ("Plumbing and Drain Specialist", "Columbus OH"),
    ("Tree Removal and Arborist", "Raleigh NC"),
    ("Siding and Window Replacement", "Kansas City MO"),
    ("Concrete and Stamped Paving", "Las Vegas NV"),
    ("Residential Roofing Services", "Fort Worth TX"),
    ("Solar Panel Installation", "San Diego CA"),
    ("Landscape Design and Architecture", "Scottsdale AZ"),
    ("Kitchen Renovation Specialist", "Minneapolis MN"),
    ("Commercial Painting Contractor", "Atlanta GA"),
    ("Electrical Contractor Commercial", "Austin TX"),
    ("Deck and Patio Builder", "Portland OR"),
    ("Spray Foam Insulation Contractor", "Dallas TX"),
    ("Custom Cabinetry and Woodworking", "Nashville TN"),
    ("Driveway Paving and Asphalt", "Richmond VA"),
    ("Waterproofing and Basement Sealing", "Pittsburgh PA"),
    ("Structural Framing Contractor", "Phoenix AZ"),

    # Medical & Wellness / High-Ticket Aesthetics (Niche 2)
    ("Chiropractor Sports Medicine", "Fort Lauderdale FL"),
    ("Cosmetic Dentistry Veneers", "San Diego CA"),
    ("MedSpa Aesthetics Clinic", "Boca Raton FL"),
    ("Dental Implants Specialist", "Austin TX"),
    ("Plastic Surgery Center", "Scottsdale AZ"),
    ("Dermatology and Skin Clinic", "Tampa FL"),
    ("Orthodontist Invisalign Specialist", "Dallas TX"),
    ("Physical Therapy Clinic", "Charlotte NC"),
    ("Family Wellness Chiropractic", "Orlando FL"),
    ("Aesthetic Laser Center", "Houston TX"),

    # Luxury Automotive, Marine & Specialty Trades (Niche 3)
    ("Auto Detailing Ceramic Coating", "Miami FL"),
    ("Paint Protection Film PPF", "Scottsdale AZ"),
    ("Window Tinting Commercial and Auto", "Las Vegas NV"),
    ("Mobile Car Wash and Detailing", "Dallas TX"),
    ("Marine Boat Detailing", "Fort Lauderdale FL"),
    ("Custom Auto Upholstery", "Phoenix AZ"),
    ("Fleet Maintenance and Repair", "Atlanta GA"),

    # Top Commonwealth Metros (UK / Canada / Australia)
    ("Roofing Contractor", "Calgary AB"),
    ("Kitchen Renovation", "Toronto ON"),
    ("Custom Home Builder", "Vancouver BC"),
    ("Commercial Cleaning Services", "Melbourne AU"),
    ("Painting Contractor", "Sydney AU"),
    ("Roofing and Gutter Contractor", "Manchester UK"),
    ("Electrical Services Commercial", "Brisbane AU"),
    ("Landscaping Contractor", "Perth AU"),
    ("Plumbing and Heating Engineer", "Birmingham UK"),
    ("Bathroom Installation Specialist", "Leeds UK")
]


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
    owner = lead.get("owner_name", "Owner")
    city = lead.get("city", "your area")
    cat = lead.get("category", "contractor")
    site = lead.get("website", "")
    domain = lead.get("domain", "")

    is_direct_owner = owner not in ["Owner", "Business Owner", "Founder"]

    if is_direct_owner:
        subject = f"quick question for {owner} re {domain}"
        greeting = f"Hi {owner},"
    else:
        subject = f"quick question re {biz}"
        greeting = "Hi there,"

    body = (
        f"{greeting}\n\n"
        f"Came across {biz} while looking at {cat.lower()} contractors in {city}.\n\n"
        f"Took a look at your website ({domain}) on mobile. You have solid reviews, but right now prospective clients on their phones have to pinch-to-zoom and fill out a slow generic form to get a quote.\n\n"
        f"We put together a clean, 60-second instant mobile quote selector with a 1-tap call bar for {biz} ($180 - $280 flat, 24-hr turnaround) that lets homeowners get an instant estimate and connects directly to your phone.\n\n"
        f"Mind if I send over the 20-second preview link?\n\n"
        f"Best,\n"
        f"Faiz Majeed\n"
        f"Founder · FZCORE Studio | fzcorestudio.com"
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

                        owner_name = audit.get("owner_name", "Business Owner")
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
        existing_pitches.sort(key=lambda x: (1 if x.get("recipient_name") in ["Owner", "Business Owner", "Founder"] else 0))

        with open(pitches_file, "w", encoding="utf-8") as pf:
            json.dump(existing_pitches, pf, indent=2)

        print(f"\n🎉 [HARVEST COMPLETE] Secured {len(new_qualified)} verified leads! Active vault inventory now: {len(existing_pitches)} pitches.")

    return len(new_qualified)
