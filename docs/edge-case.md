# Edge Cases & Corner Scenarios

> AI-Powered Restaurant Recommendation System  
> Companion to [context.md](./context.md), [architecture.md](./architecture.md), and [implementation-plan.md](./implementation-plan.md)

This document catalogs edge cases, boundary conditions, failure modes, and corner scenarios across every layer of the system. Use it for test design, error handling, and QA.

---

## How to Read This Document

| Column | Meaning |
|--------|---------|
| **ID** | Unique reference for tests and issues |
| **Severity** | `Critical` — breaks core flow; `High` — bad UX or wrong results; `Medium` — degraded experience; `Low` — cosmetic or rare |
| **Expected behavior** | What the system should do (not what it must never do unless stated) |

---

## 1. Data Ingestion & Preprocessing

### 1.1 Dataset loading

| ID | Scenario | Example | Expected behavior | Severity |
|----|----------|---------|-------------------|----------|
| D-01 | Hugging Face unreachable | Network offline on first load | Fail startup with clear error; log root cause; do not serve requests | Critical |
| D-02 | Dataset renamed or removed on HF | 404 from HF hub | Fail startup; message points to `HF_DATASET` config | Critical |
| D-03 | Slow HF download | First load takes >60s | Show loading indicator (UI) or block until ready; log progress | Medium |
| D-04 | Partial/corrupt cached dataset | Truncated local cache file | Detect invalid cache; re-download or fail with actionable message | High |
| D-05 | Empty dataset returned | 0 rows after load | Fail startup; refuse to serve | Critical |
| D-06 | Schema change on HF | Column names differ from expected | Log mapping failure; fail startup or map with fallback column detection | High |
| D-07 | Duplicate HF load on restart | App restarted twice quickly | Use cache; do not re-fetch unless cache invalid | Low |

### 1.2 Missing or malformed field values

| ID | Scenario | Example | Expected behavior | Severity |
|----|----------|---------|-------------------|----------|
| D-08 | Missing restaurant name | `name` is null/empty | Drop row; increment dropped-row counter in logs | High |
| D-09 | Missing location | `location` is null/empty | Drop row | High |
| D-10 | Missing cuisine | `cuisine` is null/empty | Drop row or assign `"unknown"` and exclude from cuisine filter | High |
| D-11 | Missing rating | `rating` is null | Drop row or default to 0 (document choice; prefer drop) | Medium |
| D-12 | Missing cost | `cost` is null/empty | Drop row or assign `budget_tier: unknown` and exclude from budget filter | Medium |
| D-13 | Non-numeric rating | `"NEW"`, `"-"`, `"4.5/5"` | Parse if possible; otherwise drop row | Medium |
| D-14 | Rating out of range | `-1`, `6.0`, `99` | Clamp to 0–5 or drop if clearly invalid | Medium |
| D-15 | Rating exactly 0 | `0.0` | Keep row; valid for filtering with `min_rating: 0` | Low |
| D-16 | Cost as free text | `"₹300"`, `"300-500"`, `"Moderate"` | Normalize to display string + budget tier via parsing rules | Medium |
| D-17 | Cost unparseable | `"N/A"`, `"--"` | Set `budget_tier: unknown`; exclude from strict budget filter | Medium |
| D-18 | Multi-cuisine string | `"North Indian, Chinese, Mughlai"` | Split, lowercase, dedupe → `list[str]` | Medium |
| D-19 | Duplicate restaurants | Same name + location twice | Dedupe; keep highest-rated or first occurrence; log count | Medium |
| D-20 | Very long restaurant name | 200+ characters | Trim for display; keep full name in storage | Low |
| D-21 | Special characters in name | `"Café No. 5"`, `"Tom's Diner"` | Preserve UTF-8; do not strip accents/apostrophes | Low |

### 1.3 Location & cuisine normalization

