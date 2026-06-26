from playwright.sync_api import sync_playwright
import json
import re
import os
import time
import random
import urllib.request
import urllib.error
from datetime import datetime

DATA_FILE = "data.json"
HISTORY_FILE = "history.json"
LOG_FILE = "error_log.txt"
DEBUG_TIKET_FILE = "debug_tiket.txt"
DEBUG_TRIP_FILE = "debug_trip.txt"

MAX_RETRY = 3
RETRY_DELAY_SECONDS = 6

HOTELS = {
    "Verse Lite Gajah Mada": {
        "agoda": "https://www.agoda.com/verse-lite-hotel-gajah-mada/hotel/jakarta-id.html",
        "booking": "https://www.booking.com/hotel/id/verse-lite-pembangunan.html",
        "traveloka": "https://www.traveloka.com/id-id/hotel/indonesia/verse-lite-hotel-gajah-mada-3000010028056",
        "tripcom": "https://id.trip.com/hotels/central-jakarta-city-hotel-detail-6449572/verse-lite-hotel-gajah-mada/",
        "tiket": "https://www.tiket.com/hotel/indonesia/verse-lite-hotel-gajah-mada-807001751612826254"
    },
    "Verse Luxe Wahid Hasyim": {
        "agoda": "https://www.agoda.com/verse-luxe-hotel-wahid-hasyim/hotel/jakarta-id.html",
        "booking": "https://www.booking.com/hotel/id/verse-luxe-wahid-hasyim.html",
        "traveloka": "https://www.traveloka.com/id-id/hotel/indonesia/verse-luxe-hotel-wahid-hasyim-3000010036666",
        "tripcom": "https://id.trip.com/hotels/central-jakarta-city-hotel-detail-9029304/verse-luxe-hotel-wahid-hasyim/",
        "tiket": "https://www.tiket.com/hotel/indonesia/verse-luxe-hotel-wahid-hasyim-112001545304320268"
    },
    "Verse Cirebon": {
        "agoda": "https://www.agoda.com/verse-hotel-cirebon/hotel/cirebon-id.html",
        "booking": "https://www.booking.com/hotel/id/verse-cirebon.html",
        "traveloka": "https://www.traveloka.com/id-id/hotel/indonesia/verse-hotel-cirebon-3000010015654",
        "tripcom": "https://id.trip.com/hotels/kedawung-hotel-detail-5965336/verse-hotel-cirebon/",
        "tiket": "https://www.tiket.com/hotel/indonesia/verse-hotel-cirebon-108001534490349528"
    },
    "Oak Tree Mahakam Blok M": {
        "agoda": "https://www.agoda.com/oak-tree-urban-hotel/hotel/jakarta-id.html",
        "booking": "https://www.booking.com/hotel/id/oak-tree-urban.html",
        "traveloka": "https://www.traveloka.com/id-id/hotel/indonesia/oak-tree-urban-hotel-jakarta-461895",
        "tripcom": "https://id.trip.com/hotels/south-jakarta-city-hotel-detail-2652976/oak-tree-urban-hotel-jakarta/",
        "tiket": "https://www.tiket.com/hotel/indonesia/oak-tree-urban-jakarta-412001639976768183"
    }
}

PLATFORM_SCOPE = ["agoda", "booking", "traveloka", "tripcom", "tiket"]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


def log_error(hotel_name, platform_name, message):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now()} | {hotel_name} | {platform_name} | {message}\n")
    except Exception:
        pass


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
                "ranking_change": None
            }

        final_hotels.append(hotel)

    return final_hotels


def safe_goto(page, url, timeout=80000, wait_until="domcontentloaded"):
    last_error = None
    for attempt in range(1, MAX_RETRY + 1):
        try:
            page.goto(url, timeout=timeout, wait_until=wait_until)
            return True
        except Exception as e:
            last_error = e
            time.sleep(RETRY_DELAY_SECONDS * attempt)
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


