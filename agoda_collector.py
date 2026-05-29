from playwright.sync_api import sync_playwright
import json
import re
import os
import time
import random
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
        "agoda": "https://www.agoda.com/verse-lite-hotel-gajah-mada/reviews/jakarta-id.html",
        "booking": "https://www.booking.com/hotel/id/verse-lite-pembangunan.html#tab-reviews",
        "traveloka": "https://www.traveloka.com/id-id/hotel/indonesia/verse-lite-hotel-gajah-mada-3000010028056",
        "tripcom": "https://id.trip.com/hotels/central-jakarta-city-hotel-detail-6449572/verse-lite-hotel-gajah-mada/",
        "tiket": "https://www.tiket.com/hotel/indonesia/verse-lite-hotel-gajah-mada-807001751612826254"
    },
    "Verse Luxe Wahid Hasyim": {
        "agoda": "https://www.agoda.com/verse-luxe-hotel-wahid-hasyim/reviews/jakarta-id.html",
        "booking": "https://www.booking.com/hotel/id/verse-luxe-wahid-hasyim.html#tab-reviews",
        "traveloka": "https://www.traveloka.com/id-id/hotel/indonesia/verse-luxe-hotel-wahid-hasyim-3000010036666",
        "tripcom": "https://id.trip.com/hotels/central-jakarta-city-hotel-detail-9029304/verse-luxe-hotel-wahid-hasyim/",
        "tiket": "https://www.tiket.com/hotel/indonesia/verse-luxe-hotel-wahid-hasyim-112001545304320268"
    },
    "Verse Cirebon": {
        "agoda": "https://www.agoda.com/verse-hotel-cirebon/reviews/cirebon-id.html",
        "booking": "https://www.booking.com/hotel/id/verse-cirebon.html#tab-reviews",
        "traveloka": "https://www.traveloka.com/id-id/hotel/indonesia/verse-hotel-cirebon-3000010015654",
        "tripcom": "https://id.trip.com/hotels/kedawung-hotel-detail-5965336/verse-hotel-cirebon/",
        "tiket": "https://www.tiket.com/hotel/indonesia/verse-hotel-cirebon-108001534490349528"
    },
    "Oak Tree Mahakam Blok M": {
        "agoda": "https://www.agoda.com/oak-tree-urban-hotel/reviews/jakarta-id.html",
        "booking": "https://www.booking.com/hotel/id/oak-tree-urban.html#tab-reviews",
        "traveloka": "https://www.traveloka.com/id-id/hotel/indonesia/oak-tree-urban-hotel-jakarta-461895",
        "tripcom": "https://id.trip.com/hotels/south-jakarta-city-hotel-detail-2652976/oak-tree-urban-hotel-jakarta/",
        "tiket": "https://www.tiket.com/hotel/indonesia/oak-tree-urban-jakarta-412001639976768183"
    }
}

PLATFORM_SCOPE = ["agoda", "booking", "traveloka", "tripcom", "tiket"]

# Tiket hotel ID map (dari URL slug terakhir sebelum angka panjang)
TIKET_HOTEL_IDS = {
    "Verse Lite Gajah Mada":    "807001751612826254",
    "Verse Luxe Wahid Hasyim":  "112001545304320268",
    "Verse Cirebon":             "108001534490349528",
    "Oak Tree Mahakam Blok M":  "412001639976768183"
}

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
        "Ulasan Tamu", "Ulasan tamu", "Guest Reviews",
        "Guest reviews", "Hotel Reviews", "Reviews", "review.html"
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
                if is_valid_rating(candidate_rating, 6, 10) and is_valid_reviews(candidate_reviews, 5):
                    rating = candidate_rating
                    reviews = candidate_reviews
                    break
        if rating != "N/A":
            break

    if rating == "N/A" or reviews == "N/A":
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