| ID | Scenario | Example | Expected behavior | Severity |
|----|----------|---------|-------------------|----------|
| D-22 | Location alias | User/dataset: `"Bengaluru"` vs `"Bangalore"` | Normalize to canonical key (`bangalore`) | High |
| D-23 | Location casing | `"DELHI"`, `" delhi "` | Lowercase + trim before indexing | Medium |
| D-24 | Location with area suffix | `"Delhi NCR"`, `"Bangalore North"` | Map to nearest city or keep granular; document mapping | Medium |
| D-25 | City not in dataset | `"Mumbai"` when dataset has no Mumbai rows | Location unavailable in dropdown; API returns 400 if forced | High |
| D-26 | Cuisine substring overlap | Filter `"Indian"` matches `"North Indian"` | Define match rule (contains vs exact); be consistent | High |
| D-27 | Cuisine typo in dataset | `"Itallian"` | Fuzzy match or manual alias map | Medium |
| D-28 | Single restaurant in city | Only 1 row for `"Delhi"` | Still queryable; may return <5 recommendations | Medium |

### 1.4 Budget tier mapping

| ID | Scenario | Example | Expected behavior | Severity |
|----|----------|---------|-------------------|----------|
| D-29 | All restaurants same cost band | Flat cost distribution | All map to one tier; budget filter may be meaningless | Medium |
| D-30 | Cost at tier boundary | ₹600 when threshold is 600 | Document inclusive/exclusive rule; apply consistently | Medium |
| D-31 | Extreme outliers | ₹50 vs ₹10,000 | Cap or use percentiles; avoid all rows in `high` | Medium |
| D-32 | User budget `low`, all candidates `high` | Strict filter | Zero results → trigger filter relaxation | High |

---

## 2. User Input & Preferences

### 2.1 Required fields

| ID | Scenario | Example | Expected behavior | Severity |
|----|----------|---------|-------------------|----------|
| U-01 | Missing `location` | `{}` or `{ "budget": "low" }` | `400` — validation error: location required | Critical |
| U-02 | Missing `budget` | No budget field | `400` — validation error: budget required | Critical |
| U-03 | Missing `cuisine` | No cuisine field | `400` — validation error: cuisine required | Critical |
| U-04 | Empty string location | `{ "location": "" }` | Treat as missing → `400` | High |
| U-05 | Whitespace-only fields | `{ "location": "   " }` | Treat as missing → `400` | Medium |

### 2.2 Invalid enum / type values

| ID | Scenario | Example | Expected behavior | Severity |
|----|----------|---------|-------------------|----------|
| U-06 | Invalid budget enum | `"cheap"`, `"MEDIUM"`, `123` | `400` — must be `low` \| `medium` \| `high` | High |
| U-07 | Budget wrong case | `"Medium"` | Normalize to lowercase or reject with hint | Medium |
| U-08 | Unknown location | `"Paris"` | `400` — location not in dataset; suggest valid cities | High |
| U-09 | Unknown cuisine | `"Mexican"` when not in dataset | `400` or fuzzy-suggest closest match | High |
| U-10 | `min_rating` as string | `"4.5"` | Coerce to float if valid; else `400` | Medium |
| U-11 | `min_rating` negative | `-1` | `400` — must be 0–5 | Medium |
| U-12 | `min_rating` above 5 | `5.5`, `10` | `400` or clamp to 5 with warning | Medium |
| U-13 | `min_rating` omitted | Not sent | Default to `0.0` | Low |
| U-14 | `min_rating` exactly 5 | `5.0` | Valid; may return very few or zero results | Medium |
| U-15 | Extra unknown JSON fields | `{ "location": "Delhi", "foo": "bar" }` | Ignore extras (Pydantic default) or reject — document choice | Low |

### 2.3 Additional preferences (free text)

| ID | Scenario | Example | Expected behavior | Severity |
|----|----------|---------|-------------------|----------|
| U-16 | Empty additional preferences | `""` or omitted | Skip in prompt or pass as "none" | Low |
| U-17 | Very long text | 5,000 characters | Truncate to max length (e.g., 500); log truncation | High |
| U-18 | Prompt injection attempt | `"Ignore previous instructions..."` | Sanitize; pass as user preference only; system prompt unchanged | Critical |
| U-19 | Control characters | `\n`, `\t`, null bytes | Strip control chars before prompt | High |
| U-20 | Non-English preferences | Hindi/regional language text | Pass to Groq as-is; LLM should still respond in English (per prompt) | Medium |
| U-21 | Emoji in preferences | `"🍕 pizza, kid friendly 🧒"` | Allow; sanitize only dangerous chars | Low |
| U-22 | Conflicting preferences | `"cheap" in text but budget is high` | LLM may reconcile; structured budget filter takes precedence | Medium |
| U-23 | Preferences irrelevant to dataset | `"vegan, halal, rooftop"` | LLM interprets semantically; no hard filter unless data supports it | Medium |

