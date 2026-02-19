"""
WebSite and WebPage schema generators (all page types).
"""
from src.generators.base import make_context, make_knows_about, make_same_as, make_area_served
from src.generators.person import generate_person
from src.utils.helpers import build_id, normalize_url, clean_dict


def generate_website(data: dict) -> dict:
    """
    Generate WebSite schema with SearchAction (SiteLinks Searchbox).
    """
    base_url = normalize_url(data.get("website_url", ""))
    website_id = build_id(base_url, "website")
    org_id = build_id(base_url, "organization")

    schema = {
        "@context": make_context(),
        "@type": "WebSite",
        "@id": website_id,
        "url": base_url,
        "name": data.get("business_name", ""),
        "description": data.get("description", ""),
        "inLanguage": data.get("language", "en"),
        "publisher": {"@id": org_id},
    }

    if data.get("enable_search_action"):
        schema["potentialAction"] = {
            "@type": "SearchAction",
            "target": {
                "@type": "EntryPoint",
                "urlTemplate": f"{base_url}/?s={{search_term_string}}",
            },
            "query-input": "required name=search_term_string",
        }

    return clean_dict(schema)


def generate_webpage(data: dict, page_url: str = "", page_type: str = "WebPage") -> dict:
    """
    Generic WebPage schema. page_type can be:
    WebPage, AboutPage, ContactPage, CollectionPage, CheckoutPage, etc.
    """
    base_url = normalize_url(data.get("website_url", ""))
    page = normalize_url(page_url or base_url)
    webpage_id = build_id(page, "webpage")
    website_id = build_id(base_url, "website")
    org_id = build_id(base_url, "organization")

    schema = {
        "@context": make_context(),
        "@type": page_type,
        "@id": webpage_id,
        "url": page,
        "name": data.get("page_title", data.get("business_name", "")),
        "description": data.get("page_description", data.get("description", "")),
        "inLanguage": data.get("language", "en"),
        "isPartOf": {"@id": website_id},
        "about": {"@id": org_id},
        "publisher": {"@id": org_id},
    }

    related_links = data.get("related_links", [])
    if related_links:
        schema["relatedLink"] = related_links

    significant_links = data.get("significant_links", [])
    if significant_links:
        schema["significantLink"] = significant_links

    return clean_dict(schema)


def generate_homepage(data: dict) -> dict:
    """
    Homepage schema: WebPage → isPartOf WebSite → publisher Organization → founder Person.
    """
    base_url = normalize_url(data.get("website_url", ""))
    webpage_id = build_id(base_url, "webpage")
    website_id = build_id(base_url, "website")
    org_id = build_id(base_url, "organization")
    person_id = build_id(base_url, "person")

    schema_type = data.get("schema_subtype", "LocalBusiness")
    if not schema_type or schema_type == "Organization":
        schema_type = "Organization"

    org = {
        "@type": [schema_type, "Organization"] if schema_type != "Organization" else "Organization",
        "@id": org_id,
        "name": data.get("business_name", ""),
        "legalName": data.get("legal_name", "") or data.get("business_name", ""),
        "url": base_url,
        "description": data.get("description", ""),
        "disambiguatingDescription": data.get("disambiguating_description", ""),
        "slogan": data.get("slogan", ""),
        "email": data.get("email", ""),
        "telephone": data.get("telephone", ""),
        "priceRange": data.get("price_range", ""),
    }

    if data.get("additional_types"):
        existing = org.get("@type", [])
        if isinstance(existing, str):
            existing = [existing]
        for t in data["additional_types"]:
            if t not in existing:
                existing.append(t)
        org["@type"] = existing

    if data.get("logo_url"):
        org["logo"] = {"@type": "ImageObject", "contentUrl": data["logo_url"]}

    if data.get("image_url"):
        org["image"] = data["image_url"]

    if data.get("has_map"):
        org["hasMap"] = data["has_map"]

    if data.get("street_address") or data.get("city"):
        org["address"] = {
            "@type": "PostalAddress",
            "streetAddress": data.get("street_address", ""),
            "addressLocality": data.get("city", ""),
            "addressRegion": data.get("state", ""),
            "postalCode": data.get("postal_code", ""),
            "addressCountry": data.get("country", ""),
        }

    same_as = make_same_as(data.get("same_as", []))
    if same_as:
        org["sameAs"] = same_as

    knows_about_items = data.get("knows_about", [])
    if knows_about_items:
        org["knowsAbout"] = make_knows_about(knows_about_items)

    area = make_area_served(data)
    if area:
        org["areaServed"] = area

    services = data.get("services", [])
    if services:
        org["makesOffer"] = {
            "@type": "Offer",
            "@id": build_id(base_url, "offer"),
            "businessFunction": "http://purl.org/goodrelations/v1#ProvideService",
            "itemOffered": [
                {
                    "@type": "Service",
                    "name": svc.get("name", ""),
                    "url": svc.get("url", ""),
                    "serviceType": svc.get("service_type", svc.get("name", "")),
                }
                for svc in services
                if svc.get("name")
            ],
        }

    founder_name = data.get("founder_name", "")
    if founder_name:
        founder = {
            "@type": "Person",
            "@id": person_id,
            "name": founder_name,
        }
        person_same_as = make_same_as(data.get("person_same_as", []))
        if person_same_as:
            founder["sameAs"] = person_same_as
        person_knows = data.get("person_knows_about", [])
        if person_knows:
            founder["knowsAbout"] = make_knows_about(person_knows)
        if data.get("job_title"):
            founder["jobTitle"] = data["job_title"]
        org["founder"] = founder

    website = {
        "@type": "WebSite",
        "@id": website_id,
        "url": base_url,
        "name": data.get("business_name", ""),
        "publisher": clean_dict(org),
        "about": {"@id": org_id},
    }

    schema = {
        "@context": make_context(),
        "@type": "WebPage",
        "@id": webpage_id,
        "url": base_url,
        "name": data.get("page_title", data.get("business_name", "")),
        "description": data.get("page_description", data.get("description", "")),
        "inLanguage": data.get("language", "en"),
        "mainEntity": {"@id": org_id},
        "isPartOf": clean_dict(website),
    }

    related_links = data.get("related_links", [])
    if related_links:
        schema["relatedLink"] = related_links

    return clean_dict(schema)


