# Smart PYQ Flask API

This folder is a new API boundary. Existing OCR, C++ and database scripts are
not imported or modified by the Flask application.

## Configure credentials in PowerShell

```powershell
$env:MYSQL_HOST = "localhost"
$env:MYSQL_PORT = "3306"
$env:MYSQL_DATABASE = "smart_pyq_db"
$env:MYSQL_USER = "root"
$env:MYSQL_PASSWORD = "<your-local-password>"
$env:FRONTEND_ORIGIN = "http://localhost:5500"
$env:FLASK_SECRET_KEY = "<long-random-session-secret>"
```

The password is intentionally not stored in this repository or sent to the
browser.

## Run

From `C:\PYQ`:

```powershell
C:\Python315\python.exe -m flask --app backend.app run --host 127.0.0.1 --port 5000
```

Run the frontend in another terminal so the browser has an HTTP origin:

```powershell
C:\Python315\python.exe -m http.server 5500 --directory frontend
```

## Endpoints

- `GET /api/papers` — returns `{ "data": [...], "count": n }` from `question_papers`.
- `GET /api/papers/<id>` — returns one paper or HTTP 404.
- `GET /api/repeated-questions` — groups exact normalized question matches across at least two distinct papers. Supports `subject`, `exam_year`, and `min_frequency` filters.
- `POST /api/papers` — accepts a multipart PDF field named `pdf` plus `subject`,
  `academic_year`, `semester`, `exam_year`, `term`, and `paper_code`.

The upload route saves the PDF under `input_pdfs`, reuses the existing OCR
converter and question extractor, writes text under `output_text`, and commits
the paper/questions transaction only after verification. Uploads require an
authenticated administrator session and CSRF token; frontend role visibility is
not a security boundary. Students use public read-only APIs without accounts.

Administrator sessions are opaque HttpOnly cookies backed by the `auth_sessions`
table; the cookie does not contain admin credentials or session state. The first
administrator can be created interactively with:

```powershell
python -m backend.create_admin
```

The existing `question_papers` contract does not include `semester` or
`paper_code`. The upload accepts both fields and persists them if matching
columns exist, otherwise returns a warning without changing the schema.

Supported collection filters are `q`, `subject`, `academic_year`, `exam_year`
and `term`. PDF and text path columns are returned unchanged.
