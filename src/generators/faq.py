"""
FAQPage schema generator — with isPartOf nesting and mentions.
Supports HTML in answers (uses single quotes for href per the guide).
"""
from src.generators.base import make_context
from src.utils.helpers import build_id, normalize_url, clean_dict


def _build_answer_text(text: str, links: list[dict] | None = None) -> str:
    """
    Build answer text. If links provided, inserts HTML <a> tags.
    Uses single quotes for href (required for JSON-LD embedding).
    """
    if not links:
        return text
    for link in links:
        anchor = link.get("anchor_text", "")
        url = link.get("url", "")
        if anchor and url:
            text = text.replace(anchor, f"<a href='{url}'>{anchor}</a>")
    return text


def generate_faq(data: dict) -> dict:
    """
    FAQPage with isPartOf WebPage, author, reviewedBy, and mentions on answers.
    """
    base_url = normalize_url(data.get("website_url", ""))
    faq_page_url = normalize_url(data.get("faq_page_url", f"{base_url}/faq"))
    org_id = build_id(base_url, "organization")
    person_id = build_id(base_url, "person")
    website_id = build_id(base_url, "website")
    webpage_id = build_id(faq_page_url, "webpage")
    faq_id = build_id(faq_page_url, "faqpage")

    questions = data.get("questions", [])
    main_entity = []
    for q in questions:
        question_text = q.get("question", "")
        answer_text = q.get("answer", "")
        answer_links = q.get("answer_links", [])
        mentions_items = q.get("mentions", [])

        if not question_text or not answer_text:
            continue

        answer_obj = {
            "@type": "Answer",
            "text": _build_answer_text(answer_text, answer_links),
        }

        if mentions_items:
            answer_obj["mentions"] = [
                clean_dict({
                    "@type": m.get("type", "Thing"),
                    "name": m.get("name", ""),
                    "@id": m.get("wikidata_id", ""),
                    "sameAs": m.get("wikipedia_url", ""),
                })
                for m in mentions_items
                if m.get("name")
            ]

        main_entity.append({
            "@type": "Question",
            "name": question_text,
            "acceptedAnswer": answer_obj,
        })

    founder_name = data.get("founder_name", "") or data.get("person_name", "")

    faq_schema = clean_dict({
        "@context": make_context(),
        "@type": "FAQPage",
        "@id": faq_id,
        "url": faq_page_url,
        "name": data.get("faq_page_title", f"FAQ — {data.get('business_name', '')}"),
        "description": data.get("faq_page_description", ""),
        "inLanguage": data.get("language", "en"),
        "author": {"@id": org_id},
        "reviewedBy": (
            {"@type": "Person", "@id": person_id, "name": founder_name}
            if founder_name else {"@id": org_id}
        ),
        "mainEntity": main_entity,
        "isPartOf": {
            "@type": "WebPage",
            "@id": webpage_id,
            "url": faq_page_url,
            "isPartOf": {
                "@type": "WebSite",
                "@id": website_id,
                "url": base_url,
                "publisher": {"@id": org_id},
            },
        },
    })

    return faq_schema


def generate_faq_nested_in_page(data: dict, page_url: str) -> dict:
    """
    FAQPage nested into an existing page (e.g. service page or article).
    Uses @graph to connect both schemas.
    """
    base_url = normalize_url(data.get("website_url", ""))
    page = normalize_url(page_url)
    webpage_id = build_id(page, "webpage")
    website_id = build_id(base_url, "website")
    org_id = build_id(base_url, "organization")
    faq_id = build_id(page, "faqpage")
    person_id = build_id(base_url, "person")
    founder_name = data.get("founder_name", "") or data.get("person_name", "")

    questions = data.get("questions", [])
    main_entity = []
    for q in questions:
        question_text = q.get("question", "")
        answer_text = q.get("answer", "")
        answer_links = q.get("answer_links", [])
        if not question_text or not answer_text:
            continue
        main_entity.append({
            "@type": "Question",
            "name": question_text,
            "acceptedAnswer": {
                "@type": "Answer",
                "text": _build_answer_text(answer_text, answer_links),
            },
        })

    webpage_node = clean_dict({
        "@type": "WebPage",
        "@id": webpage_id,
        "url": page,
        "name": data.get("page_title", ""),
        "description": data.get("page_description", ""),
        "inLanguage": data.get("language", "en"),
        "isPartOf": {
            "@type": "WebSite",
            "@id": website_id,
            "url": base_url,
            "publisher": {"@id": org_id},
        },
    })

    faq_node = clean_dict({
        "@type": "FAQPage",
        "@id": faq_id,
        "author": {"@id": org_id},
        "reviewedBy": (
            {"@type": "Person", "@id": person_id, "name": founder_name}
            if founder_name else {"@id": org_id}
        ),
        "mainEntity": main_entity,
        "isPartOf": {"@id": webpage_id},
    })

    return {"@context": make_context(), "@graph": [webpage_node, faq_node]}