def generate_about_page(data: dict) -> dict:
    """
    AboutPage with Person as mainEntity — full E-E-A-T signals.
    """
    base_url = normalize_url(data.get("website_url", ""))
    about_url = normalize_url(data.get("about_page_url", f"{base_url}/about"))
    webpage_id = build_id(about_url, "webpage")
    website_id = build_id(base_url, "website")
    org_id = build_id(base_url, "organization")
    person_id = build_id(base_url, "person")

    person_schema = {
        "@type": "Person",
        "@id": person_id,
        "name": data.get("founder_name", "") or data.get("person_name", ""),
        "url": about_url,
        "description": data.get("person_description", ""),
        "jobTitle": data.get("job_title", ""),
        "email": data.get("person_email", data.get("email", "")),
        "telephone": data.get("person_telephone", data.get("telephone", "")),
    }

    if data.get("person_image"):
        person_schema["image"] = data["person_image"]

    if base_url:
        person_schema["worksFor"] = {"@id": org_id}

    knows_about_items = data.get("person_knows_about", []) or data.get("knows_about", [])
    if knows_about_items:
        person_schema["knowsAbout"] = make_knows_about(knows_about_items)

    person_same_as = make_same_as(data.get("person_same_as", []))
    if person_same_as:
        person_schema["sameAs"] = person_same_as

    if data.get("alumni_of"):
        person_schema["alumniOf"] = {
            "@type": "EducationalOrganization",
            "name": data["alumni_of"],
        }
        if data.get("alumni_of_url"):
            person_schema["alumniOf"]["@id"] = data["alumni_of_url"]

    if data.get("has_credential"):
        person_schema["hasCredential"] = data["has_credential"]

    if data.get("knows_language"):
        person_schema["knowsLanguage"] = data["knows_language"]

    schema = {
        "@context": make_context(),
        "@type": "AboutPage",
        "@id": webpage_id,
        "url": about_url,
        "name": data.get("about_page_title", f"About {data.get('business_name', '')}"),
        "description": data.get("about_page_description", data.get("person_description", "")),
        "inLanguage": data.get("language", "en"),
        "mainEntity": clean_dict(person_schema),
        "isPartOf": {
            "@type": "WebSite",
            "@id": website_id,
            "url": base_url,
            "publisher": {"@id": org_id},
        },
        "about": {"@id": org_id},
    }

    related_links = data.get("related_links", [])
    if related_links:
        schema["relatedLink"] = related_links

    return clean_dict(schema)


def generate_contact_page(data: dict) -> dict:
    """
    ContactPage schema with Organization contact details.
    """
    base_url = normalize_url(data.get("website_url", ""))
    contact_url = normalize_url(data.get("contact_page_url", f"{base_url}/contact"))
    webpage_id = build_id(contact_url, "webpage")
    website_id = build_id(base_url, "website")
    org_id = build_id(base_url, "organization")

    schema = {
        "@context": make_context(),
        "@type": "ContactPage",
        "@id": webpage_id,
        "url": contact_url,
        "name": data.get("contact_page_title", f"Contact {data.get('business_name', '')}"),
        "description": data.get("contact_page_description", ""),
        "inLanguage": data.get("language", "en"),
        "about": {"@id": org_id},
        "mainEntity": {
            "@id": org_id,
            "@type": data.get("schema_subtype", "Organization"),
            "name": data.get("business_name", ""),
            "telephone": data.get("telephone", ""),
            "email": data.get("email", ""),
            "address": {
                "@type": "PostalAddress",
                "streetAddress": data.get("street_address", ""),
                "addressLocality": data.get("city", ""),
                "addressRegion": data.get("state", ""),
                "postalCode": data.get("postal_code", ""),
                "addressCountry": data.get("country", ""),
            },
        },
        "isPartOf": {
            "@type": "WebSite",
            "@id": website_id,
            "url": base_url,
            "publisher": {"@id": org_id},
        },
    }

    return clean_dict(schema)
