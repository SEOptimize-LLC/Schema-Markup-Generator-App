"""
Person schema generator — used for founders, authors, and E-E-A-T signals.
"""
from src.generators.base import make_context, make_postal_address, make_knows_about, make_same_as
from src.utils.helpers import build_id, normalize_url, clean_dict


def generate_person(data: dict, base_url: str = "") -> dict:
    """
    Generate a full Person schema with E-E-A-T signals.
    Can be standalone or embedded within Organization/AboutPage.
    """
    base = normalize_url(base_url or data.get("website_url", ""))
    person_id = build_id(base, "person")
    org_id = build_id(base, "organization")

    schema = {
        "@context": make_context(),
        "@type": "Person",
        "@id": person_id,
        "name": data.get("founder_name", "") or data.get("person_name", ""),
        "alternateName": data.get("person_alternate_name", ""),
        "description": data.get("person_description", ""),
        "url": data.get("person_url", base),
        "email": data.get("person_email", ""),
        "telephone": data.get("person_telephone", ""),
        "jobTitle": data.get("job_title", ""),
        "gender": data.get("gender", ""),
        "nationality": data.get("nationality", ""),
        "birthDate": data.get("birth_date", ""),
        "birthPlace": data.get("birth_place", ""),
        "memberOf": data.get("member_of", ""),
    }

    if data.get("person_image"):
        schema["image"] = data["person_image"]

    if data.get("job_title"):
        schema["jobTitle"] = {
            "@type": "DefinedTerm",
            "name": data["job_title"],
        }
        if data.get("job_title_same_as"):
            schema["jobTitle"]["sameAs"] = data["job_title_same_as"]

    if base:
        schema["worksFor"] = {"@id": org_id}
        schema["owns"] = {"@id": org_id}

    knows_about_items = data.get("person_knows_about", [])
    if knows_about_items:
        schema["knowsAbout"] = make_knows_about(knows_about_items)

    if data.get("knows_language"):
        schema["knowsLanguage"] = data["knows_language"]

    alumni_of = data.get("alumni_of", "")
    if alumni_of:
        schema["alumniOf"] = {
            "@type": "EducationalOrganization",
            "name": alumni_of,
        }
        if data.get("alumni_of_url"):
            schema["alumniOf"]["@id"] = data["alumni_of_url"]

    credentials = data.get("has_credential", "")
    if credentials:
        schema["hasCredential"] = credentials

    awards = data.get("award", "")
    if awards:
        schema["award"] = awards

    same_as = make_same_as(data.get("person_same_as", []))
    if same_as:
        schema["sameAs"] = same_as

    address = make_postal_address(data)
    if address:
        schema["address"] = address

    return clean_dict(schema)


def generate_author_reference(data: dict, base_url: str) -> dict:
    """
    Compact Person reference used as author/reviewedBy in Article/BlogPosting.
    Returns @id reference if person schema exists on the about page,
    otherwise returns inline Person object.
    """
    base = normalize_url(base_url)
    person_id = build_id(base, "person")
    person_name = data.get("founder_name", "") or data.get("person_name", "")

    if not person_name:
        return {}

    return {
        "@type": "Person",
        "@id": person_id,
        "name": person_name,
    }
