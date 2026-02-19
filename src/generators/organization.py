"""
Organization and LocalBusiness schema generators.
"""
from src.generators.base import (
    make_context, make_postal_address, make_area_served, make_opening_hours,
    make_image_object, make_logo, make_contact_point, make_knows_about,
    make_same_as, make_offer, make_geo, make_aggregate_rating,
    make_service_area, make_has_offer_catalog,
)
from src.utils.helpers import build_id, normalize_url, clean_dict


def generate_organization(data: dict) -> dict:
    """
    Generate a full Organization schema.
    Used for SaaS / e-commerce / non-local businesses.
    """
    base_url = normalize_url(data.get("website_url", ""))
    org_id = build_id(base_url, "organization")
    person_id = build_id(base_url, "person")

    schema = {
        "@context": make_context(),
        "@type": "Organization",
        "@id": org_id,
        "name": data.get("business_name", ""),
        "legalName": data.get("legal_name", "") or data.get("business_name", ""),
        "alternateName": data.get("alternate_name", ""),
        "url": base_url,
        "description": data.get("description", ""),
        "disambiguatingDescription": data.get("disambiguating_description", ""),
        "slogan": data.get("slogan", ""),
        "foundingDate": data.get("founding_date", ""),
        "foundingLocation": data.get("founding_location", ""),
        "email": data.get("email", ""),
        "telephone": data.get("telephone", ""),
    }

    if data.get("additional_types"):
        schema["additionalType"] = data["additional_types"]

    if data.get("logo_url"):
        schema["logo"] = make_logo(data["logo_url"])

    if data.get("image_url"):
        schema["image"] = make_image_object(data["image_url"])

    knows_about_items = data.get("knows_about", [])
    if knows_about_items:
        schema["knowsAbout"] = make_knows_about(knows_about_items)

    same_as = make_same_as(data.get("same_as", []))
    if same_as:
        schema["sameAs"] = same_as

    if data.get("telephone") or data.get("email"):
        schema["contactPoint"] = make_contact_point(
            data.get("telephone", ""), data.get("email", "")
        )

    if data.get("founder_name"):
        schema["founder"] = {
            "@type": "Person",
            "@id": person_id,
            "name": data["founder_name"],
        }

    if data.get("parent_organization"):
        schema["parentOrganization"] = {"@type": "Organization", "name": data["parent_organization"]}

    area = make_area_served(data)
    if area:
        schema["areaServed"] = area

    rating = make_aggregate_rating(data)
    if rating:
        schema["aggregateRating"] = rating

    return clean_dict(schema)


