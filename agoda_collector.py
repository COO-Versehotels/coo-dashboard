from playwright.sync_api import sync_playwright
import json
import re
import os
import time
from datetime import datetime

DATA_FILE = "data.json"
HISTORY_FILE = "history.json"
LOG_FILE = "error_log.txt"
<<<<<<< HEAD
DEBUG_TIKET_FILE = "debug_tiket.txt"   # v3.2: dump teks Tiket untuk analisa

# ============================================================
# v3.2 — Tambah debug logging untuk Tiket
# Tujuan: lihat apa yang Playwright dapat dari Tiket di GitHub Actions
# ============================================================

MAX_RETRY = 3
RETRY_DELAYS = [5, 15, 45]

NETWORK_ERROR_PATTERNS = [
    "ERR_NETWORK_IO_SUSPENDED",
    "ERR_INTERNET_DISCONNECTED",
    "ERR_NAME_NOT_RESOLVED",
    "ERR_CONNECTION_REFUSED",
    "ERR_CONNECTION_RESET",
    "ERR_CONNECTION_TIMED_OUT",
    "ERR_PROXY_CONNECTION_FAILED",
    "net::ERR_FAILED",
]

HOTEL_FAILURE_THRESHOLD = 3
HOTEL_COOLDOWN_SECONDS = 30
=======
DEBUG_TIKET_FILE = "debug_tiket.txt"
DEBUG_TRIP_FILE = "debug_trip.txt"

MAX_RETRY = 3
RETRY_DELAY_SECONDS = 6
>>>>>>> 65709b9 (fix final scraper v7 all platforms auto)

HOTELS = {
    "Verse Lite Gajah Mada": {
        "agoda": "https://www.agoda.com/verse-lite-hotel-gajah-mada/reviews/jakarta-id.html",
        "booking": "https://www.booking.com/hotel/id/verse-lite-pembangunan.html#tab-reviews",
        "traveloka": "https://www.traveloka.com/id-id/hotel/indonesia/verse-lite-hotel-gajah-mada-3000010028056",
        "tripcom": "https://id.trip.com/hotels/central-jakarta-city-hotel-detail-6449572/verse-lite-hotel-gajah-mada/",
        "tiket": "https://www.tiket.com/id-id/hotel/indonesia/verse-lite-hotel-gajah-mada-807001751612826254"
    },
    "Verse Luxe Wahid Hasyim": {
        "agoda": "https://www.agoda.com/verse-luxe-hotel-wahid-hasyim/reviews/jakarta-id.html",
        "booking": "https://www.booking.com/hotel/id/verse-luxe-wahid-hasyim.html#tab-reviews",
        "traveloka": "https://www.traveloka.com/id-id/hotel/indonesia/verse-luxe-hotel-wahid-hasyim-3000010036666",
        "tripcom": "https://id.trip.com/hotels/central-jakarta-city-hotel-detail-9029304/verse-luxe-hotel-wahid-hasyim/",
        "tiket": "https://www.tiket.com/id-id/hotel/indonesia/verse-luxe-hotel-wahid-hasyim-112001545304320268"
    },
    "Verse Cirebon": {
        "agoda": "https://www.agoda.com/verse-hotel-cirebon/reviews/cirebon-id.html",
        "booking": "https://www.booking.com/hotel/id/verse-cirebon.html#tab-reviews",
        "traveloka": "https://www.traveloka.com/id-id/hotel/indonesia/verse-hotel-cirebon-3000010015654",
        "tripcom": "https://id.trip.com/hotels/kedawung-hotel-detail-5965336/verse-hotel-cirebon/",
        "tiket": "https://www.tiket.com/id-id/hotel/indonesia/verse-hotel-cirebon-108001534490349528"
    },
    "Oak Tree Mahakam Blok M": {
        "agoda": "https://www.agoda.com/oak-tree-urban-hotel/reviews/jakarta-id.html",
        "booking": "https://www.booking.com/hotel/id/oak-tree-urban.html#tab-reviews",
        "traveloka": "https://www.traveloka.com/id-id/hotel/indonesia/oak-tree-urban-hotel-jakarta-461895",
        "tripcom": "https://id.trip.com/hotels/south-jakarta-city-hotel-detail-2652976/oak-tree-urban-hotel-jakarta/",
        "tiket": "https://www.tiket.com/id-id/hotel/indonesia/oak-tree-urban-jakarta-412001639976768183"
    }
}

