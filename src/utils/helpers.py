import json
import io
import zipfile
import re


def slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def normalize_url(url: str) -> str:
    """Ensure URL has https scheme and no trailing slash."""
    if not url:
        return ""
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    return url.rstrip("/")


def build_id(base_url: str, fragment: str) -> str:
    """Build a consistent @id URI with fragment identifier."""
    base = normalize_url(base_url)
    return f"{base}/#{fragment}"


def org_ref(base_url: str) -> dict:
    return {"@id": build_id(base_url, "organization")}


def website_ref(base_url: str) -> dict:
    return {"@id": build_id(base_url, "website")}


def person_ref(base_url: str) -> dict:
    return {"@id": build_id(base_url, "person")}


def page_ref(page_url: str, fragment: str = "webpage") -> dict:
    url = normalize_url(page_url)
    return {"@id": f"{url}/#{fragment}"}


def format_json(data: dict) -> str:
    """Serialize schema dict to pretty-printed JSON string."""
    return json.dumps(data, indent=2, ensure_ascii=False)


def wrap_in_script_tag(json_str: str) -> str:
    """Wrap JSON-LD in HTML script tag."""
    return f'<script type="application/ld+json">\n{json_str}\n</script>'


def clean_dict(d: dict) -> dict:
    """Recursively remove None, empty string, and empty list/dict values."""
    if not isinstance(d, dict):
        return d
    result = {}
    for k, v in d.items():
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        if isinstance(v, list):
            cleaned_list = [clean_dict(item) if isinstance(item, dict) else item for item in v]
            cleaned_list = [item for item in cleaned_list if item not in (None, "", {}, [])]
            if cleaned_list:
                result[k] = cleaned_list
        elif isinstance(v, dict):
            cleaned = clean_dict(v)
            if cleaned:
                result[k] = cleaned
        else:
            result[k] = v
    return result


def build_zip(schemas: dict[str, dict], client_slug: str) -> bytes:
    """
    Build a zip file of JSON-LD schemas.
    schemas: dict of {filename_key: schema_dict}
    Returns bytes of the zip file.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for key, schema in schemas.items():
            filename = f"{client_slug}-{key}.json"
            content = format_json(schema)
            zf.writestr(filename, content)
    return buf.getvalue()


def parse_urls_input(text: str) -> list[str]:
    """Parse newline or comma separated URLs into a list."""
    if not text:
        return []
    separators = re.split(r"[\n,]+", text)
    return [url.strip() for url in separators if url.strip()]


def parse_cities_input(text: str) -> list[str]:
    """Parse newline or comma separated city names into a list."""
    if not text:
        return []
    separators = re.split(r"[\n,]+", text)
    return [city.strip() for city in separators if city.strip()]


def parse_postal_codes(text: str) -> list[str]:
    """Parse newline or comma or space separated postal codes."""
    if not text:
        return []
    separators = re.split(r"[\n,\s]+", text)
    return [code.strip() for code in separators if code.strip()]
