# Changelog

All notable changes to the Market Data Explorer app are documented here.

## [Unreleased]

- Date preset buttons (Last Week, Last Month, Last 3 Months, This Month, Last Year, Last 12 Months, Year to Date)
- Unit tests for species normalization, date parsing, and API endpoints
- Test runner script (`run_tests.py`)
- Documentation (TESTING.md, CHANGELOG.md)

## Initial release

- Flask app reading MySQL market data from `market_data.brixham`
- Species dropdown, start/end date pickers
- Price vs Tonnage chart (Chart.js, dual axis)
- 21-day moving average smoothing
- Print chart support
- API: `GET /api/species`, `GET /api/timeseries`
- Species normalization with aliases (e.g. PLC -> PLAICE, BUTT -> TURBOT)
- Docker and Docker Compose support