PLATFORM_SCOPE = ["agoda", "booking", "traveloka", "tripcom", "tiket"]


def log_error(hotel_name, platform_name, message):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now()} | {hotel_name} | {platform_name} | {message}\n")
    except Exception:
        pass


<<<<<<< HEAD
# ============================================================
# v3.2 — Debug logging untuk Tiket
# ============================================================
def debug_dump_tiket(hotel_name, url, raw_text, html_snippet=None):
    """
    Dump teks yang didapat Playwright dari Tiket ke file debug.
    Akan dipakai untuk analisa: apakah halaman blocked / kosong / format beda.
    """
    try:
        with open(DEBUG_TIKET_FILE, "a", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(f"TIMESTAMP: {datetime.now()}\n")
            f.write(f"HOTEL: {hotel_name}\n")
            f.write(f"URL: {url}\n")
            f.write(f"TEXT LENGTH: {len(raw_text) if raw_text else 0}\n")
            f.write("-" * 80 + "\n")
            f.write("RAW TEXT (first 3000 chars):\n")
            f.write(raw_text[:3000] if raw_text else "(EMPTY)")
            f.write("\n" + "-" * 80 + "\n")
            f.write("RAW TEXT (last 1500 chars):\n")
            if raw_text and len(raw_text) > 3000:
                f.write(raw_text[-1500:])
            f.write("\n" + "-" * 80 + "\n")
            
            # Cari semua angka format X,Y atau X.Y di teks
            if raw_text:
                rating_candidates = re.findall(r"\b\d[.,]\d\b", raw_text)
                f.write(f"ALL RATING CANDIDATES (X.Y / X,Y): {rating_candidates[:30]}\n")
                
                # Cari kata kunci penting
                keywords = ["Sangat Bagus", "Mengesankan", "Luar Biasa", "Menyenangkan",
                           "ulasan", "review", "rating", "Excellent", "Very Good",
                           "blocked", "Access Denied", "denied", "captcha", "robot",
                           "Cloudflare", "DataDome", "403", "Forbidden"]
                f.write("KEYWORD FOUND:\n")
                for kw in keywords:
                    count = len(re.findall(re.escape(kw), raw_text, re.IGNORECASE))
                    if count > 0:
                        f.write(f"  - '{kw}': {count}x\n")
            
            if html_snippet:
                f.write("\n" + "-" * 80 + "\n")
                f.write("HTML SNIPPET (first 2000 chars):\n")
                f.write(html_snippet[:2000])
            
            f.write("\n" + "=" * 80 + "\n\n")
    except Exception as e:
        print(f"     debug dump failed: {e}")
=======
def debug_write(path, hotel_name, url, text, html=""):
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(f"TIME: {datetime.now()}\n")
            f.write(f"HOTEL: {hotel_name}\n")
            f.write(f"URL: {url}\n")
            f.write(f"TEXT LENGTH: {len(text or '')}\n")
            f.write("-" * 80 + "\n")
            f.write((text or "(EMPTY)")[:7000])
            f.write("\n" + "-" * 80 + "\n")
            if html:
                f.write("HTML SNIPPET:\n")
                f.write(html[:2500])
            f.write("\n\n")
    except Exception:
        pass
>>>>>>> 65709b9 (fix final scraper v7 all platforms auto)


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
    return re.sub(r"\s+", " ", str(text)).strip()


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
    has_fresh = fresh_data.get("rating") != "N/A" and fresh_data.get("reviews") != "N/A"
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
        log_error(hotel_name, platform_name, f"CACHED_USED: {error_reason}")
        return make_result(
            rating=cached.get("rating", "N/A"),
            reviews=cached.get("reviews", "N/A"),
            ranking=cached.get("ranking"),
            status="CACHED",
            source_date=cached.get("source_date"),
            error_reason=error_reason
        )

    log_error(hotel_name, platform_name, f"ERROR_NO_CACHE: {error_reason}")
    return make_result(
        rating="N/A",
        reviews="N/A",
        ranking=None,
        status="ERROR",
        source_date=None,
        error_reason=error_reason or "selector_mismatch"
    )


def save_history_snapshot(history, hotels_data):
    today = datetime.now().strftime("%Y-%m-%d")
    snapshot = {"date": today, "hotels": hotels_data}

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
                    rating_change = round(float(current_values["rating"]) - float(start_values["rating"]), 1)
                except Exception:
                    rating_change = None

                try:
                    review_change = int(str(current_values["reviews"])) - int(str(start_values["reviews"]))
                except Exception:
                    review_change = None

            hotel["comparison"]["platforms"][platform_name] = {
                "rating_change": rating_change,
                "review_change": review_change,
                "ranking_change": ranking_change
            }

        final_hotels.append(hotel)

    return final_hotels


<<<<<<< HEAD
def is_network_error(exc):
    err_str = str(exc)
    return any(pattern in err_str for pattern in NETWORK_ERROR_PATTERNS)


def safe_goto(page, url, timeout=60000, wait_until="domcontentloaded"):
=======
def safe_goto(page, url, timeout=80000, wait_until="domcontentloaded"):
>>>>>>> 65709b9 (fix final scraper v7 all platforms auto)
    last_error = None
    for attempt in range(1, MAX_RETRY + 1):
        try:
            page.goto(url, timeout=timeout, wait_until=wait_until)
            return True
        except Exception as e:
            last_error = e
<<<<<<< HEAD
            if attempt >= MAX_RETRY:
                break

            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]

            if is_network_error(e):
                delay = delay * 2
                print(f"        ⚠ network error, retrying in {delay}s (attempt {attempt + 1}/{MAX_RETRY})")
            else:
                print(f"        ⚠ retry in {delay}s (attempt {attempt + 1}/{MAX_RETRY})")

            time.sleep(delay)

