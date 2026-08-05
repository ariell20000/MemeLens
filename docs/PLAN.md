# MemeLens — Implementation Plan

## Context

This plan turns a brainstorming conversation (started with Gemini, refined here) into a concrete build plan for the user's second portfolio project, targeting junior backend/cyber roles. The repo (`C:\Users\ariel\Desktop\MemeLens`) is currently empty — greenfield build.

**The problem the project solves:** existing meme tools only support keyword search, not situational/semantic search ("a meme for when someone whines about something trivial while others suffer more"). This space isn't literally unclaimed (Supermeme.ai already does AI-based meme search), and that's fine — the goal isn't novelty, it's demonstrating engineering ability across a genuinely new set of technologies this time, building on the user's first project, `slack-kudos-bot` (FastAPI, Pydantic, JWT/HMAC auth, SQL optimization, Docker, GitHub Actions).

**Guiding constraints, decided during planning:**
- Maximize learning that's broadly relevant to junior backend/cyber jobs; avoid narrow/niche detours.
- **Deliberately diversify tech stack vs. `slack-kudos-bot`**, rather than repeating the same patterns: this project adds a React + TypeScript frontend and AWS cloud experience on top of the Postgres/FastAPI/Docker foundation already proven.
- $0 budget, with an explicitly accepted exception: AWS S3's free tier (5GB) is time-limited to 12 months, not indefinite. Accepted knowingly because storage cost past that point is negligible (~$0.05/month for this dataset size) — flag it in the README rather than avoid AWS over it. Lambda's free tier (1M requests + 400,000 GB-seconds/month), by contrast, has no expiry.
- Originally scoped at ~3 weeks; **not a hard deadline.** The user is building this with AI pair-programming (Claude Code/Cursor/gh cli), reviewing and understanding every suggested change rather than accepting it blindly — the same discipline used on `slack-kudos-bot`. The week-based structure below is pacing, not a wall.
- **Vector search: pgvector (Postgres extension)** on Neon's free tier, not a dedicated vector DB — reuses/deepens the user's strongest existing skill (SQL/Postgres) while still costing $0 indefinitely.
- **Scope: lean v1.** Static images only — no GIFs, stickers, video, OCR, or a separate hybrid manual-tagging subsystem. These go in a "Future Work" README section, not attempted. Search works in **English and Hebrew** via one multilingual embedding model, not a translation/OCR pipeline.
- **Live deployment is in scope** — a real URL is the strongest "a recruiter actually looked" signal.
- **AI-delegation split, decided explicitly:** for subjects genuinely new to the user (AWS: Lambda/S3/IAM; React + TypeScript; pgvector/embedding-specific query and indexing logic), **hand-write more** and use Claude Code as an explainer/reviewer rather than primary author — the goal is to actually absorb unfamiliar territory, not just approve a diff. For subjects already proven in `slack-kudos-bot` (FastAPI app structure, JWT auth pattern, Docker/Compose basics, CI YAML boilerplate, SQLAlchemy/Alembic scaffolding), **let Claude Code draft more** and spend the saved time on deep review, questioning, and iteration — this is deliberate practice at the professional AI-assisted workflow itself, which is its own hireable skill.

## 1. System Architecture

- **Backend: FastAPI app, packaged for AWS Lambda via [Mangum](https://mangum.io/)** (an ASGI adapter that lets a normal FastAPI app run inside a Lambda handler unchanged). Deployed as a **Lambda container image** (base: `public.ecr.aws/lambda/python:3.12`), since the ML dependencies (`torch`, `transformers`, `sentence-transformers`) exceed Lambda's non-container package size limits but fit comfortably under the container image limit (10GB). Exposed publicly via a **Lambda Function URL** — chosen over API Gateway specifically because Function URLs have no additional charge beyond standard (always-free-tier) Lambda pricing, while API Gateway's free tier is 12-months-only. This keeps the whole backend genuinely free indefinitely, not just for a year.
- **Frontend: React + TypeScript**, built as static assets and deployed to **Vercel's free tier** (zero-config for a Vite/CRA React build, HTTPS out of the box, one-command deploys). Kept as a separate hosting target from the AWS backend deliberately — this is the same real-world pattern most companies actually use (backend on a cloud provider, frontend on a specialized static host), and avoids adding CloudFront/ACM-certificate complexity on top of an already-expanding AWS surface area (Lambda + S3 + IAM already provide the AWS learning goal). Styled with **Tailwind CSS**.
- **Postgres + pgvector**, hosted on **Neon's free tier** (0.5GB storage, 100 CU-hours/month, no forced pause on inactivity — unlike Supabase). Cloud-vendor-agnostic, unaffected by the AWS/GCP decision.
- **Image storage: AWS S3.** Free tier (5GB) covers the ~2GB image set for its first 12 months; storage cost afterward is negligible (a few cents/month) even unfree — call this out plainly in the README rather than treat it as a real cost risk.
- **IAM**: a least-privilege role for the Lambda function, scoped to read/write only the project's specific S3 bucket/prefix — deliberately hand-write this policy (don't accept a wildcard `s3:*`-style default from a quick AI draft) since "I understand least-privilege IAM" is a concrete, checkable interview point.

