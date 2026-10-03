# qr-feedback — project guide

FastAPI feedback MVP: public review forms per business slug, SQLite persistence, low-rating flags, password-protected administration and CSV export.

## Scope and source

This guide describes the default branch `main` reviewed on 3 October 2026. Commands were checked against committed manifests and configuration; applications and external integrations were not executed as part of this documentation update.

## Repository map

- `app/main.py`
- `app/db.py`
- `app/models.py`
- `app/templates`
- `app/static/styles.css`
- `requirements.txt`

## Prerequisites and local use

Clone the repository and enter its root directory:

```sh
git clone https://github.com/sarabranco92/qr-feedback.git
cd qr-feedback
```

### Installation (Windows PowerShell)

Run from the repository root so relative templates/static paths resolve:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:ADMIN_PASSWORD = "replace-with-your-local-password"
$env:SESSION_SECRET = "replace-with-a-long-random-secret"
$env:DB_PATH = "data/app.db"
python -m uvicorn app.main:app --reload
```

On macOS/Linux, activate with `source .venv/bin/activate` and set the same variables with `export`. If PowerShell activation is blocked, use `.\.venv\Scripts\python.exe` for pip/uvicorn instead of changing machine-wide policy.

Open http://127.0.0.1:8000/r/demo. SQLite tables and a demo business initialize on startup. Production needs persistent storage for DB_PATH, e.g. `/data/app.db` on a mounted disk, and a backup policy for review/contact data.

### Routes

| Method | Path | Purpose |
| --- | --- | --- |
| GET, POST | `/r/{slug}` | Public form and submission |
| POST | `/api/reviews` | Validated JSON review submission |
| GET, POST | `/admin/login` | Administrator sign-in |
| GET | `/admin/logout` | Clear session cookie |
| GET | `/admin` | Authenticated dashboard |
| POST | `/admin/reviews/{review_id}/seen` | Mark review seen |
| GET | `/admin/export.csv` | Authenticated CSV export |

An API review payload contains `business_slug`, `rating`, and optionally `comment` and `contact_email`. The app returns `{ "ok": true, "flagged": true/false }` after insertion.

## Configuration and implementation notes

Business slugs are created automatically when accessed. The admin dashboard shows at most 200 rows, while CSV export queries all rows. The default session secret is for development only; set your own. The code does not load dotenv automatically. Ratings are validated from 1 to 5, comments up to 1000 characters, and optional contact email uses EmailStr. Dependencies are unpinned and there is no committed automated test suite. This repo supplies review URLs, not an implemented QR-image generator.

## Verification checklist

Open `/r/demo`, submit a 1–5 rating, sign in through `/admin/login`, filter reviews, mark one seen, and download `/admin/export.csv`. Check that a rating of 1 or 2 is flagged and that admin routes reject an unauthenticated request.

No dedicated automated test/spec files were found in the reviewed application tree. Where a test script exists, its presence alone does not establish test coverage.

## Maintenance

Keep this guide in sync when routes, commands, environment variables or hosting paths change. Use development databases/accounts for integration checks. Keep private credentials in server-side environment configuration and out of documentation. No new license or ownership terms are introduced by this guide; retain existing repository notices.