=======
            time.sleep(RETRY_DELAY_SECONDS * attempt)
>>>>>>> 65709b9 (fix final scraper v7 all platforms auto)
    raise last_error


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

    rating_match = re.search(r"\b(\d[.,]\d)\b", text)
    if rating_match:
        rating = clean_rating(rating_match.group(1))

    review_match = re.search(r"([\d,\.]+)\s+reviews", text, re.IGNORECASE)
    if review_match:
        reviews = clean_number(review_match.group(1))

    ok = is_valid_rating(rating, 1, 10) and is_valid_reviews(reviews, 1)
    return {
        "rating": rating if ok else "N/A",
        "reviews": reviews if ok else "N/A",
        "ranking": None,
        "match_ok": ok,
        "error_reason": None if ok else "agoda_pattern_not_found"
    }


def parse_booking(text):
    rating = "N/A"
    reviews = "N/A"

    rating_patterns = [
        r"Scored\s+(\d[.,]\d)",
        r"\b(\d[.,]\d)\s*/\s*10\b",
        r"\b(\d[.,]\d)\s*(?:Very good|Wonderful|Exceptional|Good|Pleasant|Fair|Fabulous|Superb|Baik|Menyenangkan|Istimewa|Sangat baik|Luar biasa)",
    ]

    for pattern in rating_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = clean_rating(match.group(1))
            if is_valid_rating(candidate, 1, 10):
                rating = candidate
                break

    review_patterns = [
        r"([\d,\.]+)\s+reviews",
        r"([\d,\.]+)\s+review",
        r"([\d,\.]+)\s+ulasan",
        r"based on\s+([\d,\.]+)",
        r"from\s+([\d,\.]+)\s+reviews",
    ]

    for pattern in review_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = clean_number(match.group(1))
            if is_valid_reviews(candidate, 5):
                reviews = candidate
                break

    ok = is_valid_rating(rating, 1, 10) and is_valid_reviews(reviews, 5)
    return {
        "rating": rating if ok else "N/A",
        "reviews": reviews if ok else "N/A",
        "ranking": None,
        "match_ok": ok,
        "error_reason": None if ok else "booking_pattern_not_found"
    }