### 2.4 Input encoding & API format

| ID | Scenario | Example | Expected behavior | Severity |
|----|----------|---------|-------------------|----------|
| U-24 | Invalid JSON body | `{ location: Delhi }` | `422` Unprocessable Entity | High |
| U-25 | Wrong Content-Type | `text/plain` body | `415` or `422` with clear message | Medium |
| U-26 | UTF-8 location/cuisine | `"Delhi"`, `"Mughlai"` | Accept UTF-8 throughout | Low |
| U-27 | SQL injection in text fields | `"'; DROP TABLE--"` | No DB in MVP; sanitize for prompt only | Low |

---

## 3. Filtering & Candidate Selection

### 3.1 Zero or sparse results

| ID | Scenario | Example | Expected behavior | Severity |
|----|----------|---------|-------------------|----------|
| F-01 | No match on all filters | Delhi + Italian + high + min 4.8 | Relax filters: cuisine → min_rating → budget (in order) | Critical |
| F-02 | Still zero after full relaxation | Niche combo in sparse city | `404` — no restaurants found; suggest broadening search | Critical |
| F-03 | Exactly 1 candidate | Only one Italian in Delhi | Send 1 to Groq; return 1 recommendation (not 5) | High |
| F-04 | Exactly 2 candidates | Two matches | Return up to 2 recommendations | High |
| F-05 | Fewer than `TOP_RECOMMENDATIONS` (5) | 3 candidates | Return 3, not pad with fake entries | High |
| F-06 | More than `MAX_CANDIDATES` (20) | 200 matches | Take top 20 by rating before LLM | High |
| F-07 | All candidates same rating | Tie at 4.2 | Stable secondary sort (name asc or id) | Medium |
| F-08 | Relaxation drops user-critical constraint | User wants Italian; relaxed removes cuisine | Include `metadata.filters_relaxed` so UI can warn user | High |

### 3.2 Filter boundary conditions

| ID | Scenario | Example | Expected behavior | Severity |
|----|----------|---------|-------------------|----------|
| F-09 | `min_rating` filters all rows | min 5.0 in city with max 4.9 | Relax min_rating or return 404 with explanation | High |
| F-10 | Budget filter too strict | `low` budget, all restaurants `medium+` | Relax budget tier or return 404 | High |
| F-11 | Cuisine partial match | User: `"Chinese"`, row: `"Indo Chinese"` | Match via contains/substring rule | Medium |
| F-12 | Multi-cuisine restaurant | Row cuisines: `["Italian", "Pizza"]`, user: `"Pizza"` | Match if any cuisine matches | Medium |
| F-13 | Case-insensitive cuisine filter | User: `"italian"` | Match regardless of case | Medium |
| F-14 | Location filter with alias | User selects Bangalore, row stored as bengaluru | Match after normalization | High |

### 3.3 Context builder

| ID | Scenario | Example | Expected behavior | Severity |
|----|----------|---------|-------------------|----------|
| F-15 | Candidate JSON exceeds token limit | 20 large rows + long names | Truncate fields or reduce `MAX_CANDIDATES` | High |
| F-16 | Special chars in candidate JSON | Names with quotes, backslashes | Proper JSON escaping in prompt payload | Medium |
| F-17 | Null optional fields in candidate | Missing estimated_cost | Omit or send `"unknown"`; do not crash serializer | Medium |
| F-18 | Duplicate IDs in candidate pool | Bug introduces dupes | Dedupe before prompt; log warning | High |

---

## 4. Groq / LLM Recommendation Engine

### 4.1 API & connectivity failures

