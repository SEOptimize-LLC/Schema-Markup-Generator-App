# Schema Markup Generator

A Streamlit web app for generating advanced, entity-based JSON-LD schema markup following the knowledge graph methodology. Built for SEO professionals who need production-ready structured data — not just basic templates.

---

## What It Does

Takes your business information and outputs complete, interconnected JSON-LD schemas with:

- **Wikidata & Wikipedia entity anchoring** (`knowsAbout`, `additionalType`, `sameAs`)
- **Consistent `@id` cross-referencing** across all schemas (root entity system)
- **E-E-A-T signals** via Person schema (`alumniOf`, `hasCredential`, `knowsAbout`, `worksFor`)
- **`isPartOf` chaining** — FAQPage → WebPage → WebSite → Organization
- **Knowledge graph signals** — `areaServed`, `GeoShape`, `containsPlace`, entity `mentions`
- **AI enrichment** via Claude Sonnet (OpenRouter) to auto-suggest subtypes, Wikidata IDs, and topical authority topics
- **Fact Cheat upload** — paste in a pre-verified business data document to auto-fill all fields

---

## Schema Types Supported

| Schema | Description |
| --- | --- |
| Homepage | WebPage + WebSite + Organization + Person (nested) |
| WebSite | Standalone with optional SearchAction |
| About Page | AboutPage with Person as `mainEntity` (full E-E-A-T) |
| Contact Page | ContactPage with address and contact points |
| Organization | Root entity with all advanced properties |
| Person | Founder/author with `knowsAbout`, `alumniOf`, `sameAs` |
| Service Page | Single service with `hasOfferCatalog`, `areaServed` |
| Services Page | Multi-service with OfferCatalog + nested Offers |
| Blog Post | BlogPosting with author, publisher, `mentions` entities |
| FAQ Page | FAQPage with `isPartOf` WebPage and entity `mentions` |
| BreadcrumbList | Page trail with ListItem positions |
| Product | Product with Offer, AggregateRating, Merchant Center |
| WebApplication | SaaS product schema |
| Pricing Page | AggregateOffer + UnitPriceSpecification per tier |

---

## Getting Started

### Prerequisites

- Python 3.10+
- An [OpenRouter](https://openrouter.ai) API key (free tier available)

### Local Setup

```bash
git clone https://github.com/SEOptimize-LLC/Schema-Markup-Generator-App.git
cd Schema-Markup-Generator-App
pip install -r requirements.txt
```

Create `.streamlit/secrets.toml`:

```toml
OPENROUTER_API_KEY = "your-openrouter-api-key"
MODEL = "anthropic/claude-sonnet-4-5"
```

Run the app:

```bash
streamlit run app.py
```

---

## Deployment (Streamlit Cloud)

1. Fork or push this repo to your GitHub account
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Select this repo, set main file to `app.py`
4. Under **Advanced settings → Secrets**, add:

```toml
OPENROUTER_API_KEY = "your-openrouter-api-key"
MODEL = "anthropic/claude-sonnet-4-5"
```

5. Deploy — no server setup required

---

## How to Use

### Step 1 — Business Info

- Enter business name and website URL
- *(Optional)* Upload a Fact Cheat `.txt` or `.md` file to auto-fill all fields from verified data
- Click **Enrich with AI** to auto-suggest schema subtype, Wikidata IDs, `knowsAbout` topics, and `sameAs` profiles
- Fill in address, contact details, media URLs, social profiles, and service list

### Step 2 — Select Schemas

- Choose which page schemas to generate (pre-selected based on business type)
- Supports: Local/Service Business, E-commerce, SaaS/Software

### Step 3 — Customize

- Review and edit each schema's specific fields in tabbed view
- Add FAQ questions, service sub-items, pricing tiers, breadcrumb items, etc.

### Step 4 — Output

- View generated JSON-LD and HTML (`<script>` tag) side by side
- Download individual `.json` files or all as a `.zip`
- Validation panel highlights missing required fields (errors) and advisory improvements (warnings)

---

## Output File Naming

Files are named using the client slug set in Step 1:

```text
acme-plumbing-homepage.json
acme-plumbing-about.json
acme-plumbing-service.json
acme-plumbing-faq.json
acme-plumbing-schemas.zip
```

---

## Project Structure

```text
├── app.py                        # Main Streamlit UI
├── requirements.txt
├── .env.example
├── .streamlit/
│   ├── config.toml               # Theme config
│   └── secrets.toml.example      # Secrets template
└── src/
    ├── ai/
    │   └── enrichment.py         # OpenRouter/Claude API calls
    ├── generators/
    │   ├── base.py               # Shared builders (@id, address, hours)
    │   ├── organization.py       # Organization + LocalBusiness
    │   ├── person.py             # Person (E-E-A-T)
    │   ├── website.py            # WebSite + WebPage types
    │   ├── service.py            # Service + OfferCatalog
    │   ├── blog.py               # BlogPosting + Article
    │   ├── faq.py                # FAQPage
    │   ├── product.py            # Product + Merchant Center
    │   ├── saas.py               # WebApplication + AggregateOffer
    │   └── breadcrumb.py         # BreadcrumbList
    ├── validators/
    │   └── schema_validator.py   # Required field checks + warnings
    └── utils/
        └── helpers.py            # JSON formatting, ZIP builder, URL helpers
```

---

## Environment Variables

| Variable | Description |
| --- | --- |
| `OPENROUTER_API_KEY` | Your OpenRouter API key |
| `MODEL` | Model to use (default: `anthropic/claude-sonnet-4-5`) |

---

## Dependencies

```text
streamlit>=1.32.0
openai>=1.12.0
```

The OpenAI Python SDK is used as an OpenRouter-compatible client — no direct OpenAI account needed.

---

## License

MIT
