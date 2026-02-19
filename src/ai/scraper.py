"""
Web scraper for extracting schema-relevant business data from a URL.
Pulls: logo, image, phone, email, address, Google Maps URL, and any
existing JSON-LD already on the page.
"""
import json
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def scrape_business_page(url: str) -> dict:
    """
    Scrape a business homepage and return a dict of schema-relevant fields.
    Never raises — returns whatever was found, empty dict on total failure.
    """
    result = {}

    try:
        resp = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
        resp.raise_for_status()
    except Exception:
        return result

    try:
        soup = BeautifulSoup(resp.text, "html.parser")

        # ── 1. Existing JSON-LD on the page (highest priority) ─────────────────
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                raw = json.loads(script.string or "")
                schemas = raw.get("@graph", [raw]) if isinstance(raw, dict) else raw
                if not isinstance(schemas, list):
                    schemas = [schemas]

                for s in schemas:
                    if not isinstance(s, dict):
                        continue
                    stype = s.get("@type", "")
                    types = stype if isinstance(stype, list) else [stype]
                    is_biz = any(
                        t in (
                            "LocalBusiness", "Organization", "Plumber",
                            "HVACBusiness", "HomeAndConstructionBusiness",
                            "LegalService", "MedicalBusiness", "Dentist",
                            "AutoRepair", "GeneralContractor",
                        )
                        for t in types
                    )
                    if is_biz or "LocalBusiness" in str(types):
                        _merge_from_schema(result, s)
            except Exception:
                continue

        # ── 2. Open Graph tags ─────────────────────────────────────────────────
        og = {
            tag.get("property", ""): tag.get("content", "")
            for tag in soup.find_all("meta", property=True)
        }
        name_tags = {
            tag.get("name", ""): tag.get("content", "")
            for tag in soup.find_all("meta", attrs={"name": True})
        }

        if not result.get("image_url"):
            result["image_url"] = og.get("og:image", "")

        if not result.get("description"):
            result["description"] = (
                og.get("og:description", "")
                or name_tags.get("description", "")
            )

        if not result.get("business_name"):
            result["business_name"] = og.get("og:site_name", "")

        # ── 3. Logo detection ──────────────────────────────────────────────────
        if not result.get("logo_url"):
            result["logo_url"] = _find_logo(soup, url)

        # ── 4. Phone (tel: links) ──────────────────────────────────────────────
        if not result.get("telephone"):
            tel = soup.find("a", href=re.compile(r"^tel:", re.I))
            if tel:
                result["telephone"] = re.sub(r"^tel:", "", tel["href"]).strip()

        # ── 5. Email (mailto: links) ───────────────────────────────────────────
        if not result.get("email"):
            mailto = soup.find("a", href=re.compile(r"^mailto:", re.I))
            if mailto:
                result["email"] = (
                    re.sub(r"^mailto:", "", mailto["href"]).split("?")[0].strip()
                )

        # ── 6. Google Maps URL ─────────────────────────────────────────────────
        if not result.get("has_map"):
            maps_a = soup.find("a", href=re.compile(r"google\.com/maps", re.I))
            if maps_a:
                result["has_map"] = maps_a["href"]
            else:
                maps_iframe = soup.find(
                    "iframe", src=re.compile(r"google\.com/maps", re.I)
                )
                if maps_iframe:
                    result["has_map"] = maps_iframe.get("src", "")

        # ── 7. Country default ─────────────────────────────────────────────────
        # Default to US unless scraping found something else
        if not result.get("country"):
            result["country"] = "US"

    except Exception:
        pass

    return {k: v for k, v in result.items() if v}


