"""
Schema validator — checks required fields and advanced best practices.
Returns errors (blocking) and warnings (advisory).
"""
from dataclasses import dataclass


@dataclass
class ValidationIssue:
    level: str  # "error" or "warning"
    field: str
    message: str


def validate_business_data(data: dict) -> list[ValidationIssue]:
    """Validate the core business data before schema generation."""
    issues = []

    # --- Errors (required for valid schema) ---
    if not data.get("business_name", "").strip():
        issues.append(ValidationIssue("error", "business_name", "Business name is required."))

    if not data.get("website_url", "").strip():
        issues.append(ValidationIssue("error", "website_url", "Website URL is required."))

    # --- Warnings (important for knowledge graph quality) ---
    if not data.get("description", "").strip():
        issues.append(ValidationIssue("warning", "description", "Business description is missing. This is important for Google Knowledge Panel."))

    if not data.get("same_as"):
        issues.append(ValidationIssue("warning", "same_as", "No sameAs profiles provided. Add Google Business Profile, social media, and Wikidata URLs to establish entity authority."))
    else:
        same_as = data.get("same_as", [])
        has_gbp = any("google.com/maps" in u or "g.page" in u or "business.site" in u for u in same_as if u)
        if not has_gbp:
            issues.append(ValidationIssue("warning", "same_as", "Google Business Profile URL not found in sameAs. This is a strong trust signal for local businesses."))

    if not data.get("knows_about"):
        issues.append(ValidationIssue("warning", "knows_about", "No knowsAbout topics provided. Add Wikidata-linked topics to strengthen the knowledge graph."))
    else:
        has_wikidata = any(item.get("wikidata_id") for item in data.get("knows_about", []))
        if not has_wikidata:
            issues.append(ValidationIssue("warning", "knows_about", "knowsAbout topics have no Wikidata @id links. Add Wikidata URLs to anchor entities in the knowledge graph."))

    if not data.get("logo_url", "").strip():
        issues.append(ValidationIssue("warning", "logo_url", "Logo URL is missing. Google requires a logo for Organization schema."))

    if not data.get("image_url", "").strip():
        issues.append(ValidationIssue("warning", "image_url", "Image URL is missing. Google requires at least one image for LocalBusiness schema."))

    return issues


def validate_local_business(data: dict) -> list[ValidationIssue]:
    """Validate LocalBusiness-specific required fields."""
    issues = validate_business_data(data)

    if not data.get("telephone", "").strip():
        issues.append(ValidationIssue("error", "telephone", "Telephone is required for LocalBusiness schema (Google requirement)."))

    if not data.get("street_address", "").strip() and not data.get("city", "").strip():
        issues.append(ValidationIssue("error", "address", "Address (at minimum city) is required for LocalBusiness schema."))

    if not data.get("country", "").strip():
        issues.append(ValidationIssue("warning", "country", "Country is missing from address. Required by Google for LocalBusiness."))

    if not data.get("opening_hours"):
        issues.append(ValidationIssue("warning", "opening_hours", "Opening hours not provided. Recommended for LocalBusiness rich results."))

    if not data.get("has_map", "").strip():
        issues.append(ValidationIssue("warning", "has_map", "Google Maps URL (hasMap) not provided. Strongly recommended for LocalBusiness entity anchoring."))

    if not data.get("cities") and not data.get("postal_codes"):
        issues.append(ValidationIssue("warning", "area_served", "No areaServed cities or postal codes provided. Important for local SEO knowledge graph."))

    if not data.get("price_range", "").strip():
        issues.append(ValidationIssue("warning", "price_range", "priceRange not set. Recommended for LocalBusiness (e.g., $, $$, $$$)."))

    return issues


def validate_organization(data: dict) -> list[ValidationIssue]:
    """Validate Organization-specific fields."""
    issues = validate_business_data(data)

    if not data.get("email", "").strip() and not data.get("telephone", "").strip():
        issues.append(ValidationIssue("warning", "contact", "No email or telephone provided. At least one contact method is recommended."))

    if not data.get("founding_date", "").strip():
        issues.append(ValidationIssue("warning", "founding_date", "foundingDate not provided. Helps Google establish entity longevity."))

    return issues


def validate_person(data: dict) -> list[ValidationIssue]:
    """Validate Person / founder data."""
    issues = []

    if not data.get("founder_name", "").strip() and not data.get("person_name", "").strip():
        issues.append(ValidationIssue("warning", "founder_name", "No person/founder name provided. Person schema won't be generated."))
        return issues

    if not data.get("person_same_as"):
        issues.append(ValidationIssue("warning", "person_same_as", "No person sameAs profiles (LinkedIn, etc.). Required for E-E-A-T author disambiguation."))

    if not data.get("person_knows_about") and not data.get("knows_about"):
        issues.append(ValidationIssue("warning", "person_knows_about", "Person has no knowsAbout topics. Add expertise areas with Wikidata links for E-E-A-T signals."))

    if not data.get("job_title", "").strip():
        issues.append(ValidationIssue("warning", "job_title", "jobTitle not provided. Important for E-E-A-T expertise signals."))

    return issues


