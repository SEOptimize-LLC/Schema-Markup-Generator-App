import streamlit as st

from src.ai.enrichment import enrich_business, extract_from_fact_cheat
from src.ai.scraper import scrape_business_page
from src.generators.website import generate_homepage, generate_about_page, generate_contact_page, generate_website
from src.generators.organization import generate_organization, generate_local_business
from src.generators.person import generate_person
from src.generators.service import generate_service_page, generate_multi_service_page
from src.generators.blog import generate_blog_post
from src.generators.faq import generate_faq
from src.generators.product import generate_product
from src.generators.saas import generate_saas_app, generate_saas_pricing_page
from src.generators.breadcrumb import generate_breadcrumb
from src.validators.schema_validator import (
    validate_local_business, validate_organization, validate_person,
    validate_service, validate_blog_post, validate_faq,
    validate_product, validate_saas, format_issues_for_display,
)
from src.utils.helpers import format_json, slugify, build_zip, parse_urls_input, parse_cities_input, parse_postal_codes, normalize_url

# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Schema Markup Generator",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.schema-box { background: #1e1e1e; color: #d4d4d4; padding: 1rem; border-radius: 8px; font-family: monospace; font-size: 0.8rem; overflow-x: auto; white-space: pre; }
.error-box { background: #fef2f2; border-left: 4px solid #ef4444; padding: 0.75rem 1rem; border-radius: 4px; margin: 0.5rem 0; }
.warning-box { background: #fffbeb; border-left: 4px solid #f59e0b; padding: 0.75rem 1rem; border-radius: 4px; margin: 0.5rem 0; }
.success-box { background: #f0fdf4; border-left: 4px solid #22c55e; padding: 0.75rem 1rem; border-radius: 4px; margin: 0.5rem 0; }
.step-header { font-size: 1.4rem; font-weight: 700; margin-bottom: 0.5rem; color: #1F2937; }
.section-header { font-size: 1rem; font-weight: 600; color: #4F46E5; margin-top: 1.5rem; margin-bottom: 0.5rem; }
</style>
""", unsafe_allow_html=True)

# ─── Session State Init ──────────────────────────────────────────────────────
defaults = {
    "step": 1,
    "enriched": False,
    "business_data": {},
    "generated_schemas": {},
    "selected_schemas": [],
    "services": [{"name": "", "url": "", "service_type": "", "audience": ""}],
    "sub_services": [{"name": "", "url": "", "service_type": ""}],
    "service_categories": [{"name": "", "url": "", "description": "", "services": []}],
    "faq_questions": [{"question": "", "answer": "", "answer_links": []}],
    "pricing_tiers": [{"name": "", "price": "", "url": "", "billing_period": "MON", "description": ""}],
    "breadcrumb_items": [{"name": "Home", "url": ""}, {"name": "", "url": ""}],
    "opening_hours": [],
    "locations": [],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🔍 Schema Generator")
    st.markdown("---")

    business_type = st.selectbox(
        "Business Type",
        ["Local / Service Business", "E-commerce", "SaaS / Software"],
        key="business_type_select",
    )
    st.session_state["business_type"] = business_type

    st.markdown("---")
    st.markdown("**Steps**")
    steps = ["1. Business Info", "2. Select Schemas", "3. Customize", "4. Output"]
    for i, s in enumerate(steps, 1):
        style = "**→** " if st.session_state["step"] == i else "&nbsp;&nbsp;&nbsp;"
        st.markdown(f"{style}{s}", unsafe_allow_html=True)

    st.markdown("---")
    if st.button("🔄 Start Over", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# ─── Step 1: Business Info ───────────────────────────────────────────────────
if st.session_state["step"] == 1:
    st.markdown('<div class="step-header">Step 1 — Business Information</div>', unsafe_allow_html=True)
    st.caption("Fill in your business details. Use the AI Enrich button to auto-fill advanced fields.")

    col1, col2 = st.columns(2)
    with col1:
        business_name = st.text_input("Business Name *", value=st.session_state["business_data"].get("business_name", ""))
    with col2:
        website_url = st.text_input("Website URL *", value=st.session_state["business_data"].get("website_url", ""), placeholder="https://example.com")

    col3, col4 = st.columns(2)
    with col3:
        legal_name = st.text_input("Legal Name", value=st.session_state["business_data"].get("legal_name", ""), placeholder="Same as business name if unchanged")
    with col4:
        alternate_name = st.text_input("Alternate Name", value=st.session_state["business_data"].get("alternate_name", ""))

    client_slug_default = slugify(business_name) if business_name else ""
    client_slug = st.text_input("Client Slug (for file names)", value=st.session_state["business_data"].get("client_slug", client_slug_default), placeholder="e.g. acme-plumbing")
    st.caption("Files will be named: `{client-slug}-homepage.json`, `{client-slug}-about.json`, etc.")

    # ── Fact Cheat Upload ──────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Fact Cheat Upload (Optional)</div>', unsafe_allow_html=True)
    st.caption("Upload a pre-verified Fact Cheat (.txt or .md) to auto-fill all fields with accurate business data.")

    uploaded_fact_cheat = st.file_uploader(
        "Upload Fact Cheat File",
        type=["txt", "md"],
        help="A structured document with verified business facts — name, phone, address, services, hours, ratings, etc.",
        key="fact_cheat_uploader",
    )

    if uploaded_fact_cheat is not None:
        col_fc1, col_fc2 = st.columns([3, 1])
        with col_fc1:
            st.info(f"📄 **{uploaded_fact_cheat.name}** ready to extract.")
        with col_fc2:
            extract_btn = st.button("📋 Extract Data", use_container_width=True)
        if extract_btn:
            with st.spinner("Extracting business data from Fact Cheat..."):
                try:
                    fact_cheat_content = uploaded_fact_cheat.read().decode("utf-8", errors="ignore")
                    extracted = extract_from_fact_cheat(fact_cheat_content)

                    # Merge into business_data (extracted values take precedence)
                    merged = dict(st.session_state["business_data"])
                    for k, v in extracted.items():
                        if v or v == 0:
                            merged[k] = v
                    st.session_state["business_data"] = merged

                    # Populate services list if extracted
                    if extracted.get("services"):
                        st.session_state["services"] = [
                            {
                                "name": s.get("name", ""),
                                "url": s.get("url", ""),
                                "service_type": s.get("service_type", s.get("name", "")),
                                "audience": s.get("audience", ""),
                            }
                            for s in extracted["services"]
                        ]

                    # Pre-populate opening hours widget keys so checkboxes render correctly
                    if extracted.get("has_24_7"):
                        for d in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
                            st.session_state[f"open_{d}"] = True
                            st.session_state[f"opens_{d}"] = "00:00"
                            st.session_state[f"closes_{d}"] = "23:59"
                    elif extracted.get("opening_hours"):
                        for oh in extracted["opening_hours"]:
                            d = oh.get("day", "")
                            if d:
                                st.session_state[f"open_{d}"] = True
                                st.session_state[f"opens_{d}"] = oh.get("opens", "09:00")
                                st.session_state[f"closes_{d}"] = oh.get("closes", "17:00")

                    filled = sum(1 for v in extracted.values() if v)
                    st.success(f"✅ Extracted {filled} fields from Fact Cheat! Review and edit below.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Extraction failed: {e}")

    st.markdown('<div class="section-header">AI Enrichment + Website Scraping</div>', unsafe_allow_html=True)
    st.caption("Scrapes the website URL for logo, images, phone, address, maps link, and existing schema — then calls AI for Wikidata, entity links, and topical authority topics.")
    col_enrich1, col_enrich2 = st.columns([3, 1])
    with col_enrich2:
        enrich_btn = st.button("✨ Enrich with AI", use_container_width=True, disabled=not (business_name and website_url))

    if enrich_btn:
        scraped = {}
        with st.spinner("Step 1/2 — Scraping website for logo, images, address, and schema data..."):
            try:
                scraped = scrape_business_page(normalize_url(website_url))
                # Merge scraped data into business_data immediately
                merged = dict(st.session_state["business_data"])
                for k, v in scraped.items():
                    if v and not merged.get(k):
                        merged[k] = v
                # Default country to US if not set
                if not merged.get("country"):
                    merged["country"] = "US"
                st.session_state["business_data"] = merged
                # Pre-populate opening hours from scraper if found
                if scraped.get("opening_hours"):
                    for oh in scraped["opening_hours"]:
                        d = oh.get("day", "")
                        if d:
                            st.session_state[f"open_{d}"] = True
                            st.session_state[f"opens_{d}"] = oh.get("opens", "09:00")
                            st.session_state[f"closes_{d}"] = oh.get("closes", "17:00")
            except Exception as e:
                st.warning(f"Scraping partially failed: {e} — continuing with AI enrichment.")

        with st.spinner("Step 2/2 — Enriching with Claude Sonnet 4.5 for Wikidata, entity links, and topical authority..."):
            try:
                enriched = enrich_business(business_name, normalize_url(website_url), business_type)
                st.session_state["ai_enriched"] = enriched
                st.session_state["enriched"] = True
                scraped_fields = len([v for v in scraped.values() if v])
                st.success(
                    f"Done! Scraped {scraped_fields} field(s) from the website. "
                    "AI enrichment complete. Review fields below."
                )
            except Exception as e:
                st.error(f"AI enrichment failed: {e}")
                st.session_state["ai_enriched"] = {}

    ai = st.session_state.get("ai_enriched", {})

    st.markdown('<div class="section-header">Description & Identity</div>', unsafe_allow_html=True)
    description = st.text_area("Description *", value=st.session_state["business_data"].get("description", ai.get("description", "")), height=100)
    disambiguating = st.text_area("Disambiguating Description", value=st.session_state["business_data"].get("disambiguating_description", ai.get("disambiguating_description", "")), height=80)
    slogan = st.text_input("Slogan / Tagline", value=st.session_state["business_data"].get("slogan", ai.get("slogan", "")))
    schema_subtype = st.text_input("Schema Subtype", value=st.session_state["business_data"].get("schema_subtype", ai.get("schema_subtype", "LocalBusiness")), help="e.g. HVACBusiness, LegalService, Dentist, AutoRepair, Organization")

    st.markdown('<div class="section-header">Contact Details</div>', unsafe_allow_html=True)
    col5, col6 = st.columns(2)
    with col5:
        telephone = st.text_input("Telephone", value=st.session_state["business_data"].get("telephone", ""))
        email = st.text_input("Email", value=st.session_state["business_data"].get("email", ""))
    with col6:
        founding_date = st.text_input("Founding Date", value=st.session_state["business_data"].get("founding_date", ""), placeholder="YYYY or YYYY-MM-DD")
        price_range = st.selectbox("Price Range", ["", "$", "$$", "$$$", "$$$$"], index=["", "$", "$$", "$$$", "$$$$"].index(st.session_state["business_data"].get("price_range", "")))

    st.markdown('<div class="section-header">Address</div>', unsafe_allow_html=True)
    col7, col8 = st.columns(2)
    with col7:
        street_address = st.text_input("Street Address", value=st.session_state["business_data"].get("street_address", ""))
        city = st.text_input("City", value=st.session_state["business_data"].get("city", ""))
    with col8:
        state = st.text_input("State / Region", value=st.session_state["business_data"].get("state", ""))
        postal_code = st.text_input("Postal Code", value=st.session_state["business_data"].get("postal_code", ""))
    country = st.text_input("Country", value=st.session_state["business_data"].get("country", "US"), placeholder="e.g. US, AU, GB")

    st.markdown('<div class="section-header">Media</div>', unsafe_allow_html=True)
    col9, col10 = st.columns(2)
    with col9:
        logo_url = st.text_input("Logo URL", value=st.session_state["business_data"].get("logo_url", ""))
        image_url = st.text_input("Business Image URL", value=st.session_state["business_data"].get("image_url", ""))
    with col10:
        has_map = st.text_input("Google Maps URL (hasMap)", value=st.session_state["business_data"].get("has_map", ""), placeholder="https://www.google.com/maps/place/...")

    st.markdown('<div class="section-header">sameAs — External Profiles</div>', unsafe_allow_html=True)
    st.caption("One URL per line. Include: Google Business Profile, social media, Wikidata entity, industry directories.")
    ai_same_as = ai.get("suggested_same_as", [])
    default_same_as = "\n".join(st.session_state["business_data"].get("same_as", ai_same_as))
    same_as_raw = st.text_area("sameAs URLs", value=default_same_as, height=120, placeholder="https://www.google.com/maps/place/...\nhttps://www.facebook.com/yourbusiness\nhttps://www.instagram.com/yourbusiness\nhttps://www.wikidata.org/wiki/Q...")

    st.markdown('<div class="section-header">knowsAbout — Topical Authority</div>', unsafe_allow_html=True)
    st.caption("Topics the business is an expert in. Each row: Topic Name | Wikidata URL | Wikipedia URL")
    ai_knows = ai.get("knows_about", [])
    default_knows = "\n".join([f"{k.get('name','')} | {k.get('wikidata_id','')} | {k.get('wikipedia_url','')}" for k in (st.session_state["business_data"].get("knows_about_raw", ai_knows))])
    knows_about_raw = st.text_area("knowsAbout Topics (one per line: Name | Wikidata URL | Wikipedia URL)", value=default_knows, height=150, placeholder="HVAC | https://www.wikidata.org/wiki/Q1798773 | https://en.wikipedia.org/wiki/Heating,_ventilation,_and_air_conditioning")

    st.markdown('<div class="section-header">additionalType — Entity Disambiguation</div>', unsafe_allow_html=True)
    st.caption("Wikipedia/Wikidata URLs that describe the business category. One per line.")
    ai_add_types = ai.get("additional_types", [])
    default_add_types = "\n".join(st.session_state["business_data"].get("additional_types", ai_add_types))
    additional_types_raw = st.text_area("additionalType URLs", value=default_add_types, height=80, placeholder="https://en.wikipedia.org/wiki/Plumbing\nhttps://www.wikidata.org/wiki/Q82048")

    st.markdown('<div class="section-header">Founder / Primary Person (E-E-A-T)</div>', unsafe_allow_html=True)
    col11, col12 = st.columns(2)
    with col11:
        founder_name = st.text_input("Founder / Author Name", value=st.session_state["business_data"].get("founder_name", ""))
        job_title = st.text_input("Job Title", value=st.session_state["business_data"].get("job_title", ""))
        alumni_of = st.text_input("alumniOf (University/School)", value=st.session_state["business_data"].get("alumni_of", ""))
    with col12:
        person_image = st.text_input("Person Image URL", value=st.session_state["business_data"].get("person_image", ""))
        knows_language = st.text_input("knowsLanguage", value=st.session_state["business_data"].get("knows_language", ""), placeholder="english, spanish")
        has_credential = st.text_input("hasCredential", value=st.session_state["business_data"].get("has_credential", ""))

    person_same_as_raw = st.text_area("Person sameAs (LinkedIn, Twitter, etc.)", value="\n".join(st.session_state["business_data"].get("person_same_as", [])), height=80, placeholder="https://www.linkedin.com/in/yourname/\nhttps://twitter.com/yourhandle")

    st.markdown('<div class="section-header">Area Served</div>', unsafe_allow_html=True)
    col13, col14 = st.columns(2)
    with col13:
        cities_raw = st.text_area("Cities Served (one per line)", value="\n".join(st.session_state["business_data"].get("cities", [])), height=100, placeholder="Los Angeles\nSanta Monica\nBeverly Hills")
        area_served_name = st.text_input("Area Served Name (fallback)", value=st.session_state["business_data"].get("area_served_name", ai.get("area_served_suggestion", "")), placeholder="Greater Los Angeles")
    with col14:
        postal_codes_raw = st.text_area("Postal Codes (one per line or space-separated)", value="\n".join(st.session_state["business_data"].get("postal_codes", [])), height=100, placeholder="90001\n90002\n90210")

    st.markdown('<div class="section-header">Opening Hours</div>', unsafe_allow_html=True)
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    opening_hours = []
    with st.expander("Configure Opening Hours", expanded=False):
        for day in days:
            col_d, col_o, col_c, col_on = st.columns([2, 2, 2, 1])
            with col_d:
                st.text(day)
            with col_on:
                is_open = st.checkbox("Open", value=day not in ["Sunday"], key=f"open_{day}")
            if is_open:
                with col_o:
                    opens = st.text_input("Opens", value="09:00", key=f"opens_{day}")
                with col_c:
                    closes = st.text_input("Closes", value="17:00", key=f"closes_{day}")
                opening_hours.append({"day": day, "opens": opens, "closes": closes})

    # ── Services (for local business) ────────────────────────────────────────
    if business_type == "Local / Service Business":
        st.markdown('<div class="section-header">Services</div>', unsafe_allow_html=True)
        st.caption("Add the services this business offers.")
        services = st.session_state["services"]
        for idx, svc in enumerate(services):
            col_s1, col_s2, col_s3 = st.columns([3, 3, 1])
            with col_s1:
                services[idx]["name"] = st.text_input(f"Service Name {idx+1}", value=svc.get("name", ""), key=f"svc_name_{idx}")
            with col_s2:
                services[idx]["url"] = st.text_input(f"Service URL {idx+1}", value=svc.get("url", ""), key=f"svc_url_{idx}")
            with col_s3:
                if st.button("−", key=f"rm_svc_{idx}") and len(services) > 1:
                    services.pop(idx)
                    st.rerun()
            services[idx]["service_type"] = st.text_input(f"Service Type {idx+1}", value=svc.get("service_type", svc.get("name", "")), key=f"svc_type_{idx}")
        if st.button("+ Add Service"):
            services.append({"name": "", "url": "", "service_type": "", "audience": ""})
            st.rerun()
        st.session_state["services"] = services

    # ── Navigation ────────────────────────────────────────────────────────────
    st.markdown("---")
    if st.button("Next: Select Schemas →", type="primary", use_container_width=True):
        # Parse and save all data
        knows_about = []
        for line in knows_about_raw.strip().split("\n"):
            parts = [p.strip() for p in line.split("|")]
            if parts[0]:
                entry = {"name": parts[0]}
                if len(parts) > 1:
                    entry["wikidata_id"] = parts[1]
                if len(parts) > 2:
                    entry["wikipedia_url"] = parts[2]
                knows_about.append(entry)

        st.session_state["business_data"] = {
            "business_name": business_name,
            "website_url": normalize_url(website_url),
            "legal_name": legal_name,
            "alternate_name": alternate_name,
            "client_slug": client_slug or slugify(business_name),
            "description": description,
            "disambiguating_description": disambiguating,
            "slogan": slogan,
            "schema_subtype": schema_subtype,
            "telephone": telephone,
            "email": email,
            "founding_date": founding_date,
            "price_range": price_range,
            "street_address": street_address,
            "city": city,
            "state": state,
            "postal_code": postal_code,
            "country": country,
            "logo_url": logo_url,
            "image_url": image_url,
            "has_map": has_map,
            "same_as": parse_urls_input(same_as_raw),
            "knows_about": knows_about,
            "knows_about_raw": knows_about,
            "additional_types": parse_urls_input(additional_types_raw),
            "founder_name": founder_name,
            "job_title": job_title,
            "alumni_of": alumni_of,
            "person_image": person_image,
            "knows_language": knows_language,
            "has_credential": has_credential,
            "person_same_as": parse_urls_input(person_same_as_raw),
            "cities": parse_cities_input(cities_raw),
            "postal_codes": parse_postal_codes(postal_codes_raw),
            "area_served_name": area_served_name,
            "opening_hours": opening_hours,
            "services": [s for s in st.session_state["services"] if s.get("name")],
            "language": "en",
        }
        st.session_state["step"] = 2
        st.rerun()

# ─── Step 2: Select Schemas ──────────────────────────────────────────────────
elif st.session_state["step"] == 2:
    st.markdown('<div class="step-header">Step 2 — Select Schemas to Generate</div>', unsafe_allow_html=True)

    btype = st.session_state.get("business_type", "Local / Service Business")

    all_schemas = {
        "homepage": "Homepage (WebPage + WebSite + Organization + Founder)",
        "website": "WebSite (standalone)",
        "about": "About Page (AboutPage + Person E-E-A-T)",
        "contact": "Contact Page",
        "organization": "Organization / LocalBusiness (root entity)",
        "person": "Person (standalone founder schema)",
        "service_single": "Service Page (single service)",
        "service_multi": "Services Page (multi-service with OfferCatalog)",
        "blog": "Blog Post / Article",
        "faq": "FAQ Page",
        "breadcrumb": "BreadcrumbList",
    }

    if btype == "E-commerce":
        all_schemas["product"] = "Product (with Offer, AggregateRating, Merchant Center)"
    if btype == "SaaS / Software":
        all_schemas["saas_app"] = "WebApplication (SaaS product)"
        all_schemas["saas_pricing"] = "Pricing Page (AggregateOffer + UnitPriceSpecification)"

    # Default selections by business type
    defaults_by_type = {
        "Local / Service Business": ["homepage", "about", "contact", "organization", "service_single", "faq", "breadcrumb"],
        "E-commerce": ["homepage", "about", "contact", "organization", "product", "faq"],
        "SaaS / Software": ["homepage", "about", "contact", "organization", "saas_app", "saas_pricing", "faq"],
    }
    default_sel = defaults_by_type.get(btype, list(all_schemas.keys()))

    prev_sel = st.session_state.get("selected_schemas", default_sel)

    st.caption(f"Pre-selected for **{btype}**. Add or remove as needed.")
    selected = []
    cols = st.columns(2)
    for i, (key, label) in enumerate(all_schemas.items()):
        with cols[i % 2]:
            if st.checkbox(label, value=key in prev_sel, key=f"sel_{key}"):
                selected.append(key)

    st.markdown("---")
    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("← Back"):
            st.session_state["step"] = 1
            st.rerun()
    with col_next:
        if st.button("Next: Customize →", type="primary", disabled=not selected):
            st.session_state["selected_schemas"] = selected
            st.session_state["step"] = 3
            st.rerun()

# ─── Step 3: Customize ──────────────────────────────────────────────────────
elif st.session_state["step"] == 3:
    st.markdown('<div class="step-header">Step 3 — Customize Selected Schemas</div>', unsafe_allow_html=True)
    data = st.session_state["business_data"]
    selected = st.session_state["selected_schemas"]
    base_url = data.get("website_url", "")

    tabs = st.tabs([s.replace("_", " ").title() for s in selected])

    for tab, schema_key in zip(tabs, selected):
        with tab:

            # ── Homepage ──────────────────────────────────────────────────────
            if schema_key == "homepage":
                st.caption("Homepage schema nests Organization, WebSite, and Person.")
                data["page_title"] = st.text_input("Page Title", value=data.get("page_title", data.get("business_name", "")), key="hp_title")
                data["page_description"] = st.text_area("Meta Description", value=data.get("page_description", data.get("description", "")), height=80, key="hp_desc")
                related_links_raw = st.text_area("relatedLink URLs (one per line)", value="\n".join(data.get("related_links", [])), height=80, key="hp_related", placeholder=f"{base_url}/about\n{base_url}/services\n{base_url}/contact")
                data["related_links"] = parse_urls_input(related_links_raw)

            # ── WebSite ───────────────────────────────────────────────────────
            elif schema_key == "website":
                st.caption("Standalone WebSite schema with optional SearchAction.")
                data["enable_search_action"] = st.checkbox("Include SearchAction (SiteLinks Searchbox)", value=data.get("enable_search_action", False), key="ws_search")

            # ── About Page ────────────────────────────────────────────────────
            elif schema_key == "about":
                st.caption("AboutPage with Person as mainEntity — full E-E-A-T signals.")
                data["about_page_url"] = st.text_input("About Page URL", value=data.get("about_page_url", f"{base_url}/about"), key="about_url")
                data["about_page_title"] = st.text_input("About Page Title", value=data.get("about_page_title", f"About {data.get('business_name', '')}"), key="about_title")
                data["about_page_description"] = st.text_area("About Page Description", value=data.get("about_page_description", ""), height=80, key="about_desc")
                data["person_description"] = st.text_area("Person Description", value=data.get("person_description", ""), height=80, key="person_desc")
                data["person_url"] = st.text_input("Person Profile URL", value=data.get("person_url", data.get("about_page_url", "")), key="person_url_field")

            # ── Contact Page ──────────────────────────────────────────────────
            elif schema_key == "contact":
                data["contact_page_url"] = st.text_input("Contact Page URL", value=data.get("contact_page_url", f"{base_url}/contact"), key="contact_url")
                data["contact_page_title"] = st.text_input("Contact Page Title", value=data.get("contact_page_title", f"Contact {data.get('business_name', '')}"), key="contact_title")
                data["contact_page_description"] = st.text_area("Contact Page Description", value=data.get("contact_page_description", ""), height=60, key="contact_desc")

            # ── Organization ──────────────────────────────────────────────────
            elif schema_key == "organization":
                st.caption("Root entity schema — Organization or LocalBusiness.")
                data["founding_location"] = st.text_input("Founding Location", value=data.get("founding_location", f"{data.get('city', '')}, {data.get('country', '')}").strip(", "), key="org_founding_loc")
                data["payment_accepted"] = st.text_input("Payment Accepted", value=data.get("payment_accepted", ""), placeholder="Visa, Mastercard, Cash", key="org_payment")

            # ── Person ────────────────────────────────────────────────────────
            elif schema_key == "person":
                st.caption("Standalone Person schema for the founder/primary author.")
                data["job_title_same_as"] = st.text_input("Job Title sameAs URL", value=data.get("job_title_same_as", ""), placeholder="URL to job description (talentlyft, workable, etc.)", key="person_jt_sameas")
                data["alumni_of_url"] = st.text_input("alumniOf URL (Wikidata/official)", value=data.get("alumni_of_url", ""), key="person_alumni_url")
                data["award"] = st.text_input("Awards", value=data.get("award", ""), key="person_award")
                data["nationality"] = st.text_input("Nationality", value=data.get("nationality", ""), key="person_nationality")

            # ── Service (Single) ──────────────────────────────────────────────
            elif schema_key == "service_single":
                st.caption("Single service page with provider, areaServed, and sub-services.")
                data["service_name"] = st.text_input("Primary Service Name *", value=data.get("service_name", ""), key="ss_name")
                data["service_page_url"] = st.text_input("Service Page URL", value=data.get("service_page_url", ""), placeholder=f"{base_url}/services/service-name", key="ss_url")
                data["service_description"] = st.text_area("Service Description", value=data.get("service_description", ""), height=80, key="ss_desc")
                data["service_type"] = st.text_input("serviceType", value=data.get("service_type", data.get("service_name", "")), key="ss_type")
                data["service_audience"] = st.text_input("Service Audience", value=data.get("service_audience", ""), placeholder="Residential homeowners", key="ss_audience")
                data["service_additional_type"] = st.text_input("additionalType URL (productontology/Wikipedia)", value=data.get("service_additional_type", ""), key="ss_addtype")
                st.markdown("**Sub-services (hasOfferCatalog)**")
                sub_services = st.session_state["sub_services"]
                for idx, ss in enumerate(sub_services):
                    c1, c2, c3 = st.columns([3, 3, 1])
                    with c1:
                        sub_services[idx]["name"] = st.text_input(f"Sub-service {idx+1}", value=ss.get("name", ""), key=f"ss_sub_name_{idx}")
                    with c2:
                        sub_services[idx]["url"] = st.text_input(f"URL {idx+1}", value=ss.get("url", ""), key=f"ss_sub_url_{idx}")
                    with c3:
                        if st.button("−", key=f"rm_ss_{idx}") and len(sub_services) > 1:
                            sub_services.pop(idx)
                            st.rerun()
                if st.button("+ Add Sub-service", key="add_ss"):
                    sub_services.append({"name": "", "url": "", "service_type": ""})
                    st.rerun()
                st.session_state["sub_services"] = sub_services
                data["sub_services"] = [s for s in sub_services if s.get("name")]

            # ── Service (Multi) ───────────────────────────────────────────────
            elif schema_key == "service_multi":
                st.caption("Multi-service page using @graph with multiple OfferCatalog entries.")
                data["services_page_url"] = st.text_input("Services Page URL", value=data.get("services_page_url", f"{base_url}/services"), key="sm_url")
                data["services_page_title"] = st.text_input("Services Page Title", value=data.get("services_page_title", f"Services — {data.get('business_name', '')}"), key="sm_title")
                data["services_page_description"] = st.text_area("Services Page Description", value=data.get("services_page_description", ""), height=60, key="sm_desc")
                data["service_categories"] = st.session_state["service_categories"]
                cats = st.session_state["service_categories"]
                for idx, cat in enumerate(cats):
                    with st.expander(f"Category {idx+1}: {cat.get('name', 'New Category')}", expanded=idx == 0):
                        cats[idx]["name"] = st.text_input("Category Name", value=cat.get("name", ""), key=f"cat_name_{idx}")
                        cats[idx]["url"] = st.text_input("Category URL", value=cat.get("url", ""), key=f"cat_url_{idx}")
                        cats[idx]["description"] = st.text_area("Category Description", value=cat.get("description", ""), height=60, key=f"cat_desc_{idx}")
                        services_in_cat = cat.get("services", [{"name": "", "url": ""}])
                        for sidx, s in enumerate(services_in_cat):
                            c1, c2 = st.columns(2)
                            with c1:
                                services_in_cat[sidx]["name"] = st.text_input(f"Service {sidx+1}", value=s.get("name", ""), key=f"cat_{idx}_svc_{sidx}")
                            with c2:
                                services_in_cat[sidx]["url"] = st.text_input(f"URL {sidx+1}", value=s.get("url", ""), key=f"cat_{idx}_svc_url_{sidx}")
                        if st.button(f"+ Add Service to Category {idx+1}", key=f"add_cat_svc_{idx}"):
                            services_in_cat.append({"name": "", "url": ""})
                            st.rerun()
                        cats[idx]["services"] = services_in_cat
                        if st.button(f"Remove Category {idx+1}", key=f"rm_cat_{idx}") and len(cats) > 1:
                            cats.pop(idx)
                            st.rerun()
                if st.button("+ Add Service Category"):
                    cats.append({"name": "", "url": "", "description": "", "services": []})
                    st.rerun()
                st.session_state["service_categories"] = cats
                data["service_categories"] = cats

            # ── Blog Post ─────────────────────────────────────────────────────
            elif schema_key == "blog":
                st.caption("BlogPosting with author, publisher, and entity mentions.")
                data["post_url"] = st.text_input("Post URL *", value=data.get("post_url", ""), placeholder=f"{base_url}/blog/post-title", key="blog_url")
                data["post_title"] = st.text_input("Post Title *", value=data.get("post_title", ""), key="blog_title")
                data["post_description"] = st.text_area("Meta Description", value=data.get("post_description", ""), height=60, key="blog_desc")
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    data["date_published"] = st.text_input("Date Published *", value=data.get("date_published", ""), placeholder="YYYY-MM-DD", key="blog_date")
                with col_b2:
                    data["date_modified"] = st.text_input("Date Modified", value=data.get("date_modified", ""), placeholder="YYYY-MM-DD", key="blog_modified")
                data["post_image"] = st.text_input("Featured Image URL *", value=data.get("post_image", ""), key="blog_img")
                data["keywords"] = st.text_input("Keywords", value=data.get("keywords", ""), key="blog_kw")
                data["article_section"] = st.text_input("Article Section", value=data.get("article_section", ""), key="blog_section")
                st.markdown("**Mentions (Wikidata entities in this article)**")
                st.caption("Name | Wikidata URL | Wikipedia URL")
                mentions_raw = st.text_area("Mentions", value="\n".join([f"{m.get('name','')} | {m.get('wikidata_id','')} | {m.get('wikipedia_url','')}" for m in data.get("mentions", [])]), height=100, key="blog_mentions")
                mentions = []
                for line in mentions_raw.strip().split("\n"):
                    parts = [p.strip() for p in line.split("|")]
                    if parts[0]:
                        m = {"name": parts[0], "type": "Thing"}
                        if len(parts) > 1:
                            m["wikidata_id"] = parts[1]
                        if len(parts) > 2:
                            m["wikipedia_url"] = parts[2]
                        mentions.append(m)
                data["mentions"] = mentions

            # ── FAQ Page ──────────────────────────────────────────────────────
            elif schema_key == "faq":
                st.caption("FAQPage with isPartOf WebPage, reviewedBy, and entity mentions in answers.")
                data["faq_page_url"] = st.text_input("FAQ Page URL", value=data.get("faq_page_url", f"{base_url}/faq"), key="faq_url")
                data["faq_page_title"] = st.text_input("FAQ Page Title", value=data.get("faq_page_title", f"FAQ — {data.get('business_name', '')}"), key="faq_title")
                data["faq_page_description"] = st.text_area("FAQ Page Description", value=data.get("faq_page_description", ""), height=60, key="faq_desc")
                questions = st.session_state["faq_questions"]
                for idx, q in enumerate(questions):
                    with st.expander(f"Q{idx+1}: {q.get('question', 'New Question')[:60]}", expanded=idx == 0):
                        questions[idx]["question"] = st.text_input(f"Question {idx+1} *", value=q.get("question", ""), key=f"faq_q_{idx}")
                        questions[idx]["answer"] = st.text_area(f"Answer {idx+1} *", value=q.get("answer", ""), height=100, key=f"faq_a_{idx}")
                        if st.button(f"Remove Q{idx+1}", key=f"rm_faq_{idx}") and len(questions) > 1:
                            questions.pop(idx)
                            st.rerun()
                if st.button("+ Add Question", key="add_faq"):
                    questions.append({"question": "", "answer": "", "answer_links": []})
                    st.rerun()
                st.session_state["faq_questions"] = questions
                data["questions"] = [q for q in questions if q.get("question") and q.get("answer")]

            # ── Product ───────────────────────────────────────────────────────
            elif schema_key == "product":
                st.caption("Product schema with Offer, AggregateRating, and Merchant Center data.")
                data["product_url"] = st.text_input("Product URL *", value=data.get("product_url", ""), key="prod_url")
                data["product_name"] = st.text_input("Product Name *", value=data.get("product_name", ""), key="prod_name")
                data["product_description"] = st.text_area("Product Description", value=data.get("product_description", ""), height=80, key="prod_desc")
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    data["sku"] = st.text_input("SKU", value=data.get("sku", ""), key="prod_sku")
                    data["gtin13"] = st.text_input("GTIN-13", value=data.get("gtin13", ""), key="prod_gtin")
                    data["price"] = st.text_input("Price *", value=data.get("price", ""), key="prod_price")
                    data["currency"] = st.text_input("Currency *", value=data.get("currency", "USD"), key="prod_currency")
                with col_p2:
                    data["availability"] = st.selectbox("Availability", ["In Stock", "Out of Stock", "Pre-order", "Discontinued"], key="prod_avail")
                    data["price_valid_until"] = st.text_input("Price Valid Until", value=data.get("price_valid_until", ""), placeholder="YYYY-MM-DD", key="prod_valid")
                    data["product_image"] = st.text_input("Product Image URL *", value=data.get("product_image", ""), key="prod_img")
                col_p3, col_p4 = st.columns(2)
                with col_p3:
                    data["aggregate_rating_value"] = st.text_input("Avg Rating (e.g. 4.5)", value=data.get("aggregate_rating_value", ""), key="prod_rating")
                with col_p4:
                    data["aggregate_rating_count"] = st.text_input("Review Count", value=data.get("aggregate_rating_count", ""), key="prod_rcount")
                st.markdown("**Merchant Center / Shipping**")
                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    shipping_rate = st.text_input("Shipping Rate (0 for free)", value=data.get("shipping_rate", ""), key="prod_ship_rate")
                    data["shipping_rate"] = shipping_rate if shipping_rate != "" else None
                    data["shipping_country"] = st.text_input("Shipping Country", value=data.get("shipping_country", ""), placeholder="US", key="prod_ship_country")
                with col_s2:
                    data["handling_time_min"] = st.number_input("Min Handling Days", value=int(data.get("handling_time_min", 1)), min_value=0, key="prod_hand_min")
                    data["handling_time_max"] = st.number_input("Max Handling Days", value=int(data.get("handling_time_max", 3)), min_value=0, key="prod_hand_max")
                st.markdown("**Return Policy**")
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    data["return_days"] = st.number_input("Return Window (days)", value=int(data.get("return_days", 30)), min_value=0, key="prod_ret_days")
                    data["return_policy_country"] = st.text_input("Return Policy Country", value=data.get("return_policy_country", ""), placeholder="US", key="prod_ret_country")
                with col_r2:
                    data["return_method"] = st.selectbox("Return Method", ["ReturnByMail", "ReturnInStore", "ReturnAtKiosk"], key="prod_ret_method")
                    data["return_fees"] = st.selectbox("Return Fees", ["FreeReturn", "RestockingFee", "OriginalShippingFees"], key="prod_ret_fees")

            # ── SaaS App ──────────────────────────────────────────────────────
            elif schema_key == "saas_app":
                st.caption("WebApplication schema for the SaaS product itself.")
                data["app_url"] = st.text_input("App URL (where users access the app)", value=data.get("app_url", base_url), key="saas_app_url")
                data["app_name"] = st.text_input("App/Product Name", value=data.get("app_name", data.get("business_name", "")), key="saas_app_name")
                data["app_description"] = st.text_area("App Description", value=data.get("app_description", data.get("description", "")), height=80, key="saas_app_desc")
                data["marketing_url"] = st.text_input("Marketing URL (homepage)", value=data.get("marketing_url", base_url), key="saas_mkt_url")
                col_sa1, col_sa2 = st.columns(2)
                with col_sa1:
                    data["app_category"] = st.text_input("applicationCategory", value=data.get("app_category", "BusinessApplication"), key="saas_cat")
                    data["app_suite"] = st.text_input("applicationSuite (if part of a suite)", value=data.get("app_suite", ""), key="saas_suite")
                with col_sa2:
                    data["browser_requirements"] = st.text_input("browserRequirements", value=data.get("browser_requirements", "Requires JavaScript. Requires HTML5."), key="saas_browser")
                    data["operating_system"] = st.text_input("operatingSystem", value=data.get("operating_system", "Web Browser"), key="saas_os")

            # ── SaaS Pricing ──────────────────────────────────────────────────
            elif schema_key == "saas_pricing":
                st.caption("Pricing page with AggregateOffer and UnitPriceSpecification per tier.")
                data["pricing_page_url"] = st.text_input("Pricing Page URL", value=data.get("pricing_page_url", f"{base_url}/pricing"), key="sp_url")
                data["pricing_page_title"] = st.text_input("Pricing Page Title", value=data.get("pricing_page_title", f"Pricing — {data.get('business_name', '')}"), key="sp_title")
                data["pricing_page_description"] = st.text_area("Pricing Page Description", value=data.get("pricing_page_description", ""), height=60, key="sp_desc")
                data["currency"] = st.text_input("Currency", value=data.get("currency", "USD"), key="sp_currency")
                tiers = st.session_state["pricing_tiers"]
                for idx, tier in enumerate(tiers):
                    with st.expander(f"Tier {idx+1}: {tier.get('name', 'New Tier')}", expanded=idx == 0):
                        tiers[idx]["name"] = st.text_input(f"Plan Name {idx+1}", value=tier.get("name", ""), key=f"tier_name_{idx}")
                        tiers[idx]["price"] = st.text_input(f"Price {idx+1}", value=tier.get("price", ""), key=f"tier_price_{idx}")
                        tiers[idx]["url"] = st.text_input(f"Signup URL {idx+1}", value=tier.get("url", ""), key=f"tier_url_{idx}")
                        tiers[idx]["billing_period"] = st.selectbox(f"Billing Period {idx+1}", ["MON", "ANN", "DAY", "WEE"], key=f"tier_period_{idx}")
                        tiers[idx]["description"] = st.text_area(f"Description {idx+1}", value=tier.get("description", ""), height=60, key=f"tier_desc_{idx}")
                        if st.button(f"Remove Tier {idx+1}", key=f"rm_tier_{idx}") and len(tiers) > 1:
                            tiers.pop(idx)
                            st.rerun()
                if st.button("+ Add Pricing Tier"):
                    tiers.append({"name": "", "price": "", "url": "", "billing_period": "MON", "description": ""})
                    st.rerun()
                st.session_state["pricing_tiers"] = tiers
                data["pricing_tiers"] = tiers

            # ── BreadcrumbList ────────────────────────────────────────────────
            elif schema_key == "breadcrumb":
                st.caption("BreadcrumbList for the current page trail.")
                items = st.session_state["breadcrumb_items"]
                for idx, item in enumerate(items):
                    c1, c2, c3 = st.columns([3, 3, 1])
                    with c1:
                        items[idx]["name"] = st.text_input(f"Name {idx+1}", value=item.get("name", ""), key=f"bc_name_{idx}")
                    with c2:
                        items[idx]["url"] = st.text_input(f"URL {idx+1}", value=item.get("url", base_url if idx == 0 else ""), key=f"bc_url_{idx}")
                    with c3:
                        if st.button("−", key=f"rm_bc_{idx}") and len(items) > 1:
                            items.pop(idx)
                            st.rerun()
                if st.button("+ Add Breadcrumb", key="add_bc"):
                    items.append({"name": "", "url": ""})
                    st.rerun()
                st.session_state["breadcrumb_items"] = items
                data["breadcrumb_items"] = items
                data["current_page_url"] = items[-1].get("url", base_url) if items else base_url

    st.session_state["business_data"] = data
    st.markdown("---")
    col_back2, col_gen = st.columns(2)
    with col_back2:
        if st.button("← Back"):
            st.session_state["step"] = 2
            st.rerun()
    with col_gen:
        if st.button("Generate Schemas →", type="primary", use_container_width=True):
            st.session_state["step"] = 4
            st.rerun()

# ─── Step 4: Output ──────────────────────────────────────────────────────────
elif st.session_state["step"] == 4:
    st.markdown('<div class="step-header">Step 4 — Generated Schemas</div>', unsafe_allow_html=True)
    data = st.session_state["business_data"]
    selected = st.session_state["selected_schemas"]
    client_slug = data.get("client_slug", slugify(data.get("business_name", "business")))
    btype = st.session_state.get("business_type", "Local / Service Business")

    # ── Generate all schemas ──────────────────────────────────────────────────
    schemas = {}
    all_errors = []
    all_warnings = []

    generator_map = {
        "homepage": lambda d: ("homepage", generate_homepage(d)),
        "website": lambda d: ("website", generate_website(d)),
        "about": lambda d: ("about", generate_about_page(d)),
        "contact": lambda d: ("contact", generate_contact_page(d)),
        "organization": lambda d: ("organization", generate_local_business(d) if btype == "Local / Service Business" else generate_organization(d)),
        "person": lambda d: ("person", generate_person(d, d.get("website_url", ""))),
        "service_single": lambda d: ("service", generate_service_page(d)),
        "service_multi": lambda d: ("services-multi", generate_multi_service_page(d)),
        "blog": lambda d: ("blog", generate_blog_post(d)),
        "faq": lambda d: ("faq", generate_faq(d)),
        "breadcrumb": lambda d: ("breadcrumb", generate_breadcrumb(d)),
        "product": lambda d: ("product", generate_product(d)),
        "saas_app": lambda d: ("webapp", generate_saas_app(d)),
        "saas_pricing": lambda d: ("pricing", generate_saas_pricing_page(d)),
    }

    validator_map = {
        "homepage": lambda d: validate_local_business(d) if btype == "Local / Service Business" else validate_organization(d),
        "organization": lambda d: validate_local_business(d) if btype == "Local / Service Business" else validate_organization(d),
        "about": validate_person,
        "person": validate_person,
        "service_single": validate_service,
        "blog": validate_blog_post,
        "faq": validate_faq,
        "product": validate_product,
        "saas_app": validate_saas,
        "saas_pricing": validate_saas,
    }

    for key in selected:
        if key in generator_map:
            try:
                file_key, schema = generator_map[key](data)
                schemas[file_key] = schema
            except Exception as e:
                st.error(f"Error generating **{key}**: {e}")

        if key in validator_map:
            issues = validator_map[key](data)
            errors, warnings = format_issues_for_display(issues)
            all_errors.extend([f"[{key}] {e}" for e in errors])
            all_warnings.extend([f"[{key}] {w}" for w in warnings])

    # ── Validation Summary ────────────────────────────────────────────────────
    if all_errors:
        st.markdown("### ⛔ Errors — Fix These")
        for err in all_errors:
            st.markdown(f'<div class="error-box">🔴 {err}</div>', unsafe_allow_html=True)

    if all_warnings:
        with st.expander(f"⚠️ {len(all_warnings)} Warnings (advisory — review these)", expanded=False):
            for warn in all_warnings:
                st.markdown(f'<div class="warning-box">🟡 {warn}</div>', unsafe_allow_html=True)

    if not all_errors:
        st.markdown(f'<div class="success-box">✅ {len(schemas)} schema(s) generated successfully.</div>', unsafe_allow_html=True)

    # ── Download All ──────────────────────────────────────────────────────────
    if schemas:
        zip_bytes = build_zip(schemas, client_slug)
        st.download_button(
            label=f"⬇️ Download All Schemas as ZIP ({len(schemas)} files)",
            data=zip_bytes,
            file_name=f"{client_slug}-schemas.zip",
            mime="application/zip",
            use_container_width=True,
            type="primary",
        )
        st.markdown("---")

    # ── Per-schema Display ────────────────────────────────────────────────────
    if schemas:
        tabs = st.tabs([f"{client_slug}-{k}.json" for k in schemas])
        for tab, (file_key, schema) in zip(tabs, schemas.items()):
            with tab:
                json_str = format_json(schema)
                script_wrapped = f'<script type="application/ld+json">\n{json_str}\n</script>'

                col_json, col_script = st.columns(2)
                with col_json:
                    st.markdown("**JSON-LD (raw)**")
                    st.code(json_str, language="json")
                    st.download_button(
                        label="⬇️ Download JSON",
                        data=json_str,
                        file_name=f"{client_slug}-{file_key}.json",
                        mime="application/json",
                        key=f"dl_{file_key}",
                    )
                with col_script:
                    st.markdown("**HTML (with `<script>` tag)**")
                    st.code(script_wrapped, language="html")

    st.markdown("---")
    col_back3, col_edit = st.columns(2)
    with col_back3:
        if st.button("← Back to Customize"):
            st.session_state["step"] = 3
            st.rerun()
    with col_edit:
        if st.button("Edit Business Info"):
            st.session_state["step"] = 1
            st.rerun()
