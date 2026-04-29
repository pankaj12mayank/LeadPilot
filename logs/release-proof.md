# Release Proof

- Mode: `quick`
- Status: `PASS`

| Check | Exit | Seconds |
|---|---:|---:|
| Backend auth + isolation | 0 | 6.31 |
| Backend debug validation | 0 | 4.53 |
| Backend ingestion reliability | 0 | 8.00 |
| Explorer regression guard | 0 | 17.57 |
| Frontend search/mode smoke | 0 | 3.91 |

## Backend auth + isolation

- Command: `C:\Python314\python.exe -m pytest tests/test_auth.py -q`
- Exit: `0`

```text
....                                                                     [100%]
4 passed in 1.91s
```

## Backend debug validation

- Command: `C:\Python314\python.exe -m pytest tests/test_debug_validation.py -q`
- Exit: `0`

```text
.                                                                        [100%]
1 passed in 0.37s
```

## Backend ingestion reliability

- Command: `C:\Python314\python.exe -m pytest tests/test_company_ingestion_service.py -q`
- Exit: `0`

```text
.........                                                                [100%]
9 passed in 4.23s
```

## Explorer regression guard

- Command: `C:\Python314\python.exe -m pytest tests/test_companies_api.py::test_companies_explorer_search_supports_filters_and_enriched_columns -q`
- Exit: `0`

```text
.                                                                        [100%]
1 passed in 13.47s
```

## Frontend search/mode smoke

- Command: `C:\Program Files\nodejs\npm.cmd run test -- SearchLeadsPage`
- Exit: `0`

```text
> frontend@0.0.0 test
> vitest run SearchLeadsPage


 RUN  v3.2.4 D:/Py_Projects/Leadpilot/frontend

 âœ“ src/pages/SearchLeadsPage.test.tsx (3 tests) 257ms

 Test Files  1 passed (1)
      Tests  3 passed (3)
   Start at  18:56:49
   Duration  2.25s (transform 209ms, setup 115ms, collect 543ms, tests 257ms, environment 624ms, prepare 232ms)
```

Final decision: **READY**