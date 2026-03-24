# Testing

This document describes how to run the unit tests for the Market Data Explorer app.

## Prerequisites

Install dependencies including pytest:

```bash
pip install -r requirements.txt
```

## Running tests

From the project root, run all tests with:

```bash
python run_tests.py
```

Or run pytest directly:

```bash
python -m pytest test/ -v
```

To run tests inside the Docker container:

```bash
docker compose run --rm web python run_tests.py
```

## Test structure

Tests live in the `test/` folder:

| File | Description |
|------|-------------|
| `test/conftest.py` | Pytest configuration; sets required env vars so the app can be imported without a real database |
| `test/test_normalize_species.py` | Unit tests for `_normalize_species` (species name parsing, aliases) and `_parse_iso_date` |
| `test/test_api.py` | API endpoint tests (index, `/api/species`, `/api/timeseries`) with mocked database |

## Mocking

The API tests mock the database engine. No MySQL connection is required. The `conftest.py` sets dummy values for `DB_HOST`, `DB_USER`, `DB_PASSWORD`, and `DB_DATABASE` so the app module loads; `test_api.py` patches the engine to return controlled row data.

## Frontend

The JavaScript in `static/app.js` (date presets, moving average, etc.) is not currently covered by automated tests. Manual verification or browser-based tests could be added in future.