| ID | Scenario | Example | Expected behavior | Severity |
|----|----------|---------|-------------------|----------|
| L-01 | Missing `GROQ_API_KEY` | Env var not set | Fail at startup or first request with clear setup message | Critical |
| L-02 | Invalid API key | `401` from Groq | Log error; use `FallbackRanker`; return `502` or degraded flag | Critical |
| L-03 | Groq rate limit | `429 Too Many Requests` | Retry with backoff (1–2 retries); then fallback | High |
| L-04 | Groq service outage | `503` / timeout | `FallbackRanker`; `502` with `used_fallback: true` in metadata | Critical |
| L-05 | Request timeout (>30s) | Slow Groq response | Abort; fallback ranker; log latency | High |
| L-06 | Network interruption mid-request | Connection reset | Catch exception; fallback; no partial/corrupt response to user | High |
| L-07 | Model deprecated/unavailable | `404` on model name | Log; try fallback model or fail with config hint | High |

### 4.2 Malformed or unexpected LLM output

| ID | Scenario | Example | Expected behavior | Severity |
|----|----------|---------|-------------------|----------|
| L-08 | Non-JSON response | Prose instead of JSON | Retry once with stricter prompt; then fallback | Critical |
| L-09 | JSON with markdown fences | ` ```json {...} ``` ` | Strip fences before parse | High |
| L-10 | Partial JSON | Truncated mid-object | Retry; then fallback | High |
| L-11 | Missing `recommendations` key | `{ "summary": "..." }` | Fallback or partial response with error flag | High |
| L-12 | Empty `recommendations` array | `[]` | Fallback ranker | High |
| L-13 | Fewer than 5 recommendations | LLM returns 2 | Accept 2 if valid; do not invent extras | Medium |
| L-14 | More than 5 recommendations | LLM returns 10 | Take top 5 by rank | Medium |
| L-15 | Duplicate ranks | Two items with `rank: 1` | Re-rank sequentially; log warning | Medium |
| L-16 | Missing rank field | No `rank` on items | Assign ranks 1..N by array order | Medium |
| L-17 | Invalid `restaurant_id` | ID not in candidate pool | Drop invalid entries; backfill from fallback if needed | Critical |
| L-18 | Hallucinated restaurant | Name not in candidates | Reject entry; validate ID + name against pool | Critical |
| L-19 | Wrong rating in LLM output | LLM says 4.8, dataset has 4.2 | Prefer dataset values for structured fields; LLM for explanation only | High |
| L-20 | Wrong cost in LLM output | LLM invents price | Overwrite with dataset `estimated_cost` after parse | High |
| L-21 | Empty explanation | `explanation: ""` | Use template fallback explanation | Medium |
| L-22 | Very long explanation | 2,000 words | Truncate for UI display (e.g., 500 chars) | Low |
| L-23 | Missing summary | No `summary` field | Omit summary section in UI; still show cards | Low |

### 4.3 Prompt & token edge cases

| ID | Scenario | Example | Expected behavior | Severity |
|----|----------|---------|-------------------|----------|
| L-24 | Token limit exceeded | Too many/large candidates | Reduce candidates or shorten prompt; retry | High |
| L-25 | Single candidate in prompt | 1 restaurant | LLM should still rank 1 and explain | Medium |
| L-26 | Identical candidates (dedup bug) | Same ID twice in prompt | Dedupe before send | Medium |
| L-27 | Temperature too high | Config typo `temperature: 1.5` | Clamp to valid range or use default 0.3 | Low |
| L-28 | `response_format: json_object` unsupported | Model rejects param | Omit param; rely on prompt + parser | Medium |

### 4.4 Fallback ranker

| ID | Scenario | Example | Expected behavior | Severity |
|----|----------|---------|-------------------|----------|
| L-29 | Fallback with 0 candidates | Should not reach engine | Handled upstream as F-02 (`404`) | Critical |
| L-30 | Fallback produces generic explanations | Groq down | Template: "Rated X with {cuisine} cuisine in {location}, matching your {budget} budget." | Medium |
| L-31 | Fallback sort ties | Same rating and budget match | Stable sort by name or id | Low |
| L-32 | User not informed of fallback | Groq failed silently | Set `metadata.used_fallback: true`; UI shows subtle notice | High |

---

## 5. Output Display & API Response

### 5.1 Response shaping

| ID | Scenario | Example | Expected behavior | Severity |
|----|----------|---------|-------------------|----------|
| O-01 | Null summary with valid recommendations | summary is null | Render cards only | Low |
| O-02 | Missing optional metadata | No `filters_applied` | Omit or default to empty list | Low |
| O-03 | Rating display precision | `4.333333` | Display as `4.3` (1 decimal) | Low |
| O-04 | Zero rating restaurant | `0.0` | Display `0.0` or "Unrated"; do not hide | Medium |
| O-05 | Unknown estimated cost | `"unknown"` | Display "Price not available" | Medium |
| O-06 | Very long restaurant name in card | 100+ chars | Truncate with ellipsis in UI | Low |