def parse_tiket_text(text):
    """Parse teks halaman Tiket setelah berhasil di-load (bukan captcha)."""
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
            candidate_rating = clean_rating(match.group(1))
            candidate_reviews = clean_number(match.group(2))
            if is_valid_rating(candidate_rating, 1, 5) and is_valid_reviews(candidate_reviews, 10):
                rating = candidate_rating
                reviews = candidate_reviews
                break

    if rating == "N/A":
        for pattern in [
            r"(\d[.,]\d)\s*/\s*5",
            r'"ratingValue"\s*:\s*"?(\d+(?:[.,]\d+)?)"?',
            r'"score"\s*:\s*"?(\d+(?:[.,]\d+)?)"?',
        ]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                candidate = clean_rating(match.group(1))
                if is_valid_rating(candidate, 1, 5):
                    rating = candidate
                    break

    if reviews == "N/A":
        for pattern in [
            r"Dari\s+([\d,\.]+)\s+revie",
            r"Dari\s+([\d,\.]+)\s+ulasa",
            r"([\d,\.]+)\s+revie",
            r"([\d,\.]+)\s+ulasa",
            r'"reviewCount"\s*:\s*"?(\d+)"?',
            r'"totalReview"\s*:\s*"?(\d+)"?',
        ]:
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


def fetch_tiket(playwright, hotel_name, url):
    """
    Scrape Tiket.com dengan browser stealth tersendiri per hotel.
    Setiap hotel pakai user-agent berbeda + random delay untuk menghindari Cloudflare.
    """
    ua = random.choice(USER_AGENTS)

    # Random delay antar hotel: 15-40 detik
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
                "--disable-plugins",
                "--disable-images",          # hemat bandwidth
                "--blink-settings=imagesEnabled=false",
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
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "max-age=0",
            }
        )

        page = context.new_page()

        # Stealth patches
        page.add_init_script("""
            // Sembunyikan tanda-tanda automation
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {name:'Chrome PDF Plugin', filename:'internal-pdf-viewer'},
                    {name:'Chrome PDF Viewer', filename:'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                    {name:'Native Client', filename:'internal-nacl-plugin'}
                ]
            });
            Object.defineProperty(navigator, 'languages', {get: () => ['id-ID','id','en-US','en']});
            Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 4});
            Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
            window.chrome = {
                runtime: {},
                loadTimes: function(){},
                csi: function(){},
                app: {}
            };
            // Patch permission query
            const origQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    origQuery(parameters)
            );
        """)

        last_result = None
        for attempt in range(1, MAX_RETRY + 1):
            try:
                print(f"    [tiket] Attempt {attempt}/{MAX_RETRY}...")
                page.goto(url, timeout=90000, wait_until="domcontentloaded")

                # Tunggu lebih lama agar JS load
                page.wait_for_timeout(12000)

                # Simulasi scroll manusia
                for scroll_pos in [300, 600, 900, 1200]:
                    page.evaluate(f"window.scrollTo(0, {scroll_pos})")
                    page.wait_for_timeout(random.randint(800, 1500))

                # Ambil teks
                text = get_page_text(page, 2000)

                # Ambil HTML untuk debug
                try:
                    html = page.content()
                except Exception:
                    html = ""

                debug_write(DEBUG_TIKET_FILE, hotel_name, url, text, html)

                # Cek apakah masih captcha
                if re.search(
                    r"Robot atau manusia|Centang kotak|Ray ID|Turnstile|verify you are human",
                    text, re.IGNORECASE
                ):
                    print(f"    [tiket] Cloudflare captcha terdeteksi, attempt {attempt}")
                    log_error(hotel_name, "tiket", f"cloudflare_captcha_attempt_{attempt}")
                    last_result = {
                        "rating": "N/A", "reviews": "N/A", "ranking": None,
                        "match_ok": False, "error_reason": "tiket_cloudflare_captcha"
                    }
                    if attempt < MAX_RETRY:
                        wait = random.randint(20, 35)
                        print(f"    [tiket] Tunggu {wait}s sebelum retry...")
                        time.sleep(wait)
                    continue

                # Parse
                result = parse_tiket_text(text)
                last_result = result

                if result.get("match_ok"):
                    print(f"    [tiket] Berhasil: rating={result['rating']}, reviews={result['reviews']}")
                    return result

                print(f"    [tiket] Pattern tidak match, attempt {attempt}")
                if attempt < MAX_RETRY:
                    time.sleep(random.randint(10, 20))

            except Exception as e:
                last_result = {
                    "rating": "N/A", "reviews": "N/A", "ranking": None,
                    "match_ok": False, "error_reason": f"tiket_error: {str(e)[:80]}"
                }
                print(f"    [tiket] Error: {str(e)[:60]}")
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


