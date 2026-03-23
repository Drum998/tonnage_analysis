# Market Data Flask App

This Flask app reads MySQL market data from the `market_data.brixham` table and displays:

- average `Price/KG` per day
- total `Weight` per day

The UI provides:

- species dropdown
- start date picker
- end date picker

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

## API endpoints

- `GET /api/species`
- `GET /api/timeseries?species=<name>&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