### 5.2 HTTP status codes

| ID | Scenario | HTTP | Body |
|----|----------|------|------|
| O-07 | Valid request, Groq success | `200` | Full recommendations + summary |
| O-08 | Valid request, Groq failed, fallback ok | `200` or `502` | Document choice; include `used_fallback: true` |
| O-09 | Invalid preferences | `400` | `{ "error": "...", "field": "location" }` |
| O-10 | No restaurants after relaxation | `404` | `{ "error": "No restaurants match your criteria" }` |
| O-11 | Unhandled exception | `500` | Generic message; no stack trace to client |
| O-12 | Dataset not loaded | `503` | `{ "error": "Service starting up" }` |

### 5.3 Streamlit / UI-specific

| ID | Scenario | Example | Expected behavior | Severity |
|----|----------|---------|-------------------|----------|
| O-13 | Double-click submit | User clicks Recommend twice | Debounce or disable button during loading | Medium |
| O-14 | Submit with default empty dropdown | No location selected | Inline validation; block submit | High |
| O-15 | Long Groq wait | 5–15s response | Show spinner/skeleton; no blank screen | Medium |
| O-16 | Error from API | 404/502 | User-friendly message; no raw JSON dump | High |
| O-17 | Session refresh mid-request | Browser reload | Lose in-flight request gracefully | Low |
| O-18 | Narrow viewport / mobile | Small screen | Cards stack; text remains readable | Low |
| O-19 | Unicode in results | `"Naïve Kitchen"` | Render correctly in Streamlit | Low |

---

## 6. Startup, Runtime & Configuration

| ID | Scenario | Example | Expected behavior | Severity |
|----|----------|---------|-------------------|----------|
| R-01 | App starts before dataset ready | Health check during load | `GET /health` → `{ "ready": false }` | High |
| R-02 | Invalid `MAX_CANDIDATES` | `0` or `-5` | Reject at config load or default to 20 | Medium |
| R-03 | Invalid `TOP_RECOMMENDATIONS` | `0` or `100` | Clamp to 1–10 or default to 5 | Medium |
| R-04 | `TOP_RECOMMENDATIONS` > candidates | Ask for 5, have 2 | Return 2 | Medium |
| R-05 | `MAX_CANDIDATES` < `TOP_RECOMMENDATIONS` | max 3, top 5 | Document precedence; cap recommendations at candidate count | Medium |
| R-06 | Missing `.env` file | No local env | Use defaults where safe; fail on missing `GROQ_API_KEY` at LLM call | High |
| R-07 | Wrong Python version | Python 3.8 | Document 3.11+ requirement in README | Medium |
| R-08 | Missing dependency | `groq` not installed | Import error at startup with install hint | High |
| R-09 | Out of memory on load | Huge dataset | Unlikely for Zomato subset; log OOM clearly | Low |

---

## 7. Security & Abuse

| ID | Scenario | Example | Expected behavior | Severity |
|----|----------|---------|-------------------|----------|
| S-01 | Prompt injection via additional_preferences | Jailbreak text | Sanitize; isolate in user block; never execute as instructions | Critical |
| S-02 | API key in client-side code | Streamlit exposes key | Key server-side only; never in browser bundle | Critical |
| S-03 | `.env` committed to git | Accidental push | `.gitignore`; rotate key if leaked | Critical |
| S-04 | High request volume | Scripted spam to `/recommend` | Rate limit if deployed publicly | High |
| S-05 | Oversized request body | 10 MB JSON | Reject at 1 MB or similar limit | Medium |
| S-06 | Log leakage of prompts | Full prompt in production logs | Redact or log summary only in prod | Medium |
| S-07 | LLM returns unsafe content | Offensive explanation | Optional content filter; truncate and flag | Medium |

---

## 8. Concurrency & Performance