def parse_tripcom(text):
    rating = "N/A"
    reviews = "N/A"

    focused_text = text

    focus_markers = [
        "Ulasan Tamu",
        "Ulasan tamu",
        "Guest Reviews",
        "Guest reviews",
        "Hotel Reviews",
        "Reviews",
        "review.html"
    ]

    focus_slices = []
    for marker in focus_markers:
        idx = focused_text.lower().find(marker.lower())
        if idx >= 0:
            focus_slices.append(focused_text[idx:idx + 2200])

    focus_slices.append(focused_text[:5000])

    strict_patterns = [
        r"(?:Ulasan\s+Tamu|Guest\s+Reviews?|Hotel\s+Reviews?|Reviews?)\D{0,300}(\d[.,]\d)\s*/\s*10\D{0,600}([\d,\.]+)\s+(?:ulasan|reviews?)",
        r"(\d[.,]\d)\s*/\s*10\D{0,500}([\d,\.]+)\s+(?:ulasan|reviews?)",
        r"(\d[.,]\d)\s+(?:Luar\s+Biasa|Sangat\s+Baik|Mengesankan|Baik|Excellent|Very\s+Good|Wonderful|Good|Fabulous|Superb)\D{0,500}([\d,\.]+)\s+(?:ulasan|reviews?)",
    ]

    for chunk in focus_slices:
        for pattern in strict_patterns:
            match = re.search(pattern, chunk, re.IGNORECASE | re.DOTALL)
            if match:
                candidate_rating = clean_rating(match.group(1))
                candidate_reviews = clean_number(match.group(2))

                # Trip.com hotel score should be on 10-scale and normally not below 6 for these hotels.
                # This prevents random numbers such as 1.9 / 3.5 / 4.8 from page distance/location blocks.
                if is_valid_rating(candidate_rating, 6, 10) and is_valid_reviews(candidate_reviews, 5):
                    rating = candidate_rating
                    reviews = candidate_reviews
                    break
        if rating != "N/A":
            break

    if rating == "N/A" or reviews == "N/A":
        # Fallback: find all /10 candidates, choose the first realistic hotel score.
        rating_candidates = []
        for m in re.finditer(r"\b(\d[.,]\d)\s*/\s*10\b", focused_text, re.IGNORECASE):
            candidate = clean_rating(m.group(1))
            if is_valid_rating(candidate, 6, 10):
                rating_candidates.append((m.start(), candidate))

        review_candidates = []
        for m in re.finditer(r"\b([\d,\.]+)\s+(?:ulasan|reviews?)\b", focused_text, re.IGNORECASE):
            candidate = clean_number(m.group(1))
            if is_valid_reviews(candidate, 5):
                review_candidates.append((m.start(), candidate))

        best_pair = None
        best_distance = None
        for rs, rv in rating_candidates:
            for vs, vv in review_candidates:
                dist = abs(vs - rs)
                if dist < 900:
                    if best_distance is None or dist < best_distance:
                        best_distance = dist
                        best_pair = (rv, vv)

        if best_pair:
            rating, reviews = best_pair

    ok = is_valid_rating(rating, 6, 10) and is_valid_reviews(reviews, 5)
    return {
        "rating": rating if ok else "N/A",
        "reviews": reviews if ok else "N/A",
        "ranking": None,
        "match_ok": ok,
        "error_reason": None if ok else "tripcom_pattern_not_found"
    }


def parse_tiket(text):
    if re.search(r"Robot atau manusia|Centang kotak|Ray ID|captcha|Cloudflare|Access Denied|Forbidden", text, re.IGNORECASE):
        return {
            "rating": "N/A",
            "reviews": "N/A",
            "ranking": None,
            "match_ok": False,
            "error_reason": "tiket_bot_challenge"
        }

    rating = "N/A"
    reviews = "N/A"

    combined_patterns = [
        r"Review\s+Lihat\s+semua\s+(\d[.,]\d)\s*/\s*5.*?Dari\s+([\d,\.]+)\s+review",
        r"(\d[.,]\d)\s*/\s*5\s*(?:Bagus|Sangat\s+Bagus|Luar\s+Biasa|Mengesankan|Menyenangkan|Memuaskan)?\s*Dari\s+([\d,\.]+)\s+review",
        r"(\d[.,]\d)\s*/\s*5.*?Dari\s+([\d,\.]+)\s+review",
        r"(\d[.,]\d)\s*/\s*5.*?([\d,\.]+)\s+review",
        r"(\d[.,]\d)\s*/\s*5.*?([\d,\.]+)\s+ulasan",
    ]

    for pattern in combined_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            candidate_rating = clean_rating(match.group(1))
            candidate_reviews = clean_number(match.group(2))
            if is_valid_rating(candidate_rating, 1, 5) and is_valid_reviews(candidate_reviews, 10):
                rating = candidate_rating
                reviews = candidate_reviews
                break

    if rating == "N/A":
        rating_patterns = [
            r"\b(\d[.,]\d)\s*/\s*5\b",
            r"\b(\d[.,]\d)\s+(?:Bagus|Sangat\s+Bagus|Luar\s+Biasa|Mengesankan|Menyenangkan|Memuaskan|Cukup\s+Bagus)\b",
            r'"ratingValue"\s*:\s*"?(\d+(?:[.,]\d+)?)"?',
        ]
        for pattern in rating_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                candidate = clean_rating(match.group(1))
                if is_valid_rating(candidate, 1, 5):
                    rating = candidate
                    break

    if reviews == "N/A":
        review_patterns = [
            r"\bDari\s+([\d,\.]+)\s+review\b",
            r"\bDari\s+([\d,\.]+)\s+ulasan\b",
            r"\b([\d,\.]+)\s+review\b",
            r"\b([\d,\.]+)\s+ulasan\b",
            r'"reviewCount"\s*:\s*"?(\d+)"?',
        ]
        for pattern in review_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                candidate = clean_number(match.group(1))
                if is_valid_reviews(candidate, 10):
                    reviews = candidate
                    break

    ok = is_valid_rating(rating, 1, 5) and is_valid_reviews(reviews, 10)
    return {
        "rating": rating if ok else "N/A",
        "reviews": reviews if ok else "N/A",
        "ranking": None,
        "match_ok": ok,
        "error_reason": None if ok else "tiket_pattern_not_found"
    }


