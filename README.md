# Market Data Explorer

A Flask app that reads MySQL market data from the `market_data.brixham` table and displays:

- average `Price/KG` per day
- total tonnage (Weight) per day

The UI provides:

- species dropdown
- start and end date pickers
- preset date range buttons (Last Week, Last Month, Last 3 Months, This Month, Last Year, Last 12 Months, Year to Date)
- interactive Price vs Tonnage chart with 21-day moving average
- print chart support

The **Metrics** page (`/metrics`) adds extended analytics with the same date range controls:

- Summary cards: total lots, tonnage, value, avg price, WoW/MoM change, price-tonnage correlation
- Lot count and total value over time (21-day smoothed)
- Price distribution: min, max, median, avg (21-day smoothed)
- Average lot size and price volatility over time (21-day smoothed)
- Gear breakdown by tonnage and value (doughnut and bar charts)

## Required environment variables

The app expects:

- `DB_HOST`
- `DB_USER`
- `DB_PASSWORD`
- `DB_DATABASE`
- `DB_PORT` (optional, defaults to `3306`)

You can use `example.env` as your env file.

## Build image

```bash
docker build -t tonnage-analysis-flask .
```

## Docker Compose (recommended)

Start:

```bash
docker compose up --build -d
```

Stop:

```bash
docker compose down
```

## Run container

Use host port `5055` to avoid conflicts:

```bash
docker run --rm -p 5055:5000 --env-file example.env --name tonnage-analysis-flask tonnage-analysis-flask
```

## Open app

Open:

`http://localhost:5055`

## Testing

Run unit tests:

```bash
python run_tests.py
```

See [docs/TESTING.md](docs/TESTING.md) for details.

## API endpoints

- `GET /api/species` - returns normalized species list
- `GET /api/timeseries?species=<name>&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` - returns daily averages and tonnage
- `GET /api/metrics?species=<name>&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` - returns extended metrics (lot count, value, price distribution, gear breakdown)

## Pages

- `/` - Market Data Explorer (price vs tonnage chart)
- `/metrics` - Market Metrics (extended metrics and charts)