```
                     ┌──────────────────────────┐
  User browser -->   │  React + TS (Vercel)      │
                     │  - search page             │
                     └───────────┬────────────────┘
                                 │ fetch() (CORS)
                                 v
                     ┌──────────────────────────┐
                     │ FastAPI + Mangum          │
                     │ (Lambda container image,  │
                     │  Function URL)            │
                     │  - GET /api/search         │
                     │  - POST /api/memes (admin) │
                     │  - GET /healthz             │
                     │  - multilingual CLIP model  │
                     │    (loaded at cold start,   │
                     │     reused warm)            │
                     └─────┬──────────────┬───────┘
                           │              │
                 SQLAlchemy/psycopg   boto3 (S3, via IAM role)
                           │              │
                           v              v
               ┌────────────────┐  ┌──────────────┐
               │ Neon Postgres   │  │   AWS S3      │
               │ + pgvector      │  │ (meme images) │
               └────────────────┘  └──────────────┘
```

**Concept worth understanding deliberately (Lambda execution context reuse):** the CLIP model is loaded once at module scope, outside the request handler. On a *cold* invocation, Lambda spins up a fresh execution environment and pays the full model-load cost (a few seconds); on a *warm* invocation, Lambda reuses the same environment and the already-loaded model, so only cold starts are slow. This is a real, specific Lambda concept worth being able to explain in an interview, not just something to let Claude Code silently handle.

