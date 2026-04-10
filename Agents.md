# Legal Intelligence Prototype

## Stack
- Backend: Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2
- Frontend: Next.js 14 App Router, TypeScript, Tailwind CSS, TanStack Query
- Database: PostgreSQL 16 + pgvector extension (Cloud SQL in prod)
- AI: Vertex AI (Gemini 1.5 Pro for LLM, text-embedding-005 for embeddings)
- Document parsing: Google Cloud Document AI
- Async: Cloud Tasks (not Celery — no Redis)
- Storage: GCS for PDFs, Cloud SQL for structured data
- Deployment: Cloud Run, Cloud Build CI/CD

## Key models
- Contract: id, name, type, parties[], effective_date, expiry_date, gcs_uri, status
- Clause: id, contract_id, clause_type, raw_text, page_number, embedding (vector 768)
- Alert: id, clause_id_new, clause_id_existing, severity, explanation, status

## Clause types enum
EXCLUSIVITY, INDEMNITY, TERMINATION, GOVERNING_LAW, RENEWAL, 
PAYMENT, IP_OWNERSHIP, LIABILITY_CAP, CONFIDENTIALITY, OTHER

## Conventions
- All LLM calls return structured JSON — use Pydantic models to validate
- API routes return typed response models, never raw dicts
- Background tasks use Cloud Tasks HTTP queues, not Celery
- GCS bucket name: legal-intel-contracts-{project_id}