def validate_service(data: dict) -> list[ValidationIssue]:
    """Validate service page data."""
    issues = []

    if not data.get("service_name", "").strip():
        issues.append(ValidationIssue("error", "service_name", "Service name is required."))

    if not data.get("service_page_url", "").strip():
        issues.append(ValidationIssue("warning", "service_page_url", "Service page URL not provided. @id will fall back to base URL."))

    if not data.get("service_description", "").strip():
        issues.append(ValidationIssue("warning", "service_description", "Service description is missing. Recommended for rich results."))

    return issues


def validate_blog_post(data: dict) -> list[ValidationIssue]:
    """Validate blog post data."""
    issues = []

    if not data.get("post_title", "").strip():
        issues.append(ValidationIssue("error", "post_title", "Post title (headline) is required for BlogPosting schema."))

    if not data.get("post_url", "").strip():
        issues.append(ValidationIssue("error", "post_url", "Post URL is required."))

    if not data.get("date_published", "").strip():
        issues.append(ValidationIssue("error", "date_published", "datePublished is required for Article/BlogPosting schema (Google requirement)."))

    if not data.get("post_image", "").strip():
        issues.append(ValidationIssue("error", "post_image", "Image is required for Article rich results (Google requirement)."))

    if not data.get("founder_name", "").strip() and not data.get("person_name", "").strip():
        issues.append(ValidationIssue("warning", "author", "No author provided. Adding author Person schema is important for E-E-A-T."))

    if not data.get("mentions"):
        issues.append(ValidationIssue("warning", "mentions", "No mentions entities provided. Add Wikidata-linked entities to strengthen the knowledge graph for this article."))

    return issues


def validate_faq(data: dict) -> list[ValidationIssue]:
    """Validate FAQ data."""
    issues = []

    questions = data.get("questions", [])
    if not questions:
        issues.append(ValidationIssue("error", "questions", "At least one question/answer pair is required for FAQPage schema."))
        return issues

    for idx, q in enumerate(questions):
        if not q.get("question", "").strip():
            issues.append(ValidationIssue("error", f"questions[{idx}].question", f"Question {idx + 1} is missing the question text."))
        if not q.get("answer", "").strip():
            issues.append(ValidationIssue("error", f"questions[{idx}].answer", f"Question {idx + 1} is missing the answer text."))

    return issues


def validate_product(data: dict) -> list[ValidationIssue]:
    """Validate product data for Google rich results."""
    issues = []

    if not data.get("product_name", "").strip():
        issues.append(ValidationIssue("error", "product_name", "Product name is required."))

    if not data.get("product_image", "").strip() and not data.get("product_images"):
        issues.append(ValidationIssue("error", "product_image", "At least one product image is required for Product rich results (Google requirement)."))

    if not data.get("price", "").strip():
        issues.append(ValidationIssue("error", "price", "Price is required for Product rich results."))

    if not data.get("currency", "").strip():
        issues.append(ValidationIssue("error", "currency", "Price currency is required (e.g., USD, GBP, AUD)."))

    if not data.get("product_description", "").strip():
        issues.append(ValidationIssue("warning", "product_description", "Product description is missing. Strongly recommended."))

    if not data.get("sku", "").strip() and not data.get("gtin13", "").strip():
        issues.append(ValidationIssue("warning", "sku", "Neither SKU nor GTIN provided. At least one product identifier is recommended."))

    if not data.get("aggregate_rating_value"):
        issues.append(ValidationIssue("warning", "aggregate_rating", "AggregateRating not provided. Ratings can improve CTR in search results."))

    return issues


def validate_saas(data: dict) -> list[ValidationIssue]:
    """Validate SaaS / WebApplication data."""
    issues = []

    if not data.get("app_name", "").strip() and not data.get("business_name", "").strip():
        issues.append(ValidationIssue("error", "app_name", "App/product name is required."))

    if not data.get("app_url", "").strip() and not data.get("website_url", "").strip():
        issues.append(ValidationIssue("error", "app_url", "App URL is required for WebApplication schema."))

    if not data.get("pricing_tiers"):
        issues.append(ValidationIssue("warning", "pricing_tiers", "No pricing tiers provided. AggregateOffer won't be generated."))

    if not data.get("app_category", "").strip():
        issues.append(ValidationIssue("warning", "app_category", "applicationCategory not set. Recommended for WebApplication schema."))

    return issues


def format_issues_for_display(issues: list[ValidationIssue]) -> tuple[list[str], list[str]]:
    """Split issues into error messages and warning messages."""
    errors = [f"**{i.field}**: {i.message}" for i in issues if i.level == "error"]
    warnings = [f"**{i.field}**: {i.message}" for i in issues if i.level == "warning"]
    return errors, warnings