def http_get(url, extra_headers=None):
    """HTTP GET sederhana dengan urllib — tidak butuh browser."""
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    }
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        # Handle gzip
        try:
            import gzip
            raw = gzip.decompress(raw)
        except Exception:
            pass
        return raw.decode("utf-8", errors="replace")


# ─────────────────────────────────────────────
# PARSER: AGODA
# ─────────────────────────────────────────────
def parse_agoda(text):
    rating = "N/A"
    reviews = "N/A"

    # Agoda format: "8.6 Exceptional 4,979 reviews"
    # Review count harus realistis (min 50) untuk hindari false positive
    combined_patterns = [
        r"(\d[.,]\d)\s+(?:Exceptional|Fabulous|Superb|Very Good|Good|Pleasant|Fair|Luar Biasa|Sangat Baik|Mengesankan|Bagus|Menyenangkan|Memuaskan)\s+([\d,\.]+)\s+reviews?",
        r"(\d[.,]\d)\s*/?\s*10\b.{0,300}?([\d,\.]+)\s+reviews?",
        r"([\d,\.]+)\s+reviews?.{0,300}?(\d[.,]\d)\s*/?\s*10\b",
    ]
    for pattern in combined_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            r1, r2 = clean_rating(match.group(1)), clean_number(match.group(2))
            # Minimum 50 reviews untuk hindari false positive
            if is_valid_rating(r1, 5, 10) and is_valid_reviews(r2, 50):
                rating, reviews = r1, r2
                break
            # Coba terbalik
            r1b, r2b = clean_rating(match.group(2)), clean_number(match.group(1))
            if is_valid_rating(r1b, 5, 10) and is_valid_reviews(r2b, 50):
                rating, reviews = r1b, r2b
                break

    # Fallback: scan semua "X reviews" dengan minimum 50
    if reviews == "N/A":
        candidates = []
        for m in re.finditer(r"([\d,\.]+)\s+reviews?", text, re.IGNORECASE):
            c = clean_number(m.group(1))
            if is_valid_reviews(c, 50):
                try:
                    candidates.append(int(c))
                except Exception:
                    pass
        if candidates:
            reviews = str(max(candidates))

    # Fallback rating
    if rating == "N/A":
        for m in re.finditer(r"\b(\d[.,]\d)\b", text):
            c = clean_rating(m.group(1))
            if is_valid_rating(c, 5, 10):
                rating = c
                break

    ok = is_valid_rating(rating, 5, 10) and is_valid_reviews(reviews, 50)
    return {
        "rating": rating if ok else "N/A",
        "reviews": reviews if ok else "N/A",
        "ranking": None,
        "match_ok": ok,
        "error_reason": None if ok else "agoda_pattern_not_found"
    }