def traveloka_extract_from_text(text):
    rating = "N/A"
    reviews = "N/A"

    rating_patterns = [
        r'"ratingValue"\s*:\s*"?(\d+(?:[.,]\d+)?)"?',
        r'"aggregateRating"[^}]*?"ratingValue"\s*:\s*"?(\d+(?:[.,]\d+)?)"?',
        r'"starRating"\s*:\s*"?(\d+(?:[.,]\d+)?)"?',
        r'"guestRating"\s*:\s*"?(\d+(?:[.,]\d+)?)"?',
        r'"hotelRating"\s*:\s*"?(\d+(?:[.,]\d+)?)"?',
        r'"score"\s*:\s*"?(\d+(?:[.,]\d+)?)"?',
        r"\b(\d[.,]\d)\s*/\s*10\b",
        r"\b(\d[.,]\d)\s+(?:Sangat\s+Bagus|Luar\s+Biasa|Mengesankan|Menyenangkan|Bagus|Memuaskan)\b",
        r"(\d[.,]\d)\s*(?:out of|\/|/)\s*10",
        r'rating["\s:]+(\d[.,]\d)',
    ]

    for pattern in rating_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = clean_rating(match.group(1))
            if is_valid_rating(candidate, 5, 10):
                rating = candidate
                break

    review_patterns = [
        r'"reviewCount"\s*:\s*"?(\d+)"?',
        r'"ratingCount"\s*:\s*"?(\d+)"?',
        r'"totalReviews"\s*:\s*"?(\d+)"?',
        r'"totalRatings"\s*:\s*"?(\d+)"?',
        r'"numReviews"\s*:\s*"?(\d+)"?',
        r'"reviewTotal"\s*:\s*"?(\d+)"?',
        r"\bDari\s+([\d,.]+)\s+(?:ulasan|review|reviews)\b",
        r"\b([\d,.]+)\s+ulasan\b",
        r"\b([\d,.]+)\s+reviews?\b",
        r"\b([\d,.]+)\s+Ulasan\b",
    ]

    review_candidates = []
    for pattern in review_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            candidate = clean_number(match.group(1))
            if is_valid_reviews(candidate, 10):
                try:
                    review_candidates.append(int(candidate))
                except Exception:
                    pass

    if review_candidates:
        reviews = str(max(review_candidates))

    ok = is_valid_rating(rating, 5, 10) and is_valid_reviews(reviews, 10)
    return {
        "rating": rating if ok else "N/A",
        "reviews": reviews if ok else "N/A",
        "ranking": None,
        "match_ok": ok,
        "error_reason": None if ok else "traveloka_strong_pattern_not_found"
    }


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

    grab(4000)

    for pos in [500, 1000, 1500, 2200, 3000, 3800, 4600, 5600]:
        try:
            page.evaluate(f"window.scrollTo(0, {pos})")
            grab(2000)
        except Exception:
            pass

    try:
        html = page.content()
        plain = re.sub(r"<[^>]+>", " ", html)
        collected.append(normalize_text(plain))
        collected.append(html)
    except Exception:
        pass

    try:
        json_ld_texts = page.evaluate("""
            () => {
                const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                return Array.from(scripts).map(s => s.textContent).join(' ');
            }
        """)
        if json_ld_texts:
            collected.append(json_ld_texts)
    except Exception:
        pass

    try:
        script_texts = page.evaluate("""
            () => {
                const scripts = document.querySelectorAll('script:not([src])');
                return Array.from(scripts)
                    .map(s => s.textContent)
                    .filter(t => t && (
                        t.includes('ratingValue') ||
                        t.includes('reviewCount') ||
                        t.includes('aggregateRating') ||
                        t.includes('totalReviews') ||
                        t.includes('hotelReview') ||
                        t.includes('guestReview') ||
                        t.includes('starRating')
                    ))
                    .join(' ');
            }
        """)
        if script_texts:
            collected.append(script_texts)
    except Exception:
        pass

    try:
        api_text = page.evaluate("""
            () => {
                const keys = ['__INITIAL_STATE__', '__NEXT_DATA__', '__NUXT__',
                              'TvlkGlobal', '__APP_STATE__', '__DATA__'];
                for (const key of keys) {
                    if (window[key]) {
                        try { return JSON.stringify(window[key]); } catch(e) {}
                    }
                }
                return '';
            }
        """)
        if api_text:
            collected.append(api_text)
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

        return last or {
            "rating": "N/A", "reviews": "N/A", "ranking": None,
            "match_ok": False, "error_reason": "traveloka_failed"
        }

    except Exception as e:
        return {
            "rating": "N/A", "reviews": "N/A", "ranking": None,
            "match_ok": False, "error_reason": f"traveloka_error: {str(e)[:80]}"
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
    last_html = ""

    for _ in range(MAX_RETRY):
        try:
            safe_goto(page, url, timeout=80000)
            text = get_page_text(page, wait_ms)
            last_text = text

            try:
                last_html = page.content()
            except Exception:
                last_html = ""

            if platform_name == "tripcom":
                debug_write(DEBUG_TRIP_FILE, hotel_name, url, text, last_html)

            result = parser_func(text)

            if result.get("match_ok"):
                return result

            last_error = result.get("error_reason", "pattern_not_found")
            time.sleep(10)

        except Exception as e:
            last_error = str(e)
            time.sleep(10)

    if platform_name == "tripcom":
        debug_write(DEBUG_TRIP_FILE, hotel_name, url, last_text, last_html)

    log_error(hotel_name, platform_name, last_error)
    return {
        "rating": "N/A", "reviews": "N/A", "ranking": None,
        "match_ok": False, "error_reason": last_error or "scrape_failed"
    }


def main():
    # Reset debug files
    for file in [DEBUG_TIKET_FILE, DEBUG_TRIP_FILE]:
        try:
            with open(file, "w", encoding="utf-8") as f:
                f.write(f"# DEBUG LOG — {datetime.now()}\n\n")
        except Exception:
            pass

    previous_data = load_current_data()
    hotels_today = []

    with sync_playwright() as p:
        # Browser utama untuk Agoda, Booking, Trip.com
        browser = p.chromium.launch(headless=True, args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-gpu"
        ])

        context = browser.new_context(
            locale="id-ID",
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
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
            "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        })

        for hotel_name, sources in HOTELS.items():
            print("Hotel:", hotel_name)
            hotel_record = {"name": hotel_name, "platforms": {}}

            # Platform standar (Agoda, Booking, Trip.com)
            platform_jobs = [
                ("agoda",   parse_agoda,   6000),
                ("booking", parse_booking, 9000),
                ("tripcom", parse_tripcom, 12000),
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
                print(f"     rating: {parsed['rating']} | reviews: {parsed['reviews']} | status: {parsed['status']}")
                if parsed.get("error_reason"):
                    print(f"     error: {parsed['error_reason']}")
                hotel_record["platforms"][platform_name] = parsed

            # Traveloka — browser terpisah
            print("  traveloka")
            fresh = fetch_traveloka(p, sources["traveloka"])
            parsed = finalize_platform_result(hotel_name, "traveloka", fresh, previous_data)
            print(f"     rating: {parsed['rating']} | reviews: {parsed['reviews']} | status: {parsed['status']}")
            if parsed.get("error_reason"):
                print(f"     error: {parsed['error_reason']}")
            hotel_record["platforms"]["traveloka"] = parsed

            # Tiket — browser terpisah dengan stealth per hotel
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

    print("\nSELESAI")


if __name__ == "__main__":
    main()