def traveloka_extract_from_text(text):
    rating = "N/A"
    reviews = "N/A"

    rating_patterns = [
        r"\b(\d[.,]\d)\s*/\s*10\b",
<<<<<<< HEAD
        r"\b(\d[.,]\d)\s+(?:Sangat\s+Bagus|Luar\s+Biasa|Mengesankan|Menyenangkan|Bagus|Memuaskan|Cukup\s+Bagus)\b",
        r"\b(\d[.,]\d)\s+(?:Excellent|Very\s+Good|Wonderful|Pleasant|Good|Fabulous|Superb)\b",
        r'"aggregateRating"[^}]*?"ratingValue"\s*:\s*"?(\d+(?:[.,]\d+)?)"?',
        r'"ratingValue"\s*:\s*"?(\d+(?:[.,]\d+)?)"?',
        r'"rating"\s*:\s*"?(\d[.,]\d)"?',
        r'"score"\s*:\s*"?(\d[.,]\d)"?',
        r'"reviewScore"\s*:\s*"?(\d[.,]\d)"?',
        r"\b(\d[.,]\d)\s*/\s*5\b",
        r"[Rr]ating[:\s]+(\d[.,]\d)",
        r"(?:Sangat\s+Bagus|Luar\s+Biasa|Mengesankan|Menyenangkan)\s+(\d[.,]\d)\b",
=======
        r"\b(\d[.,]\d)\s+(?:Sangat\s+Bagus|Luar\s+Biasa|Mengesankan|Menyenangkan|Bagus|Memuaskan)\b",
        r'"aggregateRating"[^}]*?"ratingValue"\s*:\s*"?(\d+(?:[.,]\d+)?)"?',
        r'"ratingValue"\s*:\s*"?(\d+(?:[.,]\d+)?)"?',
>>>>>>> 65709b9 (fix final scraper v7 all platforms auto)
    ]

    for pattern in rating_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = clean_rating(match.group(1))
            if is_valid_rating(candidate, 5, 10):
                rating = candidate
                break

    review_patterns = [
<<<<<<< HEAD
        r"\(([\d,\.]+)\s+ulasan\)",
        r"\b([\d,\.]+)\s+ulasan\b",
        r"\bdari\s+([\d,\.]+)\s+ulasan\b",
        r"\bberdasarkan\s+([\d,\.]+)\s+ulasan\b",
        r"\(([\d,\.]+)\s+reviews?\)",
        r"\b([\d,\.]+)\s+reviews?\b",
        r"\bfrom\s+([\d,\.]+)\s+reviews?\b",
        r"\bbased\s+on\s+([\d,\.]+)\s+reviews?\b",
        r'"reviewCount"\s*:\s*"?(\d+)"?',
        r'"ratingCount"\s*:\s*"?(\d+)"?',
        r'"totalReviews"\s*:\s*"?(\d+)"?',
        r"\b([\d,\.]+)\s+review\b",
=======
        r"\bDari\s+([\d,\.]+)\s+(?:ulasan|review|reviews)\b",
        r"\b([\d,\.]+)\s+ulasan\b",
        r"\b([\d,\.]+)\s+reviews?\b",
        r'"reviewCount"\s*:\s*"?(\d+)"?',
        r'"ratingCount"\s*:\s*"?(\d+)"?',
        r'"totalReviews"\s*:\s*"?(\d+)"?',
>>>>>>> 65709b9 (fix final scraper v7 all platforms auto)
    ]

    review_candidates = []
    for pattern in review_patterns:
<<<<<<< HEAD
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = clean_number(match.group(1))
            if is_valid_reviews(candidate, 10):
                reviews = candidate
                break

    if rating != "N/A":
        try:
            val = float(rating)
            if not (1.0 <= val <= 10.0):
                rating = "N/A"
        except (ValueError, TypeError):
            rating = "N/A"

    if not is_valid_reviews(reviews, 10):
        reviews = "N/A"

    match_ok = (rating != "N/A" and reviews != "N/A")
=======
        for match in re.finditer(pattern, text, re.IGNORECASE):
            candidate = clean_number(match.group(1))
            if is_valid_reviews(candidate, 50):
                try:
                    review_candidates.append(int(candidate))
                except Exception:
                    pass

    if review_candidates:
        reviews = str(max(review_candidates))
>>>>>>> 65709b9 (fix final scraper v7 all platforms auto)

    ok = is_valid_rating(rating, 5, 10) and is_valid_reviews(reviews, 50)
    return {
        "rating": rating if ok else "N/A",
        "reviews": reviews if ok else "N/A",
        "ranking": None,
        "match_ok": ok,
        "error_reason": None if ok else "traveloka_strong_pattern_not_found"
    }
<<<<<<< HEAD


def traveloka_extract_from_text(text):
    rating = "N/A"
    reviews = "N/A"

    rating_patterns = [
        r"\b(\d[.,]\d)\s*/\s*10\b",
        r"\b(\d[.,]\d)\s+(?:Sangat\s+Bagus|Luar\s+Biasa|Mengesankan|Menyenangkan|Bagus|Memuaskan)\b",
        r"\b(\d[.,]\d)\s+(?:Excellent|Very\s+Good|Wonderful|Pleasant|Good|Fabulous|Superb)\b",
        r'"aggregateRating"[^}]*?"ratingValue"\s*:\s*"?(\d+(?:[.,]\d+)?)"?',
        r'"ratingValue"\s*:\s*"?(\d+(?:[.,]\d+)?)"?',
        r'"rating"\s*:\s*"?(\d[.,]\d)"?',
        r'"score"\s*:\s*"?(\d[.,]\d)"?',
        r'"reviewScore"\s*:\s*"?(\d[.,]\d)"?',
        r"\b(\d[.,]\d)\s+dari\s+10\b",
        r"(?:Sangat\s+Bagus|Luar\s+Biasa|Mengesankan|Menyenangkan)\s+(\d[.,]\d)\b",
    ]

    review_patterns = [
        r"\(([\d,\.]+)\s+ulasan\)",
        r"\bDari\s+([\d,\.]+)\s+(?:ulasan|review|reviews)\b",
        r"\b([\d,\.]+)\s+ulasan\b",
        r"\b([\d,\.]+)\s+reviews?\b",
        r"\bdari\s+([\d,\.]+)\s+ulasan\b",
        r"\bbased\s+on\s+([\d,\.]+)\s+reviews?\b",
        r'"reviewCount"\s*:\s*"?(\d+)"?',
        r'"ratingCount"\s*:\s*"?(\d+)"?',
        r'"totalReviews"\s*:\s*"?(\d+)"?',
        r"([\d\.,]+)\s+(?:ulasan|review|reviews)\b",
    ]

    primary_rating = None
    for pattern in rating_patterns[:4]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = clean_rating(match.group(1))
            if is_valid_rating(candidate, 5, 10):
                primary_rating = candidate
                break

    if primary_rating:
        rating = primary_rating
        all_review_counts = []
        for pattern in review_patterns:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                candidate = clean_number(m.group(1))
                if is_valid_reviews(candidate, 50):
                    try:
                        all_review_counts.append(int(candidate))
                    except (ValueError, TypeError):
                        pass

        if all_review_counts:
            reviews = str(max(all_review_counts))
    else:
        rating_matches = []
        for pat in rating_patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                rating_matches.append(m)

        review_matches = []
        for pat in review_patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                review_matches.append(m)

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

    match_ok = (rating != "N/A" and reviews != "N/A")

    return {
        "rating": rating,
        "reviews": reviews,
        "ranking": None,
        "match_ok": match_ok,
        "error_reason": None if match_ok else "traveloka_strong_pattern_not_found"
    }