## 2. Data Model

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE memes (
    id              BIGSERIAL PRIMARY KEY,
    image_key       TEXT NOT NULL UNIQUE,        -- S3 object key
    image_url       TEXT NOT NULL,                -- public/CloudFront-free S3 URL
    source          TEXT NOT NULL,                -- 'kaggle_meme_generator' | 'manual'
    language        TEXT NOT NULL DEFAULT 'en',   -- 'en' | 'he' | 'mixed'
    caption         TEXT,                          -- original title/caption if the source provided one
    embedding       VECTOR(512) NOT NULL,          -- clip-ViT-B-32-multilingual-v1 output, cosine-normalized
    width           INT,
    height          INT,
    file_size_bytes INT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- HNSW over IVFFlat: IVFFlat needs a representative sample at index-build time
-- (a poor fit for incremental one-by-one manual meme inserts done after
-- the bulk load). HNSW builds incrementally with good recall from row 1, and at
-- 5k-10k rows the index cost is a non-issue.
CREATE INDEX memes_embedding_hnsw_idx
    ON memes USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

Query-time: `ORDER BY embedding <=> :query_vector` (cosine distance). `SET hnsw.ef_search = 40;` is a per-session recall/speed knob worth tuning and writing up.

*(Hand-write this schema and the query logic — new territory: first time working with `pgvector`'s types/operators/index tuning, even though general SQL/Postgres is familiar ground.)*

## 3. Embedding Model & Pipeline

**Model:** `sentence-transformers/clip-ViT-B-32-multilingual-v1` — multilingual knowledge-distilled CLIP covering 50+ languages including Hebrew, 512-dim output, image and text share one embedding space, runs fully offline/CPU, no API key or cost.

```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('clip-ViT-B-32-multilingual-v1')
img_emb = model.encode(Image.open(path))     # ingestion
text_emb = model.encode("חתול מצחיק")         # query — same 512-d space
```

- **Bulk ingestion** (`scripts/ingest_kaggle.py`, run locally, not deployed): pulls the `electron0zero/memegenerator-dataset` Kaggle dataset (classic captioned template memes) via the `kaggle` CLI, tagged `source='kaggle_meme_generator'` — for each row: load image → embed → upload to S3 via boto3 → insert row, carrying over the dataset's caption/title. Batch-insert for throughput. This is the only bulk/automated source; the only other source is the manual admin-added batch below — no second Kaggle dataset.
- **Manual single-meme add** (for the user's own hand-picked Hebrew memes): a small **admin POST endpoint**, simple enough to hit repeatedly by hand (curl/Postman/a tiny local form) while going through a WhatsApp/Facebook-sourced batch one at a time. Both paths share one `ingest_service.py` module (embed → upload → insert) — one code path, not duplicated logic.

*(Hand-write the embedding/ingestion logic — new territory: first time integrating a multilingual CLIP model and reasoning about what its output actually represents.)*

## 4. API Design

```
GET  /healthz
     -> {"status": "ok"}, includes a lightweight DB check

GET  /api/search?q=<text>&k=<default 12>
     -> embeds q, runs:
        SELECT id, image_url, caption, source, 1 - (embedding <=> :q) AS score
        FROM memes ORDER BY embedding <=> :q LIMIT :k
     -> no auth required

POST /api/memes   (multipart: image + optional caption/language)
     -> requires Authorization: Bearer <JWT>, reusing the JWT pattern from
        slack-kudos-bot. Single hardcoded admin identity is enough — issue a
        long-lived token once via scripts/issue_admin_token.py, keep it in a
        local .env, never commit it.
     -> embeds + uploads to S3 + inserts row -> 201 {id, image_url}

GET  /api/memes/{id}   -> optional single-meme detail view
```

**CORS:** since the React frontend (Vercel domain) and backend (Lambda Function URL domain) are different origins, `CORSMiddleware` must explicitly allow the Vercel origin — a concrete, easy-to-miss integration detail worth understanding rather than cargo-culting a `allow_origins=["*"]`.

*(FastAPI route wiring, Pydantic response models, and JWT reuse are familiar territory from slack-kudos-bot — good candidates to let Claude Code draft, with deep review rather than hand-typing from scratch.)*

Rate limiting is explicitly out of scope for v1 (Future Work).

## 5. Suggested Pacing (flexible, not a deadline)

**Phase 1 — Data + embedding pipeline + schema** *(hand-write — pgvector and the embedding model are both new)*
- Repo skeleton, Docker Compose with local Postgres+pgvector, Alembic migration for the schema above.
- `kaggle` CLI download of the chosen dataset; hand-write `ingest_service.py` + `scripts/ingest_kaggle.py`.
- Run bulk ingestion locally; spot-check nearest-neighbor results directly in `psql` with `<=>` before building any API around it.
- Build the admin add-endpoint + JWT auth (JWT logic can lean on Claude Code + review, since it's a repeat of slack-kudos-bot); manually add the curated batch through it. Checkpoint: confirm cross-lingual search works both directions.

**Phase 2 — Search API** *(mixed: query logic hand-written, route/response-model boilerplate can lean on Claude Code + review)*
- `/api/search`, Pydantic response models, the `<=>` query — hand-write the query itself.
- `/healthz`, input validation.
- Tune `ef_search`/`m`/`ef_construction`; benchmark with `EXPLAIN ANALYZE` at real row counts — numbers worth putting in the README.
- Tests (pytest) — Claude Code can scaffold, hand-write the assertions.
- Point at the real Neon instance, re-run migrations there.

**Phase 3 — React + TypeScript frontend** *(hand-write — first time in this stack)*
- Scaffold with Vite (`npm create vite@latest -- --template react-ts`); learn the core loop deliberately: components, `useState`/`useEffect`, typed props, a typed `fetch` call to `/api/search`.
- Search box (RTL-aware for Hebrew input), results grid (image + caption + score), Tailwind for styling.
- Use Claude Code as an explainer here, not the primary author: ask it to explain unfamiliar TS/React patterns as they come up, write the components yourself, review its suggestions rather than pasting them in wholesale.

**Phase 4 — AWS deployment** *(hand-write — first time on AWS)*
- Dockerfile for the Lambda container image (`public.ecr.aws/lambda/python:3.12` base, CPU-only torch wheel, Mangum handler).
- Push to Amazon ECR, create the Lambda function from the container image, set memory (≥3008MB to comfortably fit torch+transformers+model) and timeout (~30s to cover cold-start model load).
- Hand-write the IAM role/policy: least-privilege, scoped to the specific S3 bucket/prefix only — a good opportunity to consciously avoid a wildcard policy.
- Enable a Lambda Function URL, configure CORS for the Vercel frontend origin.
- Deploy the S3 bucket for images; point `ingest_service.py`'s upload calls at it.
- GitHub Actions CI/CD reusing the slack-kudos-bot shape (lint/test on PR) but with new deploy steps (build+push to ECR, update Lambda function code on merge) — Claude Code can draft this YAML, review it against AWS's actual deploy docs rather than trusting it blindly, since IAM/ECR permission wiring in CI is a common source of subtle mistakes.
- Deploy the React frontend to Vercel (connect the GitHub repo, set the `VITE_API_URL` env var to the Lambda Function URL).
- Smoke-test the live URLs end-to-end (cold start latency, warm latency, both languages), write the README.

## 6. Deployment Summary

- **Local dev:** `docker-compose.yml` with `db` (Postgres+pgvector) and `app` (FastAPI, run via plain `uvicorn` locally — Mangum only matters in the deployed Lambda path); `.env.example` documents `DATABASE_URL`, AWS credentials, `JWT_SECRET`.
- **Backend container:** multi-stage Dockerfile, CPU-only torch (`--index-url https://download.pytorch.org/whl/cpu`) to avoid CUDA wheels, Mangum entrypoint for the Lambda handler.
- **CI/CD (GitHub Actions):** PR — lint (ruff) + pytest. Merge to `main` — backend: build → push to ECR → update Lambda function code; frontend: Vercel's own GitHub integration handles this automatically on push.
- **Live Postgres:** Neon (managed, free tier). Run Alembic migrations against Neon before first deploy.
- Images live in S3 from ingestion time onward, so the deployed Lambda image itself stays reasonably small and cold starts stay bounded to model load, not data transfer.

## 7. README / Portfolio Framing

1. One-line pitch + live demo link (Vercel frontend URL) at the top.
2. Architecture diagram (above).
3. **"Why pgvector, not a dedicated vector DB"** and **"Why Lambda, not Fargate/EC2"** — both genuinely good talking points: pgvector reused existing SQL strength at $0 indefinitely; Lambda was chosen over Fargate specifically because Fargate has no free tier for an always-on container, and over EC2 because EC2's free tier expires after 12 months and requires self-managed ops (nginx, TLS, patching) — Lambda's always-free tier and managed runtime fit a $0-forever portfolio project better.
4. Why one multilingual embedding model over a translate-then-embed pipeline.
5. **Tradeoffs, stated honestly:** Lambda cold starts (whole ML model reloads on cold invocation — noticeably slower first-hit latency than a warm request), S3's 5GB free tier is 12-months-only (storage cost afterward is a few cents/month, explicitly not a real risk at this scale), Neon's 0.5GB ceiling (fine at 10k memes), HNSW's approximate-recall tradeoff vs. brute force.
6. **Future Work** (explicitly deferred): GIF/video/sticker support, OCR-based text extraction, hybrid manual-tag boosting on top of embeddings, rate limiting, provisioned concurrency to reduce cold starts, scaling path if the corpus grows past Neon's free tier.
7. Setup instructions (`docker-compose up`, env vars, how to run ingestion scripts, how to deploy).

## Verification

- Local: `docker-compose up`, run `scripts/ingest_kaggle.py` against a small sample, hit `/api/search?q=...` for both an English and a Hebrew query, confirm sane top-K results.
- `pytest` for ingestion + search correctness.
- `EXPLAIN ANALYZE` on the search query at full row count to confirm the HNSW index is actually used (not a seq scan).
- After deploy: hit the Lambda Function URL directly (cold + warm request, compare latency), then hit the live Vercel frontend and confirm a browser search round-trips correctly (CORS working, results rendering) for both languages; confirm `/healthz` reports DB connectivity.
