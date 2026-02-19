import json
import streamlit as st
from openai import OpenAI


def get_client() -> OpenAI:
    api_key = st.secrets.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set in Streamlit secrets.")
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )


def get_model() -> str:
    return st.secrets.get("MODEL", "anthropic/claude-sonnet-4-5")


ENRICHMENT_PROMPT = """You are a semantic SEO and schema markup expert. Given a business name, website URL, and business type, return a JSON object with enrichment data for building advanced schema.org markup.

Business Name: {business_name}
Website URL: {website_url}
Business Type: {business_type}

Return ONLY valid JSON (no markdown, no explanation) with this exact structure:
{{
  "schema_subtype": "The most specific schema.org LocalBusiness subtype (e.g. HVACBusiness, LegalService, Dentist, AutoRepair, etc.) or 'Organization' for SaaS/ecom",
  "wikidata_business_id": "Wikidata entity URL for the business category (e.g. https://www.wikidata.org/wiki/Q1798773 for HVAC). Use empty string if unsure.",
  "wikipedia_business_url": "Wikipedia article URL for the business type (e.g. https://en.wikipedia.org/wiki/Heating,_ventilation,_and_air_conditioning). Use empty string if unsure.",
  "description": "A 2-3 sentence factual description of what this business does, written in third person, suitable for schema description property.",
  "disambiguating_description": "A longer 3-5 sentence description that further disambiguates this business from similar ones. Include key services and differentiators.",
  "knows_about": [
    {{
      "name": "topic name",
      "wikidata_id": "https://www.wikidata.org/wiki/QXXXXXX",
      "wikipedia_url": "https://en.wikipedia.org/wiki/Topic_Name"
    }}
  ],
  "additional_types": [
    "https://en.wikipedia.org/wiki/RelevantType1",
    "https://www.wikidata.org/wiki/QXXXXXX"
  ],
  "slogan": "A short, factual tagline for the business (not marketing fluff)",
  "suggested_same_as": [
    "https://www.google.com/maps/place/...",
    "https://www.linkedin.com/company/...",
    "https://www.facebook.com/...",
    "https://twitter.com/...",
    "https://www.instagram.com/...",
    "https://www.wikidata.org/wiki/..."
  ],
  "area_served_suggestion": "City, State or Country the business likely serves based on the URL/name",
  "price_range": "$ or $$ or $$$ or $$$$"
}}

For knows_about: include 5-8 highly relevant topics directly related to this business's core expertise. Each must have real Wikidata and Wikipedia URLs.
For additional_types: include 2-4 Wikipedia/Wikidata URLs that best describe the business category.
For suggested_same_as: include placeholder URLs with realistic patterns — the user will fill in real values. Mark placeholders with a comment-style prefix like "FILL-IN:" in the URL string.
"""


def enrich_business(business_name: str, website_url: str, business_type: str) -> dict:
    """Call Claude via OpenRouter to enrich business data for schema generation."""
    client = get_client()
    model = get_model()

    prompt = ENRICHMENT_PROMPT.format(
        business_name=business_name,
        website_url=website_url,
        business_type=business_type,
    )

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=2000,
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    return json.loads(raw)


WIKIDATA_PROMPT = """You are a semantic SEO expert. Given a list of topics related to a business, return Wikidata entity IDs for each topic.

Topics: {topics}
Business context: {business_name} — {business_type}

Return ONLY valid JSON array (no markdown) with this structure:
[
  {{
    "name": "exact topic name from input",
    "wikidata_id": "https://www.wikidata.org/wiki/QXXXXXX",
    "wikipedia_url": "https://en.wikipedia.org/wiki/Topic"
  }}
]

Only include topics where you are confident about the Wikidata ID. Skip uncertain ones.
"""


FACT_CHEAT_EXTRACTION_PROMPT = """You are a semantic SEO expert extracting structured business data from a "Fact Cheat" document.

A Fact Cheat is a pre-verified document containing accurate facts about a business. Extract all relevant information and return it as JSON.

Fact Cheat Content:
---
{fact_cheat_content}
---

Return ONLY valid JSON (no markdown, no explanation) with this structure (omit any field where the information is not found):
{{
  "business_name": "exact business name",
  "legal_name": "legal entity name if different",
  "founder_name": "founder or CEO name",
  "job_title": "founder's job title",
  "telephone": "primary phone number",
  "email": "email address if found",
  "website_url": "website URL if found",
  "description": "2-3 sentence description based on verified facts",
  "disambiguating_description": "longer description with key differentiators",
  "slogan": "tagline if found",
  "street_address": "street address",
  "city": "primary city",
  "state": "state or region",
  "postal_code": "postal code",
  "country": "country",
  "founding_date": "founding year or date",
  "founding_location": "city, state where founded",
  "price_range": "$ or $$ or $$$ or $$$$ based on pricing signals",
  "has_map": "Google Maps URL if found",
  "aggregate_rating_value": "average rating number (e.g. 4.8)",
  "aggregate_rating_count": "number of reviews as string",
  "payment_accepted": "payment methods accepted",
  "cities": ["list", "of", "cities", "served"],
  "area_served_name": "general service area description",
  "opening_hours": [
    {{"day": "Monday", "opens": "09:00", "closes": "17:00"}}
  ],
  "services": [
    {{"name": "service name", "url": "", "service_type": "service type", "audience": ""}}
  ],
  "has_24_7": true,
  "is_licensed": true,
  "is_insured": true,
  "is_bonded": true,
  "has_emergency_service": true,
  "credentials_notes": "any credential/certification details",
  "guarantees_notes": "any guarantee or warranty details",
  "financing_notes": "any financing information"
}}

Extract only information explicitly stated in the document. Do not infer or fabricate. For opening_hours, if the document says "24/7" set all days to opens: "00:00", closes: "23:59". For services, extract each distinct service mentioned.
"""


def extract_from_fact_cheat(fact_cheat_content: str) -> dict:
    """Extract structured business data from a Fact Cheat document."""
    client = get_client()
    model = get_model()

    prompt = FACT_CHEAT_EXTRACTION_PROMPT.format(fact_cheat_content=fact_cheat_content)

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=3000,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    return json.loads(raw)


def suggest_wikidata_for_topics(topics: list[str], business_name: str, business_type: str) -> list[dict]:
    """Suggest Wikidata IDs for a list of topic strings."""
    if not topics:
        return []

    client = get_client()
    model = get_model()

    prompt = WIKIDATA_PROMPT.format(
        topics=", ".join(topics),
        business_name=business_name,
        business_type=business_type,
    )

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=1000,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    return json.loads(raw)
