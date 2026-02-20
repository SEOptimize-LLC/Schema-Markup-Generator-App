"""
Shared builder functions used by all schema generators.
"""
import re
from src.utils.helpers import normalize_url, build_id, clean_dict


def make_context() -> str:
    return "https://schema.org"


def _ensure_https(url: str) -> str:
    """Normalize http:// → https:// on asset URLs."""
    if url and url.startswith("http://"):
        return "https://" + url[7:]
    return url


def make_postal_address(data: dict) -> dict:
    return clean_dict({
        "@type": "PostalAddress",
        "streetAddress": data.get("street_address", ""),
        "addressLocality": data.get("city", ""),
        "addressRegion": data.get("state", ""),
        "postalCode": data.get("postal_code", ""),
        "addressCountry": data.get("country", ""),
    })


def make_geo(lat: str, lng: str) -> dict:
    """lat/lng are output as Number (float) per schema.org spec."""
    if not lat or not lng:
        return {}
    try:
        return {
            "@type": "GeoCoordinates",
            "latitude": float(lat),
            "longitude": float(lng),
        }
    except (ValueError, TypeError):
        return {}


def make_geo_shape(postal_codes: list[str]) -> dict:
    if not postal_codes:
        return {}
    return {
        "@type": "GeoShape",
        "postalCode": postal_codes,
    }


def make_aggregate_rating(data: dict) -> dict:
    """Build AggregateRating with correct numeric types."""
    value = data.get("aggregate_rating_value", "")
    count = data.get("aggregate_rating_count", "")
    if not value or not count:
        return {}
    try:
        return {
            "@type": "AggregateRating",
            "ratingValue": float(value),
            "reviewCount": int(str(count).replace(",", "")),
            "bestRating": 5,
            "worstRating": 1,
        }
    except (ValueError, TypeError):
        return {}


def make_service_area(data: dict) -> dict:
    """Build GeoCircle serviceArea when coordinates and radius are present."""
    lat = data.get("latitude", "")
    lng = data.get("longitude", "")
    radius = data.get("service_radius", "")
    if not lat or not lng or not radius:
        return {}
    try:
        return {
            "@type": "GeoCircle",
            "geoMidpoint": {
                "@type": "GeoCoordinates",
                "latitude": float(lat),
                "longitude": float(lng),
            },
            "geoRadius": str(radius),
        }
    except (ValueError, TypeError):
        return {}


def _is_valid_place_name(name: str, brand_words: set | None = None) -> bool:
    """Return False for names that look like SEO page titles, postal codes, or brand-prefixed strings."""
    if not name or not name.strip():
        return False
    name = name.strip()
    # Reject purely numeric strings (postal codes leaking in)
    if name.isdigit():
        return False
    # Reject names containing digits (e.g. "Area 84101", "18387")
    if any(ch.isdigit() for ch in name):
        return False
    # Reject meta-names
    if name.lower() in {"locations", "location", "areas", "area", "service area",
                        "service areas", "areas we serve", "cities we serve"}:
        return False
    # Reject long SEO-title-style strings
    if len(name) > 40:
        return False
    # Reject strings with SEO separators
    for bad in (" - ", " | ", " – ", " — "):
        if bad in name:
            return False
    # Reject names containing industry keywords
    for bad in ("Plumbing", "Plumber", "HVAC", "Heating", "Cooling",
                "Dentist", "Dental", "Lawyer", "Attorney", "Electrician",
                "Contractor", "Roofing", "Roofer"):
        if bad in name:
            return False
    # Reject names whose first word is a known brand word (e.g. "Beehive Murray")
    if brand_words:
        first_word = name.split()[0].lower()
        if first_word in brand_words:
            return False
    return True


def make_area_served(data: dict) -> list | dict:
    """
    Build areaServed as a list with AdministrativeArea for counties
    and City for named cities. Falls back to single AdministrativeArea
    or Country if minimal data.
    """
    postal_codes = data.get("postal_codes", [])
    cities = data.get("cities", [])
    country = data.get("country", "")
    area_name = data.get("area_served_name", "")

    # Extract brand words from business name to filter "Beehive Murray" style entries
    brand_words: set[str] = set()
    if data.get("business_name"):
        brand_words = {w.lower() for w in data["business_name"].split() if len(w) > 3}

    # Filter garbage city names
    clean_cities = [c for c in cities if _is_valid_place_name(c, brand_words)]

    if not postal_codes and not clean_cities:
        if area_name:
            return {"@type": "AdministrativeArea", "name": area_name}
        if country:
            return {"@type": "Country", "name": country}
        return {}

    places = []
    for name in clean_cities:
        place_type = (
            "AdministrativeArea"
            if "County" in name or "Region" in name or "District" in name
            else "City"
        )
        # Only add Wikipedia sameAs for short, clean names (≤ 3 words, no commas)
        entry: dict = {"@type": place_type, "name": name}
        words = name.split()
        if len(words) <= 3 and "," not in name:
            entry["sameAs"] = f"https://en.wikipedia.org/wiki/{name.replace(' ', '_')}"
        places.append(entry)

    if postal_codes and not places:
        return {
            "@type": "AdministrativeArea",
            "name": area_name or country,
            "geo": make_geo_shape(postal_codes),
        }

    if postal_codes:
        places.append({
            "@type": "AdministrativeArea",
            "geo": make_geo_shape(postal_codes),
        })

    return places if len(places) > 1 else places[0] if places else {}


