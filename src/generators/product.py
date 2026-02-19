"""
Product schema generator for e-commerce.
Includes Offer, AggregateRating, Review, brand @id.
"""
from src.generators.base import make_context
from src.utils.helpers import build_id, normalize_url, clean_dict


def generate_product(data: dict) -> dict:
    """
    Product schema with full Merchant Center compatible structure.
    """
    base_url = normalize_url(data.get("website_url", ""))
    product_url = normalize_url(data.get("product_url", ""))
    org_id = build_id(base_url, "organization")

    images = data.get("product_images", [])
    if data.get("product_image") and data["product_image"] not in images:
        images = [data["product_image"]] + images

    schema = {
        "@context": make_context(),
        "@type": "Product",
        "@id": product_url or base_url,
        "name": data.get("product_name", ""),
        "description": data.get("product_description", ""),
        "disambiguatingDescription": data.get("product_disambiguating", ""),
        "sku": data.get("sku", ""),
        "mpn": data.get("mpn", ""),
        "gtin": data.get("gtin", ""),
        "gtin13": data.get("gtin13", ""),
        "url": product_url,
        "color": data.get("color", ""),
        "material": data.get("material", ""),
        "pattern": data.get("pattern", ""),
        "category": data.get("category", ""),
        "slogan": data.get("product_slogan", ""),
    }

    if images:
        schema["image"] = images if len(images) > 1 else images[0]

    schema["brand"] = {"@id": org_id}
    schema["manufacturer"] = {"@id": org_id}

    if data.get("is_related_to"):
        schema["isRelatedTo"] = data["is_related_to"]

    offers = _build_offers(data, org_id, product_url)
    if offers:
        schema["offers"] = offers

    if data.get("aggregate_rating_value") and data.get("aggregate_rating_count"):
        schema["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": data["aggregate_rating_value"],
            "reviewCount": data["aggregate_rating_count"],
            "bestRating": data.get("best_rating", "5"),
            "worstRating": data.get("worst_rating", "1"),
        }

    reviews = data.get("reviews", [])
    if reviews:
        schema["review"] = [
            clean_dict({
                "@type": "Review",
                "author": {"@type": "Person", "name": r.get("author", "")},
                "datePublished": r.get("date", ""),
                "name": r.get("title", ""),
                "reviewBody": r.get("body", ""),
                "reviewRating": {
                    "@type": "Rating",
                    "ratingValue": r.get("rating", "5"),
                    "bestRating": "5",
                    "worstRating": "1",
                },
            })
            for r in reviews
            if r.get("author") and r.get("body")
        ]

    return clean_dict(schema)


def _build_offers(data: dict, org_id: str, product_url: str) -> dict | None:
    price = data.get("price", "")
    currency = data.get("currency", "USD")
    if not price:
        return None

    availability_map = {
        "In Stock": "https://schema.org/InStock",
        "Out of Stock": "https://schema.org/OutOfStock",
        "Pre-order": "https://schema.org/PreOrder",
        "Discontinued": "https://schema.org/Discontinued",
    }
    availability_label = data.get("availability", "In Stock")
    availability_url = availability_map.get(availability_label, "https://schema.org/InStock")

    offer = {
        "@type": "Offer",
        "url": product_url,
        "priceCurrency": currency,
        "price": price,
        "priceValidUntil": data.get("price_valid_until", ""),
        "itemCondition": "https://schema.org/NewCondition",
        "availability": availability_url,
        "seller": {"@id": org_id},
    }

    if data.get("shipping_rate") is not None:
        offer["shippingDetails"] = {
            "@type": "OfferShippingDetails",
            "shippingRate": {
                "@type": "MonetaryAmount",
                "value": data.get("shipping_rate", "0"),
                "currency": currency,
            },
            "shippingDestination": {
                "@type": "DefinedRegion",
                "addressCountry": data.get("shipping_country", ""),
            },
            "deliveryTime": {
                "@type": "ShippingDeliveryTime",
                "handlingTime": {
                    "@type": "QuantitativeValue",
                    "minValue": data.get("handling_time_min", 1),
                    "maxValue": data.get("handling_time_max", 3),
                    "unitCode": "DAY",
                },
                "transitTime": {
                    "@type": "QuantitativeValue",
                    "minValue": data.get("transit_time_min", 3),
                    "maxValue": data.get("transit_time_max", 7),
                    "unitCode": "DAY",
                },
            },
        }

    if data.get("return_days"):
        offer["hasMerchantReturnPolicy"] = {
            "@type": "MerchantReturnPolicy",
            "applicableCountry": data.get("return_policy_country", ""),
            "returnPolicyCategory": "https://schema.org/MerchantReturnFiniteReturnWindow",
            "merchantReturnDays": data.get("return_days", 30),
            "returnMethod": f"https://schema.org/{data.get('return_method', 'ReturnByMail')}",
            "returnFees": f"https://schema.org/{data.get('return_fees', 'FreeReturn')}",
        }

    return clean_dict(offer)