| ID | Scenario | Example | Expected behavior | Severity |
|----|----------|---------|-------------------|----------|
| P-01 | Concurrent API requests | 10 simultaneous `/recommend` | Each request independent; no shared mutable state | High |
| P-02 | Groq rate limit under load | Burst of 50 requests | Queue or return 429/fallback; do not crash | High |
| P-03 | Cold start latency | First request after boot | Dataset already loaded at startup; first Groq call may be slower | Medium |
| P-04 | Repeated identical queries | Same prefs submitted 10 times | Correct results each time; optional caching out of scope for MVP | Low |
| P-05 | Streamlit rerun loop | Widget change triggers rerun | Do not auto-submit recommendation on every widget change | Medium |

---

## 9. Data–LLM Consistency

These scenarios guard against the core failure mode: **structured filters say one thing, LLM says another**.

| ID | Scenario | Risk | Mitigation |
|----|----------|------|------------|
| C-01 | LLM recommends restaurant outside candidate pool | Hallucination | Validate every `restaurant_id` against candidates |
| C-02 | LLM ignores budget preference | Wrong explanations | Structured budget filter is authoritative; prompt reinforces |
| C-03 | LLM ranks lower-rated above higher-rated | Bad UX | Accept LLM rank for explanation quality; optional re-sort by rating in fallback |
| C-04 | LLM mentions "family-friendly" with no data | False claim | Prompt: only claim attributes supported by data or user prefs |
| C-05 | Filter relaxed but summary says "exact match" | Misleading | Pass relaxation metadata to prompt; instruct honest summary |
| C-06 | Dataset rating stale vs user expectation | Trust | Display dataset rating as source of truth |

---

## 10. End-to-End Scenario Matrix

Representative combinations for manual QA:

| # | Location | Budget | Cuisine | Min rating | Additional | Expected outcome |
|---|----------|--------|---------|------------|------------|------------------|
| E2E-01 | Delhi | medium | Italian | 4.0 | family-friendly | 5 (or fewer) Italian results with explanations |
| E2E-02 | Bangalore | low | Chinese | 0 | — | Results within low budget tier |
| E2E-03 | Valid city | high | rare cuisine | 4.5 | — | Relaxation or 404 with message |
| E2E-04 | Delhi | medium | Italian | 5.0 | — | Very few results; relaxation likely |
| E2E-05 | Valid city | medium | valid | 3.0 | 500-char preferences | Truncated prefs; still returns results |
| E2E-06 | Valid city | medium | valid | 3.0 | — | Groq disabled → fallback rankings |
| E2E-07 | Invalid location | medium | Italian | 3.0 | — | 400 validation error |
| E2E-08 | Valid city | invalid | Italian | 3.0 | — | 400 budget enum error |
| E2E-09 | Sparse city | low | any | 0 | — | 1–3 results, no padding |
| E2E-10 | Valid city | medium | valid | 3.0 | prompt injection string | Sanitized; no system compromise |

---

## 11. Recommended Test Cases (pytest mapping)

| Test file | Edge case IDs to cover |
|-----------|------------------------|
| `test_preprocessor.py` | D-08–D-21, D-22–D-27 |
| `test_repository.py` | D-05, D-19, D-28, F-14 |
| `test_preferences.py` | U-01–U-15, U-24–U-26 |
| `test_filter.py` | F-01–F-14, F-18, D-32 |
| `test_parser.py` | L-08–L-17, L-19–L-21 |
| `test_fallback.py` | L-29–L-31, L-04–L-06 |
| `test_groq_integration.py` | E2E-01, E2E-06 (live API) |
| `test_api.py` | O-07–O-12, U-01, F-02 |

---

## 12. Priority Fix Order

If implementing handlers incrementally, address in this order:

1. **Critical path** — D-01, D-05, F-01, F-02, L-01, L-04, L-08, L-17, L-18, S-01, S-02  
2. **Correctness** — L-19, L-20, F-08, C-01–C-05, U-08, U-09  
3. **UX** — L-32, O-14, O-15, O-16, F-05, F-03  
4. **Polish** — Remaining Low/Medium items  

---

## Related Documents

- [context.md](./context.md) — Success criteria and workflow
- [architecture.md](./architecture.md) — Error codes, filter relaxation, Groq config
- [implementation-plan.md](./implementation-plan.md) — Phase-wise build and acceptance criteria

---

*Last updated: generated from project context and architecture*
