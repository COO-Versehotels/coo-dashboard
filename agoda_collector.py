from playwright.sync_api import sync_playwright
import json
import re
import os
from datetime import datetime

DATA_FILE = "data.json"
HISTORY_FILE = "history.json"
TRAVELOKA_PROFILE_DIR = r"C:\coo-dashboard\traveloka_profile"

HOTELS = {
    "Verse Lite Gajah Mada": {
        "agoda": "https://www.agoda.com/verse-lite-hotel-gajah-mada/reviews/jakarta-id.html",
        "booking": "https://www.booking.com/hotel/id/verse-lite-pembangunan.html#tab-reviews",
        "traveloka": "https://www.traveloka.com/id-id/hotel/indonesia/verse-lite-hotel-gajah-mada-3000010028056",
        "tripcom": "https://id.trip.com/hotels/central-jakarta-city-hotel-detail-6449572/verse-lite-hotel-gajah-mada/?locale=en-ID&allianceid=14901&sid=1621541&ppcid=ckid-_adid-_akid-_adgid-&utm_source=google&utm_medium=cpc&utm_campaign=15838633181&gad_source=1&gad_campaignid=20414003930&gbraid=0AAAAABn2eFLKWLrN2-2WPDMNEjxdpOATE&gclid=Cj0KCQjw-pHPBhCdARIsAHXYWP8-IxMMwEn7v8dBYOar8l3aD7U3YLMJyawc4tgI_wy5cJr2nbOkf4saArAdEALw_wcB",
        "tiket": "https://www.tiket.com/id-id/review?product_type=TIXHOTEL&searchType=INVENTORY&inventory_id=verse-lite-hotel-gajah-mada-807001751612826254"
    },
    "Verse Luxe Wahid Hasyim": {
        "agoda": "https://www.agoda.com/verse-luxe-hotel-wahid-hasyim/reviews/jakarta-id.html",
        "booking": "https://www.booking.com/hotel/id/verse-luxe-wahid-hasyim.html#tab-reviews",
        "traveloka": "https://www.traveloka.com/id-id/hotel/detail?spec=17-05-2026.18-05-2026.1.1.HOTEL.3000010036666.Verse%20Luxe%20Hotel%20Wahid%20Hasyim.2",
        "tripcom": "https://id.trip.com/hotels/central-jakarta-city-hotel-detail-9029304/verse-luxe-hotel-wahid-hasyim/?locale=en-ID&allianceid=14901&sid=1621541&ppcid=ckid-_adid-_akid-_adgid-&utm_source=google&utm_medium=cpc&utm_campaign=15838633181&gad_source=1&gad_campaignid=20414003930&gbraid=0AAAAABn2eFLKWLrN2-2WPDMNEjxdpOATE&gclid=Cj0KCQjw-pHPBhCdARIsAHXYWP_SdUWp5jWpmisfXUGOgiURDpGP3pNiAMnCtMdhO_zZ7xD3ArQc47EaAv41EALw_wcB",
        "tiket": "https://www.tiket.com/en-id/review?product_type=TIXHOTEL&searchType=INVENTORY&inventory_id=verse-luxe-hotel-wahid-hasyim-112001545304320268"
    },
    "Verse Cirebon": {
        "agoda": "https://www.agoda.com/verse-hotel-cirebon/reviews/cirebon-id.html",
        "booking": "https://www.booking.com/hotel/id/verse-cirebon.html#tab-reviews",
        "traveloka": "https://www.traveloka.com/id-id/hotel/detail?spec=17-05-2026.18-05-2026.1.1.HOTEL.3000010015654.Verse%20Hotel%20Cirebon.2",
        "tripcom": "https://id.trip.com/hotels/kedawung-hotel-detail-5965336/verse-hotel-cirebon/?locale=en-ID&allianceid=14901&sid=4232505&ppcid=adid-794102872705_akid-dsa-1465719063011_adgid-191379360665&utm_source=google&utm_medium=cpc&utm_campaign=23491399628&gad_source=1",
        "tiket": "https://www.tiket.com/id-id/review?product_type=TIXHOTEL&searchType=INVENTORY&inventory_id=verse-hotel-cirebon-108001534490349528"
    },
    "Oak Tree Mahakam Blok M": {
        "agoda": "https://www.agoda.com/oak-tree-urban-hotel/reviews/jakarta-id.html",
        "booking": "https://www.booking.com/hotel/id/oak-tree-urban.html#tab-reviews",
        "traveloka": "https://www.traveloka.com/id-id/hotel/detail?spec=17-05-2026.18-05-2026.1.1.HOTEL.461895.Oak%20Tree%20Urban%20Hotel%20Jakarta.2",
        "tripcom": "https://id.trip.com/hotels/south-jakarta-city-hotel-detail-2652976/oak-tree-urban-hotel-jakarta/?locale=en-ID&allianceid=14901&sid=4232505&ppcid=adid-794102872705_akid-dsa-1465719063011_adgid-191379360665&utm_source=google&utm_medium=cpc&utm_campaign=23491399628&gad_source=1",
        "tiket": "https://www.tiket.com/id-id/review?product_type=TIXHOTEL&searchType=INVENTORY&inventory_id=oak-tree-urban-jakarta-412001639976768183"
    }
}