def _merge_from_schema(result: dict, s: dict) -> None:
    """Merge LocalBusiness/Organization JSON-LD fields into result dict."""
    if s.get("telephone") and not result.get("telephone"):
        result["telephone"] = s["telephone"]

    if s.get("email") and not result.get("email"):
        result["email"] = s["email"]

    if s.get("priceRange") and not result.get("price_range"):
        result["price_range"] = s["priceRange"]

    if s.get("hasMap") and not result.get("has_map"):
        result["has_map"] = s["hasMap"]

    if s.get("name") and not result.get("business_name"):
        result["business_name"] = s["name"]

    if s.get("description") and not result.get("description"):
        result["description"] = s["description"]

    # Logo
    logo = s.get("logo")
    if logo and not result.get("logo_url"):
        if isinstance(logo, dict):
            result["logo_url"] = logo.get("url", logo.get("contentUrl", ""))
        elif isinstance(logo, str):
            result["logo_url"] = logo

    # Image
    image = s.get("image")
    if image and not result.get("image_url"):
        if isinstance(image, list):
            image = image[0]
        if isinstance(image, dict):
            result["image_url"] = image.get("url", image.get("contentUrl", ""))
        elif isinstance(image, str):
            result["image_url"] = image

    # Address
    addr = s.get("address", {})
    if isinstance(addr, dict) and addr:
        if addr.get("streetAddress") and not result.get("street_address"):
            result["street_address"] = addr["streetAddress"]
        if addr.get("addressLocality") and not result.get("city"):
            result["city"] = addr["addressLocality"]
        if addr.get("addressRegion") and not result.get("state"):
            result["state"] = addr["addressRegion"]
        if addr.get("postalCode") and not result.get("postal_code"):
            result["postal_code"] = addr["postalCode"]
        if addr.get("addressCountry") and not result.get("country"):
            result["country"] = addr["addressCountry"]

    # Opening hours
    hours = s.get("openingHoursSpecification")
    if hours and not result.get("opening_hours"):
        parsed = _parse_opening_hours(hours)
        if parsed:
            result["opening_hours"] = parsed

    # Geo coordinates
    geo = s.get("geo", {})
    if isinstance(geo, dict) and not result.get("latitude"):
        result["latitude"] = geo.get("latitude", "")
        result["longitude"] = geo.get("longitude", "")

    # Aggregate rating
    rating = s.get("aggregateRating", {})
    if isinstance(rating, dict) and not result.get("aggregate_rating_value"):
        result["aggregate_rating_value"] = str(rating.get("ratingValue", ""))
        result["aggregate_rating_count"] = str(rating.get("reviewCount", ""))

    # sameAs
    same_as = s.get("sameAs")
    if same_as and not result.get("same_as"):
        if isinstance(same_as, str):
            same_as = [same_as]
        result["same_as"] = [u for u in same_as if u]


def _find_logo(soup: BeautifulSoup, base_url: str) -> str:
    """Try to find a logo image on the page."""
    # Common logo patterns: class, id, alt, src containing "logo"
    for attr in ("class", "id"):
        el = soup.find(
            "img",
            attrs={attr: re.compile(r"logo", re.I)},
        )
        if el and el.get("src"):
            return urljoin(base_url, el["src"])

    el = soup.find("img", alt=re.compile(r"logo", re.I))
    if el and el.get("src"):
        return urljoin(base_url, el["src"])

    # Logo inside a header/nav
    header = soup.find(["header", "nav"])
    if header:
        img = header.find("img")
        if img and img.get("src"):
            return urljoin(base_url, img["src"])

    return ""


def _parse_opening_hours(hours_data) -> list:
    """Convert openingHoursSpecification JSON-LD to our internal format."""
    if not isinstance(hours_data, list):
        hours_data = [hours_data]

    result = []
    day_map = {
        "Monday": "Monday", "Tuesday": "Tuesday", "Wednesday": "Wednesday",
        "Thursday": "Thursday", "Friday": "Friday", "Saturday": "Saturday",
        "Sunday": "Sunday",
        "https://schema.org/Monday": "Monday",
        "https://schema.org/Tuesday": "Tuesday",
        "https://schema.org/Wednesday": "Wednesday",
        "https://schema.org/Thursday": "Thursday",
        "https://schema.org/Friday": "Friday",
        "https://schema.org/Saturday": "Saturday",
        "https://schema.org/Sunday": "Sunday",
    }

    for entry in hours_data:
        if not isinstance(entry, dict):
            continue
        days = entry.get("dayOfWeek", [])
        if isinstance(days, str):
            days = [days]
        opens = entry.get("opens", "")
        closes = entry.get("closes", "")
        for day in days:
            mapped = day_map.get(day, "")
            if mapped and opens and closes:
                result.append({"day": mapped, "opens": opens, "closes": closes})

    return result
