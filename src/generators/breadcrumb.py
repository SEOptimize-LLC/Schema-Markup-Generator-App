"""
BreadcrumbList schema generator.
"""
from src.generators.base import make_context
from src.utils.helpers import normalize_url, build_id, clean_dict


def generate_breadcrumb(data: dict) -> dict:
    """
    BreadcrumbList schema.
    data["breadcrumb_items"] = list of {name, url}
    """
    base_url = normalize_url(data.get("website_url", ""))
    page_url = normalize_url(data.get("current_page_url", base_url))
    org_id = build_id(base_url, "organization")
    website_id = build_id(base_url, "website")

    items = data.get("breadcrumb_items", [])

    if not items:
        items = [{"name": "Home", "url": base_url}]

    list_elements = [
        {
            "@type": "ListItem",
            "position": idx + 1,
            "name": item.get("name", ""),
            "item": normalize_url(item.get("url", base_url)),
        }
        for idx, item in enumerate(items)
        if item.get("name")
    ]

    schema = {
        "@context": make_context(),
        "@type": "BreadcrumbList",
        "@id": build_id(page_url, "breadcrumb"),
        "itemListElement": list_elements,
    }

    return clean_dict(schema)