def generate_local_business(data: dict) -> dict:
    """
    Generate a LocalBusiness schema with full address, hours, areaServed.
    Supports specific subtypes (HVACBusiness, Dentist, LegalService, etc.)
    """
    base_url = normalize_url(data.get("website_url", ""))
    org_id = build_id(base_url, "organization")
    person_id = build_id(base_url, "person")

    schema_type = data.get("schema_subtype", "LocalBusiness")
    if schema_type in ("Organization", "OnlineBusiness", ""):
        schema_type = "LocalBusiness"

    schema = {
        "@context": make_context(),
        "@type": schema_type,
        "@id": org_id,
        "name": data.get("business_name", ""),
        "legalName": data.get("legal_name", "") or data.get("business_name", ""),
        "alternateName": data.get("alternate_name", ""),
        "url": base_url,
        "description": data.get("description", ""),
        "disambiguatingDescription": data.get("disambiguating_description", ""),
        "slogan": data.get("slogan", ""),
        "priceRange": data.get("price_range", ""),
        "email": data.get("email", ""),
        "telephone": data.get("telephone", ""),
        "paymentAccepted": data.get("payment_accepted", ""),
        "currenciesAccepted": data.get("currencies_accepted", ""),
        "foundingDate": data.get("founding_date", ""),
        "foundingLocation": data.get("founding_location", ""),
    }

    # additionalType: Schema.org types only, then user-supplied Wikipedia/Wikidata URLs
    add_types = ["LocalBusiness", "Organization"]
    if data.get("additional_types"):
        for t in data["additional_types"]:
            if t not in add_types:
                add_types.append(t)
    schema["additionalType"] = add_types

    if data.get("logo_url"):
        schema["logo"] = make_logo(data["logo_url"])

    if data.get("image_url"):
        schema["image"] = make_image_object(data["image_url"])

    if data.get("has_map"):
        schema["hasMap"] = data["has_map"]

    address = make_postal_address(data)
    if address:
        schema["address"] = address

    geo = make_geo(data.get("latitude", ""), data.get("longitude", ""))
    if geo:
        schema["geo"] = geo

    knows_about_items = data.get("knows_about", [])
    if knows_about_items:
        schema["knowsAbout"] = make_knows_about(knows_about_items)

    same_as = make_same_as(data.get("same_as", []))
    if same_as:
        schema["sameAs"] = same_as

    if data.get("telephone") or data.get("email"):
        schema["contactPoint"] = make_contact_point(
            data.get("telephone", ""), data.get("email", "")
        )

    hours = make_opening_hours(data.get("opening_hours", []))
    if hours:
        schema["openingHoursSpecification"] = hours

    area = make_area_served(data)
    if area:
        schema["areaServed"] = area

    service_area = make_service_area(data)
    if service_area:
        schema["serviceArea"] = service_area

    rating = make_aggregate_rating(data)
    if rating:
        schema["aggregateRating"] = rating

    # hasOfferCatalog — curated service catalog
    services = data.get("services", [])
    if services:
        catalog_name = f"{data.get('business_name', '')} Services".strip()
        catalog = make_has_offer_catalog(services, org_id, catalog_name)
        if catalog:
            schema["hasOfferCatalog"] = catalog

    # makesOffer — special offers (Free Estimates, Financing, etc.)
    special_offers = data.get("special_offers", [])
    if special_offers:
        schema["makesOffer"] = [
            clean_dict({
                "@type": "Offer",
                "name": o.get("name", ""),
                "description": o.get("description", ""),
            })
            for o in special_offers if o.get("name")
        ]

    if data.get("founder_name"):
        schema["founder"] = {
            "@type": "Person",
            "@id": person_id,
            "name": data["founder_name"],
        }

    return clean_dict(schema)


def generate_multi_location_org(data: dict) -> dict:
    """
    Generate an Organization with multiple LocalBusiness departments.
    data["locations"] is a list of location dicts.
    """
    base_url = normalize_url(data.get("website_url", ""))
    org_id = build_id(base_url, "organization")

    schema = {
        "@context": make_context(),
        "@type": "Organization",
        "@id": org_id,
        "name": data.get("business_name", ""),
        "url": base_url,
        "description": data.get("description", ""),
        "email": data.get("email", ""),
        "telephone": data.get("telephone", ""),
    }

    if data.get("logo_url"):
        schema["logo"] = make_logo(data["logo_url"])

    same_as = make_same_as(data.get("same_as", []))
    if same_as:
        schema["sameAs"] = same_as

    locations = data.get("locations", [])
    if locations:
        departments = []
        for idx, loc in enumerate(locations):
            dept = {
                "@type": "LocalBusiness",
                "@id": build_id(base_url, f"location-{idx + 1}"),
                "name": loc.get("name", data.get("business_name", "")),
                "url": loc.get("url", base_url),
                "telephone": loc.get("telephone", ""),
                "email": loc.get("email", ""),
                "address": make_postal_address(loc),
            }
            if loc.get("opening_hours"):
                dept["openingHoursSpecification"] = make_opening_hours(loc["opening_hours"])
            departments.append(clean_dict(dept))
        schema["department"] = departments

    return clean_dict(schema)