=======


>>>>>>> 65709b9 (fix final scraper v7 all platforms auto)
def collect_traveloka_text(page):
    collected = []

    def grab(wait_ms=1500):
        try:
            page.wait_for_timeout(wait_ms)
            text = get_page_text(page, 1000)
            if text:
                collected.append(text)
        except Exception:
            pass

    grab(3000)

    for pos in [500, 1000, 1500, 2200, 3000, 3800, 4600, 5600]:
        try:
            page.evaluate(f"window.scrollTo(0, {pos})")
            grab(1800)
        except Exception:
            pass

    try:
        html = page.content()
        plain = re.sub(r"<[^>]+>", " ", html)
        collected.append(normalize_text(plain))
    except Exception:
        pass

    return normalize_text(" ".join(collected))


def fetch_traveloka(playwright, url):
    browser = None
    context = None
    try:
        browser = playwright.chromium.launch(headless=True, args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-extensions"
        ])
        context = browser.new_context(
            locale="id-ID",
            viewport={"width": 1440, "height": 1200},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.set_extra_http_headers({"Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7"})

        last = None
        for _ in range(MAX_RETRY):
            safe_goto(page, url, timeout=90000)
            page.wait_for_timeout(8000)
            text = collect_traveloka_text(page)
            result = traveloka_extract_from_text(text)
            last = result
            if result.get("match_ok"):
                return result
            time.sleep(10)

<<<<<<< HEAD
        for attempt in range(1, MAX_RETRY + 1):
            try:
                safe_goto(page, url, timeout=90000, wait_until="domcontentloaded")
                page.wait_for_timeout(8000)

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
                        page.wait_for_timeout(800)
                    except Exception:
                        pass

                text = collect_traveloka_text(page)
                result = traveloka_extract_from_text(text)
                last_result = result

                if result.get("match_ok"):
                    return result

                time.sleep(15)

            except Exception as e:
                last_result = {
                    "rating": "N/A",
                    "reviews": "N/A",
                    "ranking": None,
                    "match_ok": False,
                    "error_reason": f"traveloka_attempt_failed: {str(e)[:120]}"
                }
                time.sleep(15)

        return last_result or {
=======
        return last or {
>>>>>>> 65709b9 (fix final scraper v7 all platforms auto)
            "rating": "N/A",
            "reviews": "N/A",
            "ranking": None,
            "match_ok": False,
            "error_reason": "traveloka_failed"
        }

    except Exception as e:
        return {
            "rating": "N/A",
            "reviews": "N/A",
            "ranking": None,
            "match_ok": False,
            "error_reason": f"traveloka_error: {str(e)[:80]}"
        }
    finally:
        try:
            if context:
                context.close()
            if browser:
                browser.close()
        except Exception:
            pass


def scrape_standard_platform(page, url, parser_func, hotel_name, platform_name, wait_ms=7000):
    last_error = None
    last_text = ""
<<<<<<< HEAD
    last_html = None
=======
    last_html = ""
>>>>>>> 65709b9 (fix final scraper v7 all platforms auto)

    for _ in range(MAX_RETRY):
        try:
            safe_goto(page, url, timeout=80000)
            text = get_page_text(page, wait_ms)
            last_text = text
<<<<<<< HEAD
            
            # v3.2: capture HTML untuk debug Tiket
            if platform_name == "tiket":
                try:
                    last_html = page.content()
                except Exception:
                    pass
            
=======

            try:
                last_html = page.content()
            except Exception:
                last_html = ""

            if platform_name == "tiket":
                debug_write(DEBUG_TIKET_FILE, hotel_name, url, text, last_html)

            if platform_name == "tripcom":
                debug_write(DEBUG_TRIP_FILE, hotel_name, url, text, last_html)

>>>>>>> 65709b9 (fix final scraper v7 all platforms auto)
            result = parser_func(text)

            if result.get("match_ok"):
                # v3.2: dump debug walaupun sukses (untuk reference)
                if platform_name == "tiket":
                    debug_dump_tiket(hotel_name, url, text, last_html)
                return result

            last_error = result.get("error_reason", "pattern_not_found")
<<<<<<< HEAD
            time.sleep(15)

        except Exception as e:
            last_error = str(e)
            time.sleep(15)

    # v3.2: dump debug saat gagal (ini yang penting!)
    if platform_name == "tiket":
        debug_dump_tiket(hotel_name, url, last_text, last_html)
=======
            time.sleep(10)

        except Exception as e:
            last_error = str(e)
            time.sleep(10)

    if platform_name == "tiket":
        debug_write(DEBUG_TIKET_FILE, hotel_name, url, last_text, last_html)

    if platform_name == "tripcom":
        debug_write(DEBUG_TRIP_FILE, hotel_name, url, last_text, last_html)
>>>>>>> 65709b9 (fix final scraper v7 all platforms auto)

    log_error(hotel_name, platform_name, last_error)
    return {
        "rating": "N/A",
        "reviews": "N/A",
        "ranking": None,
        "match_ok": False,
        "error_reason": last_error or "scrape_failed"
    }


def main():
<<<<<<< HEAD
    # v3.2: clear debug file di awal run supaya hanya berisi run terbaru
    try:
        with open(DEBUG_TIKET_FILE, "w", encoding="utf-8") as f:
            f.write(f"# DEBUG TIKET LOG — Run started at {datetime.now()}\n\n")
    except Exception:
        pass
=======
    for file in [DEBUG_TIKET_FILE, DEBUG_TRIP_FILE]:
        try:
            with open(file, "w", encoding="utf-8") as f:
                f.write(f"# DEBUG LOG — {datetime.now()}\n\n")
        except Exception:
            pass
>>>>>>> 65709b9 (fix final scraper v7 all platforms auto)

    previous_data = load_current_data()
    hotels_today = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-gpu"
        ])

        context = browser.new_context(
            locale="en-US",
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )

        page = context.new_page()
        page.set_extra_http_headers({"Accept-Language": "en-US,en;q=0.9,id-ID;q=0.8,id;q=0.7"})

        for hotel_name, sources in HOTELS.items():
            print("Hotel:", hotel_name)
