# StaleAnswer AI

StaleAnswer AI identifies claims in AI-generated answers, checks them against live web research, and explains whether the evidence is current. The Streamlit interface uses a black, earthy design system: forest green actions, warm beige typography, terracotta warnings, and slate-neutral surfaces.

## Problem statement coverage

This prototype implements the attached Stale-Answer Detector brief:

- Claim identification: extracts independent, deduplicated factual claims from an LLM-generated answer.
- Freshness detection: flags claims as potentially outdated, conflicting, verified, or unable to verify.
- Live verification: researches every claim with Tavily and evaluates the returned evidence through Bifrost by Maxim AI.
- Freshness scoring: gives every claim a transparent score and rolls those scores into an overall answer freshness score.
- Usable prototype flow: includes progress feedback, a persistent report view, recent-check history in the sidebar, source links, and PDF export.

The optional guidance in the brief is treated as product direction rather than hard-coded domain assumptions: the same workflow can check pricing, API documentation, regulations, leadership, announcements, and other time-sensitive claims.

## Authentication and request flow

Credentials are loaded from the process environment via `python-dotenv`; they are never hard-coded or sent to the browser.

```text
Streamlit UI
  ├─ claim_extractor.py ── OpenAI SDK ── Bifrost ── configured model
  ├─ web_research.py ──── TavilyClient ── Tavily Search API
  └─ answer_verifier.py ─ OpenAI SDK ── Bifrost ── configured model
```

1. The user submits an answer in `app.py`.
2. `claim_extractor.py` creates a Bifrost client and sends the answer to the configured model. The client uses `BIFROST_API_KEY` as the OpenAI-compatible API key and sends the virtual key in the `x-bf-vk` header.
3. `web_research.py` creates `TavilyClient(api_key=TAVILY_API_KEY)` and performs a live search for each extracted claim. Only valid HTTP(S) source URLs are retained.
4. `answer_verifier.py` sends each claim plus the returned source evidence through the same Bifrost client. The model must return one of four statuses; malformed or unsupported responses fall back safely to `Unable to verify`.
5. `pdf_generator.py` builds a local report from the results. API credentials are not included in the report.

The Bifrost wrapper normalizes `BIFROST_BASE_URL` to an OpenAI-compatible `/v1` or `/openai` endpoint, sets a 60-second timeout, disables SDK retries so the app's bounded 3-attempt retry policy controls behavior, and validates required configuration before any request. Keys and tokens live only in environment variables and request headers; this repository intentionally contains no credential storage, browser local storage, cookies, or persistent token cache.

## Configuration

Create a local `.env` file (ignored by Git):

```env
TAVILY_API_KEY=your_tavily_api_key
BIFROST_VIRTUAL_KEY=your_bifrost_virtual_key
BIFROST_API_KEY=your_bifrost_api_key
BIFROST_BASE_URL=http://localhost:8080
BIFROST_MODEL_NAME=gemini/gemini-3.6-flash
```

`BIFROST_VIRTUAL_KEY` may fall back to `BIFROST_API_KEY` for local setups. Never commit `.env` or expose these values in client-side code.

## Run locally

```bash
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
npx -y @maximhq/bifrost
streamlit run app.py
```

Run tests with `python -m pytest -q` when the test suite is present.

