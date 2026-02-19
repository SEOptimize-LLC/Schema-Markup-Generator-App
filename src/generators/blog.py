"""
BlogPosting and Article schema generators.
"""
from src.generators.base import make_context, make_knows_about, make_same_as
from src.utils.helpers import build_id, normalize_url, clean_dict


def generate_blog_post(data: dict) -> dict:
    """
    BlogPosting schema with:
    - author (Person @id)
    - publisher (Organization @id)
    - isPartOf WebSite
    - mentions (Wikidata entities)
    - image (ImageObject)
    """
    base_url = normalize_url(data.get("website_url", ""))
    post_url = normalize_url(data.get("post_url", ""))
    org_id = build_id(base_url, "organization")
    person_id = build_id(base_url, "person")
    website_id = build_id(base_url, "website")
    post_id = build_id(post_url or base_url, "blogposting")

    schema = {
        "@context": make_context(),
        "@type": "BlogPosting",
        "@id": post_id,
        "url": post_url,
        "headline": data.get("post_title", ""),
        "name": data.get("post_title", ""),
        "description": data.get("post_description", ""),
        "articleBody": data.get("article_body", ""),
        "keywords": data.get("keywords", ""),
        "datePublished": data.get("date_published", ""),
        "dateModified": data.get("date_modified", data.get("date_published", "")),
        "inLanguage": data.get("language", "en"),
    }

    founder_name = data.get("founder_name", "") or data.get("person_name", "")
    if founder_name or person_id:
        schema["author"] = {
            "@type": "Person",
            "@id": person_id,
            "name": founder_name,
        }

    if data.get("reviewed_by_name"):
        schema["reviewedBy"] = {
            "@type": "Person",
            "name": data["reviewed_by_name"],
            "jobTitle": data.get("reviewed_by_title", ""),
        }
    elif founder_name:
        schema["reviewedBy"] = {"@type": "Person", "@id": person_id, "name": founder_name}

    if data.get("post_image"):
        schema["image"] = {
            "@type": "ImageObject",
            "representativeOfPage": True,
            "contentUrl": data["post_image"],
            "url": data["post_image"],
            "copyrightHolder": {"@id": org_id},
            "creator": {"@id": person_id} if founder_name else {"@id": org_id},
        }

    schema["publisher"] = {"@id": org_id}

    schema["isPartOf"] = {
        "@type": "WebSite",
        "@id": website_id,
        "url": base_url,
        "name": data.get("business_name", ""),
        "publisher": {"@id": org_id},
    }

    mentions_items = data.get("mentions", [])
    if mentions_items:
        schema["mentions"] = [
            clean_dict({
                "@type": m.get("type", "Thing"),
                "name": m.get("name", ""),
                "@id": m.get("wikidata_id", ""),
                "sameAs": m.get("wikipedia_url", ""),
            })
            for m in mentions_items
            if m.get("name")
        ]

    if data.get("word_count"):
        schema["wordCount"] = data["word_count"]

    if data.get("article_section"):
        schema["articleSection"] = data["article_section"]

    schema["mainEntityOfPage"] = {
        "@type": "WebPage",
        "@id": build_id(post_url or base_url, "webpage"),
    }

    return clean_dict(schema)
