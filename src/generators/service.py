"""
Service schema generators — single service page and multi-service page.
"""
from src.generators.base import make_context, make_area_served, make_knows_about
from src.utils.helpers import build_id, normalize_url, clean_dict


def generate_service_page(data: dict) -> dict:
    """
    Single service page schema.
    Service → provider @id Org → areaServed → hasOfferCatalog with sub-services.
    """
    base_url = normalize_url(data.get("website_url", ""))
    service_url = normalize_url(data.get("service_page_url", ""))
    org_id = build_id(base_url, "organization")
    website_id = build_id(base_url, "website")

    service_name = data.get("service_name", "")
    service_id = build_id(service_url or base_url, "service") if service_url else build_id(base_url, f"service-{service_name.lower().replace(' ', '-')}")

    area = make_area_served(data)

    service = {
        "@context": make_context(),
        "@type": "Service",
        "@id": service_id,
        "name": service_name,
        "description": data.get("service_description", ""),
        "serviceType": data.get("service_type", service_name),
        "url": service_url or base_url,
        "audience": data.get("service_audience", ""),
        "provider": {"@id": org_id},
        "brand": {"@id": org_id},
    }

    if data.get("service_additional_type"):
        service["additionalType"] = data["service_additional_type"]

    if area:
        service["areaServed"] = area

    sub_services = data.get("sub_services", [])
    if sub_services:
        service["hasOfferCatalog"] = {
            "@type": "OfferCatalog",
            "name": f"{service_name} Services",
            "itemListElement": [
                {
                    "@type": "Offer",
                    "itemOffered": {
                        "@type": "Service",
                        "name": s.get("name", ""),
                        "url": s.get("url", ""),
                        "serviceType": s.get("service_type", s.get("name", "")),
                        "audience": s.get("audience", ""),
                        "provider": {"@id": org_id},
                        "brand": {"@id": org_id},
                        "areaServed": area if area else None,
                    },
                }
                for s in sub_services
                if s.get("name")
            ],
        }

    webpage_id = build_id(service_url or base_url, "webpage")

    schema = {
        "@context": make_context(),
        "@type": "WebPage",
        "@id": webpage_id,
        "url": service_url or base_url,
        "name": data.get("service_page_title", service_name),
        "description": data.get("service_page_description", data.get("service_description", "")),
        "inLanguage": data.get("language", "en"),
        "mainEntity": clean_dict(service),
        "about": clean_dict(service),
        "isPartOf": {
            "@type": "WebSite",
            "@id": website_id,
            "url": base_url,
            "publisher": {"@id": org_id},
        },
    }

    return clean_dict(schema)


def generate_multi_service_page(data: dict) -> dict:
    """
    Multi-service page: wraps multiple service categories under one page.
    Uses @graph to connect WebPage and multiple Service schemas.
    """
    base_url = normalize_url(data.get("website_url", ""))
    services_page_url = normalize_url(data.get("services_page_url", f"{base_url}/services"))
    org_id = build_id(base_url, "organization")
    website_id = build_id(base_url, "website")
    webpage_id = build_id(services_page_url, "webpage")

    area = make_area_served(data)

    service_categories = data.get("service_categories", [])

    graph = [
        clean_dict({
            "@type": "WebPage",
            "@id": webpage_id,
            "url": services_page_url,
            "name": data.get("services_page_title", f"Services — {data.get('business_name', '')}"),
            "description": data.get("services_page_description", ""),
            "inLanguage": data.get("language", "en"),
            "about": {"@id": org_id},
            "isPartOf": {
                "@type": "WebSite",
                "@id": website_id,
                "url": base_url,
                "publisher": {"@id": org_id},
            },
        })
    ]

    for idx, cat in enumerate(service_categories):
        cat_name = cat.get("name", f"Service {idx + 1}")
        cat_url = cat.get("url", "")
        cat_id = build_id(cat_url or base_url, f"service-{idx + 1}")

        sub_items = cat.get("services", [])
        offer_catalog = None
        if sub_items:
            offer_catalog = {
                "@type": "OfferCatalog",
                "name": cat_name,
                "itemListElement": [
                    {
                        "@type": "Offer",
                        "itemOffered": {
                            "@type": "Service",
                            "name": s.get("name", ""),
                            "url": s.get("url", ""),
                            "serviceType": s.get("service_type", s.get("name", "")),
                            "provider": {"@id": org_id},
                            "brand": {"@id": org_id},
                        },
                    }
                    for s in sub_items
                    if s.get("name")
                ],
            }

        service_node = clean_dict({
            "@type": "Service",
            "@id": cat_id,
            "name": cat_name,
            "description": cat.get("description", ""),
            "serviceType": cat.get("service_type", cat_name),
            "url": cat_url or services_page_url,
            "provider": {"@id": org_id},
            "brand": {"@id": org_id},
            "areaServed": area if area else None,
            "hasOfferCatalog": offer_catalog,
        })
        graph.append(service_node)

    return {"@context": make_context(), "@graph": graph}