PLATFORM_SCOPE = ["agoda", "booking", "traveloka", "tripcom", "tiket"]


def clean_number(text):
    if not text:
        return "N/A"
    digits = re.sub(r"[^\d]", "", str(text))
    return digits if digits else "N/A"


def clean_rating(text):
    if not text:
        return "N/A"
    text = str(text).strip().replace(",", ".")
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    return match.group(1) if match else "N/A"


def normalize_text(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def is_valid_rating(value, minimum, maximum):
    try:
        num = float(value)
        return minimum <= num <= maximum
    except Exception:
        return False


def is_valid_reviews(value, minimum=1):
    try:
        num = int(str(value))
        return num >= minimum
    except Exception:
        return False


def make_result(rating="N/A", reviews="N/A", ranking=None, status="N/A", source_date=None, error_reason=None):
    return {
        "rating": rating,
        "reviews": reviews,
        "ranking": ranking,
        "status": status,
        "source_date": source_date,
        "error_reason": error_reason
    }


def load_json_file(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def load_history():
    return load_json_file(HISTORY_FILE, [])


def load_current_data():
    return load_json_file(DATA_FILE, {})


def save_history_snapshot(history, hotels_data):
    today = datetime.now().strftime("%Y-%m-%d")
    snapshot = {
        "date": today,
        "hotels": hotels_data
    }

    replaced = False
    for i, item in enumerate(history):
        if item.get("date") == today:
            history[i] = snapshot
            replaced = True
            break

    if not replaced:
        history.append(snapshot)

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def get_start_of_month_snapshot(history):
    now = datetime.now()
    month_prefix = now.strftime("%Y-%m-")
    month_data = [x for x in history if x.get("date", "").startswith(month_prefix)]
    if not month_data:
        return None
    month_data.sort(key=lambda x: x["date"])
    return month_data[0]


def get_last_valid_platform(previous_data, hotel_name, platform_name):
    try:
        for hotel in previous_data.get("hotels", []):
            if hotel.get("name") == hotel_name:
                platform_data = hotel.get("platforms", {}).get(platform_name)
                if platform_data:
                    rating = platform_data.get("rating", "N/A")
                    reviews = platform_data.get("reviews", "N/A")
                    if rating != "N/A" or reviews != "N/A":
                        return platform_data
    except Exception:
        pass
    return None


def finalize_platform_result(hotel_name, platform_name, fresh_data, previous_data):
    today = datetime.now().strftime("%Y-%m-%d")
    has_fresh = (fresh_data.get("rating") != "N/A" or fresh_data.get("reviews") != "N/A")
    match_ok = fresh_data.get("match_ok", False)
    error_reason = fresh_data.get("error_reason")

    if has_fresh and match_ok:
        return make_result(
            rating=fresh_data.get("rating", "N/A"),
            reviews=fresh_data.get("reviews", "N/A"),
            ranking=fresh_data.get("ranking"),
            status="AUTO",
            source_date=today,
            error_reason=None
        )

    cached = get_last_valid_platform(previous_data, hotel_name, platform_name)
    if cached:
        return make_result(
            rating=cached.get("rating", "N/A"),
            reviews=cached.get("reviews", "N/A"),
            ranking=cached.get("ranking"),
            status="CACHED",
            source_date=cached.get("source_date"),
            error_reason=error_reason
        )

    return make_result(
        rating="N/A",
        reviews="N/A",
        ranking=fresh_data.get("ranking"),
        status="ERROR",
        source_date=None,
        error_reason=error_reason or "selector_mismatch"
    )


def build_monthly_comparison(hotels_today, start_snapshot):
    start_map = {}
    if start_snapshot:
        for hotel in start_snapshot.get("hotels", []):
            start_map[hotel["name"]] = hotel

    final_hotels = []

    for hotel in hotels_today:
        name = hotel["name"]
        hotel["comparison"] = {
            "baseline_date": start_snapshot["date"] if start_snapshot else None,
            "platforms": {}
        }

        start_platforms = start_map.get(name, {}).get("platforms", {})

        for platform_name, current_values in hotel["platforms"].items():
            rating_change = None
            review_change = None
            ranking_change = None

            start_values = start_platforms.get(platform_name)
            if start_values:
                try:
                    rating_change = round(
                        float(current_values["rating"]) - float(start_values["rating"]), 1
                    )
                except Exception:
                    rating_change = None

                try:
                    review_change = int(str(current_values["reviews"])) - int(str(start_values["reviews"]))
                except Exception:
                    review_change = None

                try:
                    current_rank_match = re.search(r"#(\d+)", str(current_values.get("ranking", "")))
                    start_rank_match = re.search(r"#(\d+)", str(start_values.get("ranking", "")))
                    if current_rank_match and start_rank_match:
                        ranking_change = int(start_rank_match.group(1)) - int(current_rank_match.group(1))
                except Exception:
                    ranking_change = None

            hotel["comparison"]["platforms"][platform_name] = {
                "rating_change": rating_change,
                "review_change": review_change,
                "ranking_change": ranking_change
            }

        final_hotels.append(hotel)

    return final_hotels


def get_page_text(page, wait_ms=7000):
    page.wait_for_timeout(wait_ms)

    try:
        page.wait_for_load_state("domcontentloaded", timeout=10000)
    except Exception:
        pass

    try:
        return normalize_text(page.locator("body").inner_text(timeout=10000))
    except Exception:
        try:
            return normalize_text(page.text_content("body", timeout=10000) or "")
        except Exception:
            return ""


def parse_agoda(text):
    rating = "N/A"
    reviews = "N/A"

    rating_match = re.search(r"\b(\d\.\d)\b", text)
    if rating_match:
        rating = rating_match.group(1)

    review_match = re.search(r"([\d,\.]+)\s+reviews", text, re.IGNORECASE)
    if review_match:
        reviews = clean_number(review_match.group(1))

    if not is_valid_rating(rating, 1, 10):
        rating = "N/A"
    if not is_valid_reviews(reviews):
        reviews = "N/A"

    ok = (rating != "N/A" and reviews != "N/A")
    return {
        "rating": rating,
        "reviews": reviews,
        "ranking": None,
        "match_ok": ok,
        "error_reason": None if ok else "main_review_block_not_found"
    }


def parse_booking(text):
    rating = "N/A"
    reviews = "N/A"

    rating_patterns = [
        r"Scored\s+(\d\.\d)",
        r"(\d\.\d)\s*(?:Very good|Wonderful|Exceptional|Good|Baik|Menyenangkan|Istimewa|Sangat baik|Luar biasa)"
    ]
    for pattern in rating_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            rating = match.group(1)
            break

    review_match = re.search(r"([\d,\.]+)\s+reviews", text, re.IGNORECASE)
    if review_match:
        reviews = clean_number(review_match.group(1))

    if not is_valid_rating(rating, 1, 10):
        rating = "N/A"
    if not is_valid_reviews(reviews):
        reviews = "N/A"

    ok = (rating != "N/A" and reviews != "N/A")
    return {
        "rating": rating,
        "reviews": reviews,
        "ranking": None,
        "match_ok": ok,
        "error_reason": None if ok else "main_review_block_not_found"
    }


def parse_tripcom(text):
    rating = "N/A"
    reviews = "N/A"

    rating_patterns = [
        r"\b(\d[.,]\d)\s*/\s*10\b",
        r"\b(\d[.,]\d)\s*/\s*5\b",
        r"\b(\d[.,]\d)\s*out of 5\b",
    ]
    for pattern in rating_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            rating = clean_rating(match.group(1))
            break

    review_patterns = [
        r"\bAll\s+([\d,\.]+)\s+reviews\b",
        r"\b([\d,\.]+)\s+reviews\b",
        r"\b([\d,\.]+)\s+review\b",
    ]
    for pattern in review_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            reviews = clean_number(match.group(1))
            break

    rating_ok = is_valid_rating(rating, 1, 10) or is_valid_rating(rating, 1, 5)
    if rating != "N/A" and not rating_ok:
        rating = "N/A"
    if not is_valid_reviews(reviews, 5):
        reviews = "N/A"

    match_ok = (rating != "N/A" and reviews != "N/A")
    error_reason = None if match_ok else "main_review_block_not_found"

    return {
        "rating": rating,
        "reviews": reviews,
        "ranking": None,
        "match_ok": match_ok,
        "error_reason": error_reason
    }


def parse_tiket(text):
    rating = "N/A"
    reviews = "N/A"

    rating_patterns = [
        r"\b(\d[.,]\d)\s*/\s*5\b",
        r"\b(\d[.,]\d)\s*/\s*10\b",
        r"Rating\s*(\d[.,]\d)"
    ]
    for pattern in rating_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            rating = clean_rating(match.group(1))
            break

    review_patterns = [
        r"\(([\d,\.]+)\s+reviews\)",
        r"\b([\d,\.]+)\s+reviews\b",
        r"\b([\d,\.]+)\s+review\b",
        r"\b([\d,\.]+)\s+ulasan\b",
        r"\bfrom\s+([\d,\.]+)\s+reviews\b"
    ]
    for pattern in review_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            reviews = clean_number(match.group(1))
            break

    rating_ok = is_valid_rating(rating, 1, 5) or is_valid_rating(rating, 1, 10)
    if rating != "N/A" and not rating_ok:
        rating = "N/A"
    if not is_valid_reviews(reviews, 5):
        reviews = "N/A"

    match_ok = (rating != "N/A" and reviews != "N/A")
    error_reason = None if match_ok else "main_review_block_not_found"

    return {
        "rating": rating,
        "reviews": reviews,
        "ranking": None,
        "match_ok": match_ok,
        "error_reason": error_reason
    }


def traveloka_extract_from_main_page(text):
    """
    Target format utama yang terlihat di browser asli:
    8,3/10
    Mengesankan
    6.458 ulasan
    """
    rating = "N/A"
    reviews = "N/A"

    # Cari pasangan rating /10 dan ulasan yang posisinya dekat
    rating_matches = list(re.finditer(r"\b(\d[.,]\d)\s*/\s*10\b", text, re.IGNORECASE))
    review_matches = list(re.finditer(r"([\d\.,]+)\s+ulasan\b", text, re.IGNORECASE))

    best_pair = None
    best_distance = None

    for rm in rating_matches:
        candidate_rating = clean_rating(rm.group(1))
        if not is_valid_rating(candidate_rating, 5, 10):
            continue

        for rv in review_matches:
            candidate_reviews = clean_number(rv.group(1))
            if not is_valid_reviews(candidate_reviews, 50):
                continue

            distance = abs(rv.start() - rm.start())
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_pair = (candidate_rating, candidate_reviews)

    if best_pair:
        rating, reviews = best_pair

    if rating == "N/A":
        m = re.search(r"\b(\d[.,]\d)\s*/\s*10\b", text, re.IGNORECASE)
        if m:
            candidate_rating = clean_rating(m.group(1))
            if is_valid_rating(candidate_rating, 5, 10):
                rating = candidate_rating

    if reviews == "N/A":
        m = re.search(r"([\d\.,]+)\s+ulasan\b", text, re.IGNORECASE)
        if m:
            candidate_reviews = clean_number(m.group(1))
            if is_valid_reviews(candidate_reviews, 50):
                reviews = candidate_reviews

    match_ok = (rating != "N/A" and reviews != "N/A")
    return {
        "rating": rating,
        "reviews": reviews,
        "ranking": None,
        "match_ok": match_ok,
        "error_reason": None if match_ok else "main_page_pattern_not_found"
    }


def fetch_traveloka_with_real_browser(playwright, url):
    os.makedirs(TRAVELOKA_PROFILE_DIR, exist_ok=True)

    context = playwright.chromium.launch_persistent_context(
        TRAVELOKA_PROFILE_DIR,
        headless=False,
        locale="id-ID",
        viewport={"width": 1440, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        args=[
            "--disable-blink-features=AutomationControlled"
        ]
    )

    try:
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(url, timeout=90000, wait_until="domcontentloaded")
        page.wait_for_timeout(12000)

        # coba tutup banner/popup kalau ada
        popup_selectors = [
            'button:has-text("Nanti saja")',
            'button:has-text("Tutup")',
            'button:has-text("Close")',
            'button:has-text("Skip")',
            '[aria-label="Close"]'
        ]
        for selector in popup_selectors:
            try:
                page.locator(selector).first.click(timeout=1000)
                page.wait_for_timeout(1000)
            except Exception:
                pass

        text = get_page_text(page, 6000)
        result = traveloka_extract_from_main_page(text)
        return result
    finally:
        context.close()


def main():
    previous_data = load_current_data()
    hotels_today = []

    with sync_playwright() as p:
        # browser normal untuk non-Traveloka
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="en-US",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        for hotel_name, sources in HOTELS.items():
            print("Hotel:", hotel_name)

            hotel_record = {
                "name": hotel_name,
                "platforms": {}
            }

            print("  agoda")
            try:
                page.goto(sources["agoda"], timeout=60000, wait_until="domcontentloaded")
                text = get_page_text(page, 6000)
                fresh = parse_agoda(text)
            except Exception:
                fresh = {
                    "rating": "N/A",
                    "reviews": "N/A",
                    "ranking": None,
                    "match_ok": False,
                    "error_reason": "page_load_failed"
                }
            parsed = finalize_platform_result(hotel_name, "agoda", fresh, previous_data)
            print("     rating:", parsed["rating"])
            print("     reviews:", parsed["reviews"])
            print("     status:", parsed["status"])
            if parsed.get("error_reason"):
                print("     error:", parsed["error_reason"])
            hotel_record["platforms"]["agoda"] = parsed

            print("  booking")
            try:
                page.goto(sources["booking"], timeout=60000, wait_until="domcontentloaded")
                text = get_page_text(page, 6000)
                fresh = parse_booking(text)
            except Exception:
                fresh = {
                    "rating": "N/A",
                    "reviews": "N/A",
                    "ranking": None,
                    "match_ok": False,
                    "error_reason": "page_load_failed"
                }
            parsed = finalize_platform_result(hotel_name, "booking", fresh, previous_data)
            print("     rating:", parsed["rating"])
            print("     reviews:", parsed["reviews"])
            print("     status:", parsed["status"])
            if parsed.get("error_reason"):
                print("     error:", parsed["error_reason"])
            hotel_record["platforms"]["booking"] = parsed

            print("  traveloka")
            try:
                fresh = fetch_traveloka_with_real_browser(p, sources["traveloka"])
            except Exception:
                fresh = {
                    "rating": "N/A",
                    "reviews": "N/A",
                    "ranking": None,
                    "match_ok": False,
                    "error_reason": "page_load_failed"
                }
            parsed = finalize_platform_result(hotel_name, "traveloka", fresh, previous_data)
            print("     rating:", parsed["rating"])
            print("     reviews:", parsed["reviews"])
            print("     status:", parsed["status"])
            if parsed.get("error_reason"):
                print("     error:", parsed["error_reason"])
            hotel_record["platforms"]["traveloka"] = parsed

            print("  tripcom")
            try:
                page.goto(sources["tripcom"], timeout=60000, wait_until="domcontentloaded")
                text = get_page_text(page, 9000)
                fresh = parse_tripcom(text)
            except Exception:
                fresh = {
                    "rating": "N/A",
                    "reviews": "N/A",
                    "ranking": None,
                    "match_ok": False,
                    "error_reason": "page_load_failed"
                }
            parsed = finalize_platform_result(hotel_name, "tripcom", fresh, previous_data)
            print("     rating:", parsed["rating"])
            print("     reviews:", parsed["reviews"])
            print("     status:", parsed["status"])
            if parsed.get("error_reason"):
                print("     error:", parsed["error_reason"])
            hotel_record["platforms"]["tripcom"] = parsed

            print("  tiket")
            try:
                page.goto(sources["tiket"], timeout=60000, wait_until="domcontentloaded")
                text = get_page_text(page, 9000)
                fresh = parse_tiket(text)
            except Exception:
                fresh = {
                    "rating": "N/A",
                    "reviews": "N/A",
                    "ranking": None,
                    "match_ok": False,
                    "error_reason": "page_load_failed"
                }
            parsed = finalize_platform_result(hotel_name, "tiket", fresh, previous_data)
            print("     rating:", parsed["rating"])
            print("     reviews:", parsed["reviews"])
            print("     status:", parsed["status"])
            if parsed.get("error_reason"):
                print("     error:", parsed["error_reason"])
            hotel_record["platforms"]["tiket"] = parsed

            hotels_today.append(hotel_record)

        context.close()
        browser.close()

    history = load_history()
    save_history_snapshot(history, hotels_today)

    history = load_history()
    start_snapshot = get_start_of_month_snapshot(history)
    final_hotels = build_monthly_comparison(hotels_today, start_snapshot)

    data = {
        "last_update": str(datetime.now()),
        "comparison_mode": "start_of_month_vs_today",
        "platform_scope": PLATFORM_SCOPE,
        "hotels": final_hotels
    }

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("\nSELESAI")


if __name__ == "__main__":
    main()