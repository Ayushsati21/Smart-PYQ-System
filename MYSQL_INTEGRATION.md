# Smart PYQ MySQL integration

## How the parts connect

- `batch_pdf_to_text.py` keeps the existing CPU OCR and text-file output flow. It imports or updates one `question_papers` row per PDF, with a transaction for the paper and its clearly numbered questions.
- `pyq_metadata.py` reads common subject, semester, term, and exam-year patterns from the current filenames. Unrecognized values stay `NULL`; an empty inferred value does not erase metadata already in MySQL.
- `pyq_questions.py` splits only lines beginning with a question number such as `Q1.` or `1.`. It joins continuation lines and normalizes Unicode, case, whitespace, and spaces before punctuation. It does not compare by keywords.
- `pbl_project.cpp` calls `pyq_database.py` for paper browsing/text retrieval and for repeated-question reports. The C++ repeated-question/DSP/OOP program remains in C++; Connector/Python handles database access.

## One-time database setup

The existing `question_papers` table is not modified by the migration. In MySQL Workbench, connect to `smart_pyq_db`, open `migrations/001_create_questions.sql`, and execute it. It creates `questions` with a restrictive foreign key, a per-paper normalized-question unique key, and an index for matching across papers. Running it again is safe.

The live schema could not be inspected from this workspace because MySQL rejected the available `root` connection without a password. Both scripts check required columns when they connect and report schema mismatches.

## Configure and run (PowerShell)

Set credentials in the PowerShell session used to run the scripts; do not put the password in source code:

```powershell
$env:MYSQL_HOST = "localhost"
$env:MYSQL_PORT = "3306"
$env:MYSQL_USER = "root"
$env:MYSQL_PASSWORD = Read-Host "MySQL password"
```

The OCR package set is already part of this project. If Connector/Python is missing:

```powershell
python -m pip install mysql-connector-python
```

Then run OCR/import from `C:\PYQ` (the script reuses existing `output_text` files):

```powershell
python batch_pdf_to_text.py
```

Compile and launch the C++ application from the project directory so it can find `pyq_database.py`:

```powershell
g++ -std=c++11 -Wall -Wextra -pedantic pbl_project.cpp -o pbl_project.exe
.\pbl_project.exe
```

Choose the stored-question analysis menu option and apply the requested filters. OCR that cannot be split confidently remains available in `question_papers.extracted_text`, but is excluded from repeated-question counts. The C++ manual-entry mode remains temporary; persistent cross-paper analysis uses imported, paper-linked questions.