<<<<<<< HEAD

            if hotel_index > 0:
                time.sleep(3)

            hotel_record = {"name": hotel_name, "platforms": {}}
            consecutive_failures = 0
=======
            hotel_record = {"name": hotel_name, "platforms": {}}
>>>>>>> 65709b9 (fix final scraper v7 all platforms auto)

            platform_jobs = [
                ("agoda", parse_agoda, 6000),
                ("booking", parse_booking, 9000),
                ("tripcom", parse_tripcom, 12000),
                ("tiket", parse_tiket, 12000),
            ]

            for platform_name, parser_func, wait_ms in platform_jobs:
                print("  " + platform_name)

                fresh = scrape_standard_platform(
                    page=page,
                    url=sources[platform_name],
                    parser_func=parser_func,
                    hotel_name=hotel_name,
                    platform_name=platform_name,
                    wait_ms=wait_ms
                )

                parsed = finalize_platform_result(hotel_name, platform_name, fresh, previous_data)

<<<<<<< HEAD
                if parsed["status"] == "ERROR":
                    consecutive_failures += 1

                    if consecutive_failures >= HOTEL_FAILURE_THRESHOLD:
                        print(f"     ⚠ {consecutive_failures} consecutive failures detected")
                        print(f"     ⏸ cooling down {HOTEL_COOLDOWN_SECONDS}s for network recovery...")
                        time.sleep(HOTEL_COOLDOWN_SECONDS)
                        consecutive_failures = 0
                else:
                    consecutive_failures = 0

=======
>>>>>>> 65709b9 (fix final scraper v7 all platforms auto)
                print("     rating:", parsed["rating"])
                print("     reviews:", parsed["reviews"])
                print("     status:", parsed["status"])
                if parsed.get("error_reason"):
                    print("     error:", parsed["error_reason"])

                hotel_record["platforms"][platform_name] = parsed

            print("  traveloka")
            fresh = fetch_traveloka(p, sources["traveloka"])
            parsed = finalize_platform_result(hotel_name, "traveloka", fresh, previous_data)

            print("     rating:", parsed["rating"])
            print("     reviews:", parsed["reviews"])
            print("     status:", parsed["status"])
            if parsed.get("error_reason"):
                print("     error:", parsed["error_reason"])

            hotel_record["platforms"]["traveloka"] = parsed
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