def make_opening_hours(hours: list[dict]) -> list[dict]:
    """
    hours: list of {day, opens, closes}
    Consolidates days with the same hours into a single spec.
    Uses "24:00" closes for true 24/7 (per Google's recommendation).
    """
    if not hours:
        return []

    groups: dict[tuple, list] = {}
    for h in hours:
        if not h.get("day"):
            continue
        opens = h.get("opens", "09:00")
        closes = h.get("closes", "17:00")
        # Normalize 23:59 → 24:00 for midnight-spanning all-day specs
        if opens == "00:00" and closes == "23:59":
            closes = "24:00"
        key = (opens, closes)
        groups.setdefault(key, []).append(h["day"])

    result = []
    for (opens, closes), days in groups.items():
        result.append({
            "@type": "OpeningHoursSpecification",
            "dayOfWeek": days if len(days) > 1 else days[0],
            "opens": opens,
            "closes": closes,
        })
    return result


def make_image_object(url: str) -> dict:
    if not url:
        return {}
    url = _ensure_https(url)
    return {"@type": "ImageObject", "contentUrl": url, "url": url}


def make_logo(url: str) -> dict:
    if not url:
        return {}
    url = _ensure_https(url)
    return {"@type": "ImageObject", "contentUrl": url, "url": url}


def make_contact_point(telephone: str, email: str = "") -> dict:
    cp = {"@type": "ContactPoint", "contactType": "Customer Service"}
    if telephone:
        cp["telephone"] = telephone
    if email:
        cp["email"] = email
    return cp


def make_knows_about(items: list[dict]) -> list[dict]:
    """
    items: list of {name, wikidata_id, wikipedia_url}
    Uses Wikipedia URL as sameAs only — Wikidata @id is omitted because
    AI-generated Q-IDs are unreliable and frequently hallucinated.
    """
    result = []
    for item in items:
        if not item.get("name"):
            continue
        thing: dict = {"@type": "Thing", "name": item["name"]}
        # Use Wikipedia URL as sameAs (human-verifiable, accurate)
        if item.get("wikipedia_url"):
            thing["sameAs"] = item["wikipedia_url"]
        result.append(thing)
    return result


def make_same_as(urls: list[str]) -> list[str]:
    return [u for u in urls if u and not u.startswith("FILL-IN:")]


def _clean_service_type(raw: str) -> str:
    """Strip SEO location suffixes and separators from a service name."""
    # Split on common SEO separators and take the first part
    for sep in (" in ", " - ", " | ", " – ", " — ", " | "):
        if sep in raw:
            raw = raw.split(sep)[0].strip()
    # Remove trailing punctuation
    raw = raw.rstrip(".,;:")
    return raw.strip()


def make_has_offer_catalog(services: list[dict], org_id: str, catalog_name: str = "") -> dict:
    """
    Build hasOfferCatalog from a list of service dicts.
    Filters deprecated -old URLs and cleans serviceType values.
    Each service: {name, url, service_type, description, audience}
    """
    items = []
    for svc in services:
        if not svc.get("name"):
            continue
        url = svc.get("url", "")
        # Skip deprecated -old or _old slug variants
        slug = url.rstrip("/").split("/")[-1].lower()
        if slug.endswith("-old") or slug.endswith("_old"):
            continue

        raw_type = svc.get("service_type", svc.get("name", ""))
        service_type = _clean_service_type(raw_type)

        offered = clean_dict({
            "@type": "Service",
            "name": svc.get("name", ""),
            "url": url,
            "serviceType": service_type,
            "description": svc.get("description", ""),
            "provider": {"@id": org_id},
        })
        if svc.get("audience"):
            offered["audience"] = {"@type": "Audience", "audienceType": svc["audience"]}
        items.append({"@type": "Offer", "itemOffered": offered})

    if not items:
        return {}
    return clean_dict({
        "@type": "OfferCatalog",
        "name": catalog_name,
        "itemListElement": items,
    })


def make_offer(data: dict) -> dict:
    offer = clean_dict({
        "@type": "Offer",
        "name": data.get("offer_name", ""),
        "url": data.get("offer_url", ""),
        "priceCurrency": data.get("currency", ""),
    })
    if data.get("low_price"):
        offer["lowPrice"] = data["low_price"]
    if data.get("high_price"):
        offer["highPrice"] = data["high_price"]
    if data.get("price"):
        offer["price"] = data["price"]
    return offer