def fetch_agoda(url, hotel_name, playwright=None):
    """
    Agoda: butuh JavaScript render — gunakan Playwright.
    HTTP request biasa hanya dapat navigasi, tidak ada rating/review.
    """
    if playwright is None:
        return {
            "rating": "N/A", "reviews": "N/A", "ranking": None,
            "match_ok": False, "error_reason": "agoda_no_playwright"
        }

    browser = None
    context = None
    try:
        browser = playwright.chromium.launch(headless=True, args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-gpu",
        ])
        context = browser.new_context(
            locale="id-ID",
            viewport={"width": 1366, "height": 768},
            user_agent=random.choice(USER_AGENTS),
        )
        page = context.new_page()
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'languages', {get: () => ['id-ID','id','en-US','en']});
            window.chrome = {runtime: {}};
        """)
        page.set_extra_http_headers({
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8",
        })

        for attempt in range(1, MAX_RETRY + 1):
            try:
                safe_goto(page, url, timeout=80000)
                # Agoda butuh waktu untuk load rating via AJAX
                page.wait_for_timeout(10000)

                # Scroll untuk trigger lazy load
                for pos in [500, 1000, 1500]:
                    page.evaluate(f"window.scrollTo(0, {pos})")
                    page.wait_for_timeout(1500)

                text = get_page_text(page, 2000)
                try:
                    html = page.content()
                except Exception:
                    html = ""

                result = parse_agoda(text + " " + html)
                # Debug: tulis teks yang diterima Agoda
                debug_write(DEBUG_TRIP_FILE, hotel_name + "_AGODA", url, text[:3000], html[:1000])
                if result.get("match_ok"):
                    print(f"    [agoda] Berhasil attempt {attempt}: rating={result['rating']}, reviews={result['reviews']}")
                    return result

                print(f"    [agoda] Pattern tidak match attempt {attempt}, text_len={len(text)}")
                time.sleep(8)

            except Exception as e:
                log_error(hotel_name, "agoda", f"attempt_{attempt}: {str(e)[:80]}")
                time.sleep(8)

    except Exception as e:
        log_error(hotel_name, "agoda", f"browser_error: {str(e)[:80]}")
    finally:
        try:
            if context:
                context.close()
            if browser:
                browser.close()
        except Exception:
            pass

    return {
        "rating": "N/A", "reviews": "N/A", "ranking": None,
        "match_ok": False, "error_reason": "agoda_pattern_not_found"
    }


# ─────────────────────────────────────────────
# PARSER: BOOKING.COM
# ─────────────────────────────────────────────
def parse_booking(text):
    rating = "N/A"
    reviews = "N/A"

    rating_patterns = [
        r'"ratingValue"\s*:\s*([\d.]+)',
        r'"reviewScore"\s*:\s*([\d.]+)',
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
        r'"reviewCount"\s*:\s*(\d+)',
        r'"ratingCount"\s*:\s*(\d+)',
        r"([\d,\.]+)\s+reviews",
        r"([\d,\.]+)\s+review",
        r"([\d,\.]+)\s+ulasan",
        r"based on\s+([\d,\.]+)",
        r"from\s+([\d,\.]+)\s+reviews",
        r"([\d,\.]+)\s+guest\s+reviews",
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


# ─────────────────────────────────────────────
# PARSER + FETCH: TRIP.COM (urllib — server-side render)
# ─────────────────────────────────────────────
def parse_tripcom(text):
    rating = "N/A"
    reviews = "N/A"

    # Pola dari halaman Trip.com yang ter-render server-side:
    # "8,4 /10 Luar Biasa 224 ulasan" atau "8,4*/10* ... 224 ulasan"
    combined_patterns = [
        r"(\d[.,]\d)\s*\*?\s*/\s*10\s*\*?\s*(?:Luar\s+Biasa|Sangat\s+Baik|Mengesankan|Baik|Excellent|Very\s+Good|Wonderful|Good|Fabulous|Superb)?.{0,300}?([\d,\.]+)\s+(?:ulasan|reviews?)",
        r"(\d[.,]\d)\s*/10.{0,200}?([\d,\.]+)\s+(?:ulasan|reviews?)",
        r"([\d,\.]+)\s+(?:ulasan|reviews?).{0,200}?(\d[.,]\d)\s*/10",
    ]

    for pattern in combined_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            g1, g2 = match.group(1), match.group(2)
            r1, r2 = clean_rating(g1), clean_number(g2)
            # Cek apakah g1 adalah rating atau review count
            if is_valid_rating(r1, 6, 10) and is_valid_reviews(r2, 5):
                rating, reviews = r1, r2
                break
            # Coba terbalik
            r1b, r2b = clean_rating(g2), clean_number(g1)
            if is_valid_rating(r1b, 6, 10) and is_valid_reviews(r2b, 5):
                rating, reviews = r1b, r2b
                break

    # Fallback
    if rating == "N/A":
        for m in re.finditer(r"\b(\d[.,]\d)\s*/\s*10\b", text, re.IGNORECASE):
            c = clean_rating(m.group(1))
            if is_valid_rating(c, 6, 10):
                rating = c
                break

    if reviews == "N/A":
        candidates = []
        for m in re.finditer(r"\b([\d,\.]+)\s+(?:ulasan|reviews?)\b", text, re.IGNORECASE):
            c = clean_number(m.group(1))
            if is_valid_reviews(c, 5):
                try:
                    candidates.append(int(c))
                except Exception:
                    pass
        if candidates:
            reviews = str(max(candidates))

    ok = is_valid_rating(rating, 6, 10) and is_valid_reviews(reviews, 5)
    return {
        "rating": rating if ok else "N/A",
        "reviews": reviews if ok else "N/A",
        "ranking": None,
        "match_ok": ok,
        "error_reason": None if ok else "tripcom_pattern_not_found"
    }


def fetch_tripcom(url, hotel_name):
    """Trip.com: HTTP request biasa karena server-side render."""
    for attempt in range(1, MAX_RETRY + 1):
        try:
            html = http_get(url, {
                "Referer": "https://id.trip.com/",
                "Accept-Language": "id-ID,id;q=0.9",
            })
            text = normalize_text(re.sub(r"<[^>]+>", " ", html))
            debug_write(DEBUG_TRIP_FILE, hotel_name, url, text[:3000], html[:2500])
            result = parse_tripcom(text + " " + html)
            if result.get("match_ok"):
                print(f"    [tripcom] HTTP berhasil attempt {attempt}: rating={result['rating']}, reviews={result['reviews']}")
                return result
            print(f"    [tripcom] Pattern tidak match attempt {attempt}, text length={len(text)}")
            time.sleep(8)
        except Exception as e:
            log_error(hotel_name, "tripcom", f"http_attempt_{attempt}: {str(e)[:80]}")
            print(f"    [tripcom] Error attempt {attempt}: {str(e)[:60]}")
            time.sleep(8)
    return {
        "rating": "N/A", "reviews": "N/A", "ranking": None,
        "match_ok": False, "error_reason": "tripcom_pattern_not_found"
    }


# ─────────────────────────────────────────────
# PARSER + FETCH: TRAVELOKA (urllib — server-side render)
# ─────────────────────────────────────────────
def is_rating_format(text):
    """Cek apakah teks adalah format rating (X,X atau X.X) bukan ribuan seperti 6.468."""
    # Rating harus: 1 digit, koma/titik, 1 digit — misal 8,3 atau 8.3
    # Bukan ribuan seperti 6.468 atau 6,468
    return bool(re.match(r'^\d[.,]\d$', str(text).strip()))


def parse_traveloka(text):
    rating = "N/A"
    reviews = "N/A"

    # Pola dari halaman Traveloka yang ter-render:
    # "8,3 /10 Mengesankan 6.468 ulasan"
    # PENTING: rating harus format X,X (1 digit koma 1 digit)
    # Angka ribuan seperti "6.468" bukan rating!
    combined_patterns = [
        r"(\d[.,]\d)\s*/\s*10\s*(?:Mengesankan|Sangat\s+Bagus|Luar\s+Biasa|Menyenangkan|Bagus|Memuaskan|Baik)?\s*([\d,.]+)\s+ulasan",
        r"(\d[.,]\d)\s*/\s*10.{0,200}?([\d,.]+)\s+ulasan",
        r"([\d,.]+)\s+ulasan.{0,200}?(\d[.,]\d)\s*/\s*10",
    ]

    for pattern in combined_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            g1, g2 = match.group(1), match.group(2)
            # Validasi: g1 harus format rating (X,X), g2 adalah review count
            if is_rating_format(g1):
                r1, r2 = clean_rating(g1), clean_number(g2)
                if is_valid_rating(r1, 5, 10) and is_valid_reviews(r2, 10):
                    rating, reviews = r1, r2
                    break
            # Coba terbalik: g2 adalah rating, g1 adalah review
            elif is_rating_format(g2):
                r1, r2 = clean_rating(g2), clean_number(g1)
                if is_valid_rating(r1, 5, 10) and is_valid_reviews(r2, 10):
                    rating, reviews = r1, r2
                    break

    # JSON-LD / structured data
    if rating == "N/A":
        for pattern in [
            r'"ratingValue"\s*:\s*"?(\d+(?:[.,]\d+)?)"?',
            r'"aggregateRating"[^}]*?"ratingValue"\s*:\s*"?(\d+(?:[.,]\d+)?)"?',
            r'"score"\s*:\s*"?(\d+(?:[.,]\d+)?)"?',
        ]:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                c = clean_rating(m.group(1))
                if is_valid_rating(c, 5, 10) and is_rating_format(m.group(1)):
                    rating = c
                    break

    if reviews == "N/A":
        candidates = []
        for pattern in [
            r'"reviewCount"\s*:\s*"?(\d+)"?',
            r'"totalReviews"\s*:\s*"?(\d+)"?',
            r'"ratingCount"\s*:\s*"?(\d+)"?',
            r"\b([\d,.]+)\s+ulasan\b",
            r"\b([\d,.]+)\s+reviews?\b",
        ]:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                c = clean_number(m.group(1))
                if is_valid_reviews(c, 10):
                    try:
                        candidates.append(int(c))
                    except Exception:
                        pass
        if candidates:
            reviews = str(max(candidates))

    ok = is_valid_rating(rating, 5, 10) and is_valid_reviews(reviews, 10)
    return {
        "rating": rating if ok else "N/A",
        "reviews": reviews if ok else "N/A",
        "ranking": None,
        "match_ok": ok,
        "error_reason": None if ok else "traveloka_strong_pattern_not_found"
    }


def fetch_traveloka(playwright, url, hotel_name):
    """
    Traveloka: coba HTTP request dulu (server-side render),
    fallback ke Playwright jika gagal.
    """
    # Strategi 1: HTTP request biasa
    for attempt in range(1, MAX_RETRY + 1):
        try:
            html = http_get(url, {"Referer": "https://www.traveloka.com/"})
            text = normalize_text(re.sub(r"<[^>]+>", " ", html))
            result = parse_traveloka(text + " " + html)
            if result.get("match_ok"):
                print(f"    [traveloka] HTTP berhasil attempt {attempt}: rating={result['rating']}, reviews={result['reviews']}")
                return result
            print(f"    [traveloka] HTTP pattern tidak match attempt {attempt}, text length={len(text)}")
            time.sleep(6)
        except Exception as e:
            print(f"    [traveloka] HTTP error attempt {attempt}: {str(e)[:60]}")
            time.sleep(6)

    # Strategi 2: Playwright fallback
    print(f"    [traveloka] Fallback ke Playwright...")
    browser = None
    context = None
    try:
        browser = playwright.chromium.launch(headless=True, args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-gpu",
        ])
        context = browser.new_context(
            locale="id-ID",
            viewport={"width": 1440, "height": 1200},
            user_agent=random.choice(USER_AGENTS)
        )
        page = context.new_page()
        page.set_extra_http_headers({"Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8"})

        for _ in range(MAX_RETRY):
            safe_goto(page, url, timeout=90000)
            page.wait_for_timeout(8000)

            # Ambil semua sumber teks
            collected = []
            try:
                collected.append(normalize_text(page.locator("body").inner_text(timeout=10000)))
            except Exception:
                pass
            try:
                html = page.content()
                collected.append(normalize_text(re.sub(r"<[^>]+>", " ", html)))
                collected.append(html)
            except Exception:
                pass
            try:
                json_ld = page.evaluate("""
                    () => Array.from(document.querySelectorAll('script[type="application/ld+json"]'))
                         .map(s => s.textContent).join(' ')
                """)
                if json_ld:
                    collected.append(json_ld)
            except Exception:
                pass

            combined = normalize_text(" ".join(collected))
            result = parse_traveloka(combined)
            if result.get("match_ok"):
                print(f"    [traveloka] Playwright berhasil: rating={result['rating']}, reviews={result['reviews']}")
                return result
            time.sleep(10)

    except Exception as e:
        log_error(hotel_name, "traveloka", f"playwright_error: {str(e)[:80]}")
    finally:
        try:
            if context:
                context.close()
            if browser:
                browser.close()
        except Exception:
            pass

    return {
        "rating": "N/A", "reviews": "N/A", "ranking": None,
        "match_ok": False, "error_reason": "traveloka_strong_pattern_not_found"
    }


# ─────────────────────────────────────────────
# PARSER + FETCH: TIKET.COM (Playwright stealth per hotel)
# ─────────────────────────────────────────────
def parse_tiket_text(text):
    rating = "N/A"
    reviews = "N/A"

    combined_patterns = [
        r"Review\s+Lihat\s+semua\s+(\d[.,]\d)\s*/\s*5.*?Dari\s+([\d,\.]+)\s+review",
        r"(\d[.,]\d)\s*/\s*5\s*(?:Bagus|Sangat\s+Bagus|Luar\s+Biasa|Mengesankan|Menyenangkan|Memuaskan)?\s*Dari\s+([\d,\.]+)\s+review",
        r"(\d[.,]\d)\s*/\s*5.*?Dari\s+([\d,\.]+)\s+review",
        r"(\d[.,]\d)\s*/\s*5.*?([\d,\.]+)\s+review",
        r"(\d[.,]\d)\s*/\s*5.*?([\d,\.]+)\s+ulasan",
        r'"score"\s*:\s*"?(\d+(?:[.,]\d+)?)"?.*?"total"\s*:\s*(\d+)',
        r'"averageScore"\s*:\s*"?(\d+(?:[.,]\d+)?)"?.*?"totalReview"\s*:\s*(\d+)',
        r'"rating"\s*:\s*"?(\d+(?:[.,]\d+)?)"?.*?"reviewCount"\s*:\s*(\d+)',
    ]
    for pattern in combined_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            r1, r2 = clean_rating(match.group(1)), clean_number(match.group(2))
            if is_valid_rating(r1, 1, 5) and is_valid_reviews(r2, 10):
                rating, reviews = r1, r2
                break

    if rating == "N/A":
        for pattern in [
            r"(\d[.,]\d)\s*/\s*5",
            r'"ratingValue"\s*:\s*"?(\d+(?:[.,]\d+)?)"?',
        ]:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                c = clean_rating(m.group(1))
                if is_valid_rating(c, 1, 5):
                    rating = c
                    break

    if reviews == "N/A":
        for pattern in [
            r"Dari\s+([\d,\.]+)\s+revie",
            r"([\d,\.]+)\s+revie",
            r"([\d,\.]+)\s+ulasa",
            r'"reviewCount"\s*:\s*"?(\d+)"?',
            r'"totalReview"\s*:\s*"?(\d+)"?',
        ]:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                c = clean_number(m.group(1))
                if is_valid_reviews(c, 10):
                    reviews = c
                    break

    ok = is_valid_rating(rating, 1, 5) and is_valid_reviews(reviews, 10)
    return {
        "rating": rating if ok else "N/A",
        "reviews": reviews if ok else "N/A",
        "ranking": None,
        "match_ok": ok,
        "error_reason": None if ok else "tiket_pattern_not_found"
    }


def fetch_tiket(playwright, hotel_name, url):
    """Tiket.com: browser stealth tersendiri per hotel."""
    ua = random.choice(USER_AGENTS)
    delay = random.randint(15, 40)
    print(f"    [tiket] Menunggu {delay}s sebelum scrape...")
    time.sleep(delay)

    browser = None
    context = None
    try:
        browser = playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-extensions",
                f"--user-agent={ua}",
            ]
        )
        context = browser.new_context(
            locale="id-ID",
            viewport={"width": 1440, "height": 900},
            user_agent=ua,
            java_script_enabled=True,
            bypass_csp=True,
            extra_http_headers={
                "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
            }
        )
        page = context.new_page()
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {name:'Chrome PDF Plugin'},
                    {name:'Chrome PDF Viewer'},
                    {name:'Native Client'}
                ]
            });
            Object.defineProperty(navigator, 'languages', {get: () => ['id-ID','id','en-US','en']});
            Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 4});
            window.chrome = {runtime: {}, loadTimes: function(){}, csi: function(){}, app: {}};
        """)

        last_result = None
        for attempt in range(1, MAX_RETRY + 1):
            try:
                print(f"    [tiket] Attempt {attempt}/{MAX_RETRY}...")
                page.goto(url, timeout=90000, wait_until="domcontentloaded")
                page.wait_for_timeout(12000)

                for scroll_pos in [300, 600, 900, 1200]:
                    page.evaluate(f"window.scrollTo(0, {scroll_pos})")
                    page.wait_for_timeout(random.randint(800, 1500))

                text = get_page_text(page, 2000)
                try:
                    html = page.content()
                except Exception:
                    html = ""

                debug_write(DEBUG_TIKET_FILE, hotel_name, url, text, html)

                if re.search(r"Robot atau manusia|Centang kotak|Ray ID|Turnstile|verify you are human", text, re.IGNORECASE):
                    print(f"    [tiket] Cloudflare captcha terdeteksi attempt {attempt}")
                    log_error(hotel_name, "tiket", f"cloudflare_captcha_attempt_{attempt}")
                    last_result = {
                        "rating": "N/A", "reviews": "N/A", "ranking": None,
                        "match_ok": False, "error_reason": "tiket_cloudflare_captcha"
                    }
                    if attempt < MAX_RETRY:
                        time.sleep(random.randint(20, 35))
                    continue

                result = parse_tiket_text(text)
                last_result = result

                if result.get("match_ok"):
                    print(f"    [tiket] Berhasil: rating={result['rating']}, reviews={result['reviews']}")
                    return result

                if attempt < MAX_RETRY:
                    time.sleep(random.randint(10, 20))

            except Exception as e:
                last_result = {
                    "rating": "N/A", "reviews": "N/A", "ranking": None,
                    "match_ok": False, "error_reason": f"tiket_error: {str(e)[:80]}"
                }
                if attempt < MAX_RETRY:
                    time.sleep(random.randint(15, 25))

        return last_result or {
            "rating": "N/A", "reviews": "N/A", "ranking": None,
            "match_ok": False, "error_reason": "tiket_all_attempts_failed"
        }

    except Exception as e:
        return {
            "rating": "N/A", "reviews": "N/A", "ranking": None,
            "match_ok": False, "error_reason": f"tiket_browser_error: {str(e)[:80]}"
        }
    finally:
        try:
            if context:
                context.close()
            if browser:
                browser.close()
        except Exception:
            pass


