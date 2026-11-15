# Smart PYQ C++ Processing Engine — Milestone 3

A standalone C++17 prototype that accepts OCR/text output from an upstream PDF pipeline.

## Milestone 3 additions
- Paper metadata sidecars (`.meta`) for course, academic year, exam year, subject, term, and paper code.
- Multiple paper files can be loaded in one run.
- Cross-paper similarity reporting, excluding comparisons within the same paper label.
- Nested Roman subpart labels such as `1(a)(i)` are recognized beneath an alphabetic subpart.
- SHA-256 fingerprints and exact-repeat grouping remain included.

## Metadata format
For `paper_2024.txt`, create `paper_2024.meta` in the same folder:
```ini
course=B.Tech CSE
academic_year=2023-2024
exam_year=2024
subject=Data Structures
term=End Term
paper_code=DS-END-2024
```
Keys are case-insensitive. Metadata is optional; missing fields remain blank.

## Build (Windows MinGW)
```powershell
g++ -std=c++17 -O2 -I include src/*.cpp -o smart_pyq_cpp.exe
```

## Run one or more papers
```powershell
.\smart_pyq_cpp.exe samples/sample_ocr_2024.txt samples/sample_ocr_2025.txt
```
Each input file is parsed independently and its metadata is loaded from a same-basename `.meta` file.

## Scope and limitations
- No PDF rendering or OCR: input must already be extracted text.
- Not integrated with Flask, TiDB/MySQL, or Supabase; production backend remains unchanged.
- Parser support for nested Roman subparts is basic and should be validated on real PYQ OCR output. It does not yet support every paper-specific numbering convention.
- Similarity is token-set Jaccard, not the production Python TF-IDF/concept-similarity method. The 0.50 threshold is a prototype setting, not a validated academic threshold.
- Exact repeats are based on normalized text; metadata does not alter the fingerprint.

## Parser unit test
Compile and run the focused parser/SHA test (exclude `src/main.cpp`):
```powershell
g++ -std=c++17 -O2 -I include tests/test_engine.cpp src/QuestionParser.cpp src/TextNormalizer.cpp src/SHA256.cpp -o test_engine.exe
.\test_engine.exe
```


## Milestone 4 — indexed search and paper analytics

The engine now also contains reusable modules for:
- In-memory inverted indexing over normalized question text.
- BM25-style ranked keyword search with subject, academic-year, exam-year, and term filters.
- Pagination and corpus statistics for search results.
- Question counts by exam year and subject.
- Recurring-question trend aggregation across exam years.
- Exact-repeat rate calculation.
- CSV export with quoted/escaped fields.
- A focused search and analytics test executable.

### Build and test with CMake

```powershell
cmake -S . -B build
cmake --build build --config Release
ctest --test-dir build --output-on-failure
```

The modules are currently reusable C++ library-style components. They are not connected to the Flask production API or production database. The search index is in-memory and is rebuilt from the supplied question collection.
