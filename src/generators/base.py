"""
Shared builder functions used by all schema generators.
"""
from src.utils.helpers import normalize_url, build_id, clean_dict


def make_context() -> str:
    return "https://schema.org"


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
    if not lat or not lng:
        return {}
    return {
        "@type": "GeoCoordinates",
        "latitude": str(lat),
        "longitude": str(lng),
    }


def make_geo_shape(postal_codes: list[str]) -> dict:
    if not postal_codes:
        return {}
    return {
        "@type": "GeoShape",
        "postalCode": postal_codes,
    }


def make_aggregate_rating(data: dict) -> dict:
    """Build AggregateRating if rating value and count are present."""
    value = data.get("aggregate_rating_value", "")
    count = data.get("aggregate_rating_count", "")
    if not value or not count:
        return {}
    return clean_dict({
        "@type": "AggregateRating",
        "ratingValue": str(value),
        "reviewCount": str(count),
        "bestRating": "5",
        "worstRating": "1",
    })


def make_service_area(data: dict) -> dict:
    """Build GeoCircle serviceArea when coordinates and radius are present."""
    lat = data.get("latitude", "")
    lng = data.get("longitude", "")
    radius = data.get("service_radius", "")
    if not lat or not lng or not radius:
        return {}
    return {
        "@type": "GeoCircle",
        "geoMidpoint": {
            "@type": "GeoCoordinates",
            "latitude": str(lat),
            "longitude": str(lng),
        },
        "geoRadius": str(radius),
    }


def _is_valid_place_name(name: str) -> bool:
    """Return False for names that look like SEO page titles, not place names."""
    if not name or not name.strip():
        return False
    if len(name) > 60:
        return False
    for bad in (" - ", " | ", " – ", " — ", "Plumbing", "Plumber", "HVAC",
                "Dentist", "Lawyer", "Attorney", "Electrician", "Contractor"):
        if bad in name:
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

    # Filter out garbage city names from sitemap scraping
    clean_cities = [c for c in cities if _is_valid_place_name(c)]

    if not postal_codes and not clean_cities:
        if area_name:
            return {"@type": "AdministrativeArea", "name": area_name}
        if country:
            return {"@type": "Country", "name": country}
        return {}

    places = []
    for name in clean_cities:
        place_type = "AdministrativeArea" if "County" in name or "Region" in name or "District" in name else "City"
        entry = {
            "@type": place_type,
            "name": name,
        }
        # Only add Wikipedia URL for short, clean city/county names
        if len(name) <= 40:
            entry["sameAs"] = f"https://en.wikipedia.org/wiki/{name.replace(' ', '_')}"
        places.append(entry)

    if postal_codes and not places:
        # Postal code only — use GeoShape
        return {
            "@type": "AdministrativeArea",
            "name": area_name or country,
            "geo": make_geo_shape(postal_codes),
        }

    if postal_codes:
        # Append GeoShape entry alongside named places
        places.append({
            "@type": "AdministrativeArea",
            "geo": make_geo_shape(postal_codes),
        })

    return places if len(places) > 1 else places[0] if places else {}


def make_opening_hours(hours: list[dict]) -> list[dict]:
    """
    hours: list of {day, opens, closes}
    Consolidates consecutive days with the same hours into a single spec.
    """
    if not hours:
        return []

    # Group by (opens, closes) to consolidate matching days
    groups: dict[tuple, list] = {}
    for h in hours:
        if not h.get("day"):
            continue
        key = (h.get("opens", "09:00"), h.get("closes", "17:00"))
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
    return {"@type": "ImageObject", "contentUrl": url, "url": url}


def make_logo(url: str) -> dict:
    if not url:
        return {}
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
    Returns list of schema Thing objects with @id pointing to Wikidata.
    """
    result = []
    for item in items:
        if not item.get("name"):
            continue
        thing = {"@type": "Thing", "name": item["name"]}
        if item.get("wikidata_id"):
            thing["@id"] = item["wikidata_id"]
        if item.get("wikipedia_url"):
            thing["sameAs"] = item["wikipedia_url"]
        result.append(thing)
    return result


def make_same_as(urls: list[str]) -> list[str]:
    return [u for u in urls if u and not u.startswith("FILL-IN:")]


def make_has_offer_catalog(services: list[dict], org_id: str, catalog_name: str = "") -> dict:
    """
    Build hasOfferCatalog from a list of service dicts.
    Each service: {name, url, service_type, description, audience}
    """
    items = []
    for svc in services:
        if not svc.get("name"):
            continue
        offered = clean_dict({
            "@type": "Service",
            "name": svc.get("name", ""),
            "url": svc.get("url", ""),
            "serviceType": svc.get("service_type", svc.get("name", "")),
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
