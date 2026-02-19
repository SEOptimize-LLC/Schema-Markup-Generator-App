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
        "latitude": lat,
        "longitude": lng,
    }


def make_geo_shape(postal_codes: list[str]) -> dict:
    if not postal_codes:
        return {}
    return {
        "@type": "GeoShape",
        "postalCode": postal_codes,
    }


def make_area_served(data: dict) -> dict | list:
    """
    Build areaServed with GeoShape + containsPlace cities.
    Falls back to simple Country or AdministrativeArea if minimal data.
    """
    postal_codes = data.get("postal_codes", [])
    cities = data.get("cities", [])
    country = data.get("country", "")
    area_name = data.get("area_served_name", "")

    if not postal_codes and not cities:
        if area_name:
            return {"@type": "AdministrativeArea", "name": area_name}
        if country:
            return {"@type": "Country", "name": country}
        return {}

    area = {"@type": "AdministrativeArea"}

    if postal_codes:
        area["geo"] = make_geo_shape(postal_codes)

    if cities:
        area["containsPlace"] = [
            {
                "@type": "City",
                "name": city,
                "url": [
                    f"https://www.google.com/maps/place/{city.replace(' ', '+')}/",
                    f"https://en.wikipedia.org/wiki/{city.replace(' ', '_')}",
                ],
            }
            for city in cities
            if city.strip()
        ]

    return area


def make_opening_hours(hours: list[dict]) -> list[dict]:
    """
    hours: list of {day, opens, closes}
    """
    if not hours:
        return []
    return [
        {
            "@type": "OpeningHoursSpecification",
            "dayOfWeek": h.get("day", ""),
            "opens": h.get("opens", "09:00"),
            "closes": h.get("closes", "17:00"),
        }
        for h in hours
        if h.get("day")
    ]


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


def make_offer(data: dict) -> dict:
    offer = clean_dict({
        "@type": "Offer",
        "name": data.get("offer_name", ""),
        "url": data.get("offer_url", ""),
        "priceCurrency": data.get("currency", ""),
        "businessFunction": "http://purl.org/goodrelations/v1#ProvideService",
    })
    if data.get("low_price"):
        offer["lowPrice"] = data["low_price"]
    if data.get("high_price"):
        offer["highPrice"] = data["high_price"]
    if data.get("price"):
        offer["price"] = data["price"]
    return offer