# ─────────────────────────────────────────────
# SCRAPE BOOKING.COM (Playwright shared browser)
# ─────────────────────────────────────────────
def scrape_booking(page, url, hotel_name, wait_ms=9000):
    last_error = None
    for _ in range(MAX_RETRY):
        try:
            safe_goto(page, url, timeout=80000)
            text = get_page_text(page, wait_ms)
            result = parse_booking(text)
            if result.get("match_ok"):
                return result
            last_error = result.get("error_reason", "booking_pattern_not_found")
            time.sleep(10)
        except Exception as e:
            last_error = str(e)
            time.sleep(10)

    log_error(hotel_name, "booking", last_error)
    return {
        "rating": "N/A", "reviews": "N/A", "ranking": None,
        "match_ok": False, "error_reason": last_error or "booking_scrape_failed"
    }


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    for file in [DEBUG_TIKET_FILE, DEBUG_TRIP_FILE]:
        try:
            with open(file, "w", encoding="utf-8") as f:
                f.write(f"# DEBUG LOG — {datetime.now()}\n\n")
        except Exception:
            pass

    previous_data = load_current_data()
    hotels_today = []

    with sync_playwright() as p:
        # Browser untuk Booking.com
        browser = p.chromium.launch(headless=True, args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-gpu"
        ])
        context = browser.new_context(
            locale="id-ID",
            viewport={"width": 1366, "height": 768},
            user_agent=random.choice(USER_AGENTS),
            java_script_enabled=True,
            bypass_csp=True,
        )
        page = context.new_page()
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['id-ID','id','en-US','en']});
            window.chrome = {runtime: {}};
        """)
        page.set_extra_http_headers({
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        })

        for hotel_name, sources in HOTELS.items():
            print(f"\n{'='*50}")
            print(f"Hotel: {hotel_name}")
            print(f"{'='*50}")
            hotel_record = {"name": hotel_name, "platforms": {}}

            # ── Agoda (Playwright — JS render diperlukan) ──
            print("  agoda")
            fresh = fetch_agoda(sources["agoda"], hotel_name, playwright=p)
            parsed = finalize_platform_result(hotel_name, "agoda", fresh, previous_data)
            print(f"     rating: {parsed['rating']} | reviews: {parsed['reviews']} | status: {parsed['status']}")
            if parsed.get("error_reason"):
                print(f"     error: {parsed['error_reason']}")
            hotel_record["platforms"]["agoda"] = parsed

            # ── Booking.com (Playwright) ──
            print("  booking")
            fresh = scrape_booking(page, sources["booking"], hotel_name)
            parsed = finalize_platform_result(hotel_name, "booking", fresh, previous_data)
            print(f"     rating: {parsed['rating']} | reviews: {parsed['reviews']} | status: {parsed['status']}")
            if parsed.get("error_reason"):
                print(f"     error: {parsed['error_reason']}")
            hotel_record["platforms"]["booking"] = parsed

            # ── Traveloka (HTTP request + Playwright fallback) ──
            print("  traveloka")
            fresh = fetch_traveloka(p, sources["traveloka"], hotel_name)
            parsed = finalize_platform_result(hotel_name, "traveloka", fresh, previous_data)
            print(f"     rating: {parsed['rating']} | reviews: {parsed['reviews']} | status: {parsed['status']}")
            if parsed.get("error_reason"):
                print(f"     error: {parsed['error_reason']}")
            hotel_record["platforms"]["traveloka"] = parsed

            # ── Trip.com (HTTP request) ──
            print("  tripcom")
            fresh = fetch_tripcom(sources["tripcom"], hotel_name)
            parsed = finalize_platform_result(hotel_name, "tripcom", fresh, previous_data)
            print(f"     rating: {parsed['rating']} | reviews: {parsed['reviews']} | status: {parsed['status']}")
            if parsed.get("error_reason"):
                print(f"     error: {parsed['error_reason']}")
            hotel_record["platforms"]["tripcom"] = parsed

            # ── Tiket.com (Playwright stealth) ──
            print("  tiket")
            fresh = fetch_tiket(p, hotel_name, sources["tiket"])
            parsed = finalize_platform_result(hotel_name, "tiket", fresh, previous_data)
            print(f"     rating: {parsed['rating']} | reviews: {parsed['reviews']} | status: {parsed['status']}")
            if parsed.get("error_reason"):
                print(f"     error: {parsed['error_reason']}")
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

    print("\n" + "="*50)
    print("SELESAI")
    print("="*50)


if __name__ == "__main__":
    main()