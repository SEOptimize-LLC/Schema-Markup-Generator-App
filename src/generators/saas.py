"""
SaaS / WebApplication schema generator.
Covers WebApplication, pricing page with AggregateOffer + UnitPriceSpecification.
"""
from src.generators.base import make_context, make_knows_about
from src.utils.helpers import build_id, normalize_url, clean_dict


def generate_saas_app(data: dict) -> dict:
    """
    WebApplication schema for a SaaS product.
    """
    base_url = normalize_url(data.get("website_url", ""))
    app_url = normalize_url(data.get("app_url", base_url))
    org_id = build_id(base_url, "organization")
    app_id = build_id(app_url, "webapp")
    website_id = build_id(base_url, "website")

    schema = {
        "@context": make_context(),
        "@type": "WebApplication",
        "@id": app_id,
        "name": data.get("app_name", data.get("business_name", "")),
        "description": data.get("app_description", data.get("description", "")),
        "url": app_url,
        "sameAs": data.get("marketing_url", base_url),
        "browserRequirements": data.get("browser_requirements", "Requires JavaScript. Requires HTML5."),
        "applicationCategory": data.get("app_category", "BusinessApplication"),
        "applicationSuite": data.get("app_suite", ""),
        "operatingSystem": data.get("operating_system", "Web Browser"),
        "permissions": data.get("permissions", ""),
        "releaseNotes": data.get("release_notes_url", ""),
        "provider": {"@id": org_id},
    }

    pricing = data.get("pricing_tiers", [])
    if not pricing and data.get("price"):
        schema["offers"] = {
            "@type": "Offer",
            "price": data.get("price", "0"),
            "priceCurrency": data.get("currency", "USD"),
        }
    elif pricing:
        if len(pricing) == 1:
            t = pricing[0]
            schema["offers"] = clean_dict({
                "@type": "Offer",
                "name": t.get("name", ""),
                "price": t.get("price", ""),
                "priceCurrency": data.get("currency", "USD"),
                "url": t.get("url", base_url),
            })
        else:
            schema["offers"] = {
                "@type": "AggregateOffer",
                "lowPrice": min(
                    (float(t["price"]) for t in pricing if t.get("price") and str(t["price"]).replace(".", "").isdigit()),
                    default=0,
                ),
                "highPrice": max(
                    (float(t["price"]) for t in pricing if t.get("price") and str(t["price"]).replace(".", "").isdigit()),
                    default=0,
                ),
                "priceCurrency": data.get("currency", "USD"),
                "offerCount": len(pricing),
                "offers": [
                    clean_dict({
                        "@type": "Offer",
                        "name": t.get("name", ""),
                        "url": t.get("url", base_url),
                        "price": t.get("price", ""),
                        "priceCurrency": data.get("currency", "USD"),
                        "priceSpecification": {
                            "@type": "UnitPriceSpecification",
                            "price": t.get("price", ""),
                            "priceCurrency": data.get("currency", "USD"),
                            "name": t.get("name", ""),
                            "referenceQuantity": {
                                "@type": "QuantitativeValue",
                                "value": "1",
                                "unitCode": t.get("billing_period", "MON"),
                            },
                        },
                    })
                    for t in pricing
                    if t.get("name")
                ],
            }

    schema["isPartOf"] = {
        "@type": "WebSite",
        "@id": website_id,
        "url": base_url,
        "publisher": {"@id": org_id},
    }

    return clean_dict(schema)


def generate_saas_pricing_page(data: dict) -> dict:
    """
    Pricing page for SaaS with full WebPage + WebApplication + AggregateOffer.
    Uses @graph.
    """
    base_url = normalize_url(data.get("website_url", ""))
    pricing_url = normalize_url(data.get("pricing_page_url", f"{base_url}/pricing"))
    org_id = build_id(base_url, "organization")
    website_id = build_id(base_url, "website")
    webpage_id = build_id(pricing_url, "webpage")
    app_id = build_id(normalize_url(data.get("app_url", base_url)), "webapp")

    pricing_tiers = data.get("pricing_tiers", [])
    currency = data.get("currency", "USD")

    prices = [float(t["price"]) for t in pricing_tiers if t.get("price") and str(t["price"]).replace(".", "").isdigit()]

    aggregate_offer = clean_dict({
        "@type": "AggregateOffer",
        "@id": build_id(pricing_url, "aggregateoffer"),
        "url": pricing_url,
        "lowPrice": str(min(prices)) if prices else "",
        "highPrice": str(max(prices)) if prices else "",
        "priceCurrency": currency,
        "offerCount": len(pricing_tiers),
        "offers": [
            clean_dict({
                "@type": "Offer",
                "name": t.get("name", ""),
                "url": t.get("url", pricing_url),
                "description": t.get("description", ""),
                "priceSpecification": {
                    "@type": "UnitPriceSpecification",
                    "price": t.get("price", ""),
                    "priceCurrency": currency,
                    "name": t.get("name", ""),
                    "referenceQuantity": {
                        "@type": "QuantitativeValue",
                        "value": "1",
                        "unitCode": t.get("billing_period", "MON"),
                    },
                },
            })
            for t in pricing_tiers
            if t.get("name") and t.get("price")
        ],
        "category": {
            "@type": "Service",
            "@id": app_id,
            "name": data.get("app_name", data.get("business_name", "")),
            "serviceType": data.get("app_category", "SaaS"),
            "provider": {"@id": org_id},
        },
    })

    webpage = clean_dict({
        "@type": "WebPage",
        "@id": webpage_id,
        "url": pricing_url,
        "name": data.get("pricing_page_title", f"Pricing — {data.get('business_name', '')}"),
        "description": data.get("pricing_page_description", ""),
        "inLanguage": data.get("language", "en"),
        "mainEntity": {"@id": build_id(pricing_url, "aggregateoffer")},
        "about": {"@id": build_id(pricing_url, "aggregateoffer")},
        "isPartOf": {
            "@type": "WebSite",
            "@id": website_id,
            "url": base_url,
            "publisher": {"@id": org_id},
        },
    })

    return {"@context": make_context(), "@graph": [webpage, aggregate_offer]}
