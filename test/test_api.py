"""API endpoint tests with mocked database."""
from contextlib import contextmanager
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@contextmanager
def mock_db_connection(rows):
    """Mock engine.connect() to yield a connection that returns the given rows."""
    mock_conn = MagicMock()
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = rows
    mock_conn.execute.return_value = mock_result
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    with patch("app.engine") as mock_engine:
        mock_engine.connect.return_value = mock_conn
        yield


class TestIndex:
    def test_index_returns_html(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert b"Market Data Explorer" in r.data
        assert b"start_date" in r.data
        assert b"end_date" in r.data


class TestMetricsPage:
    def test_metrics_returns_html(self, client):
        r = client.get("/metrics")
        assert r.status_code == 200
        assert b"Market Metrics" in r.data
        assert b"start_date" in r.data
        assert b"end_date" in r.data
        assert b"Load Metrics" in r.data
        assert b"species" in r.data
        assert b"Last Week" in r.data


class TestSpeciesApi:
    def test_species_returns_sorted_list(self, client):
        raw_rows = [
            {"species": "SOLE 4 - GUT Gutted - A"},
            {"species": "PLC 1 - GUT Gutted - A"},
            {"species": "BUTT 1 - GUT Gutted - A"},
        ]
        with mock_db_connection(raw_rows):
            r = client.get("/api/species")
        assert r.status_code == 200
        data = r.get_json()
        assert isinstance(data, list)
        assert "SOLE" in data
        assert "PLAICE" in data
        assert "TURBOT" in data
        assert data == sorted(data)

    def test_species_filters_empty(self, client):
        raw_rows = [
            {"species": "SOLE 4 - GUT Gutted - A"},
            {"species": ""},
            {"species": "   "},
        ]
        with mock_db_connection(raw_rows):
            r = client.get("/api/species")
        assert r.status_code == 200
        data = r.get_json()
        assert "SOLE" in data
        assert len(data) >= 1


class TestTimeseriesApi:
    def test_timeseries_requires_species(self, client):
        r = client.get("/api/timeseries?start_date=2025-01-01&end_date=2025-01-31")
        assert r.status_code == 400
        assert "species" in r.get_json()["error"].lower()

    def test_timeseries_requires_dates(self, client):
        r = client.get("/api/timeseries?species=SOLE")
        assert r.status_code == 400
        assert "start_date" in r.get_json()["error"].lower() or "end_date" in r.get_json()["error"].lower()

    def test_timeseries_invalid_date_format(self, client):
        r = client.get(
            "/api/timeseries?species=SOLE&start_date=01/01/2025&end_date=2025-01-31"
        )
        assert r.status_code == 400
        assert "Invalid" in r.get_json()["error"]

    def test_timeseries_start_after_end(self, client):
        r = client.get(
            "/api/timeseries?species=SOLE&start_date=2025-01-31&end_date=2025-01-01"
        )
        assert r.status_code == 400
        assert "before" in r.get_json()["error"].lower()

    def test_timeseries_success_with_mock_data(self, client):
        raw_rows = [
            {
                "market_date": date(2025, 1, 15),
                "raw_species": "SOLE 4 - GUT Gutted - A",
                "price_per_kg": 5.5,
                "weight": 100.0,
            },
        ]
        with mock_db_connection(raw_rows):
            r = client.get(
                "/api/timeseries?species=SOLE&start_date=2025-01-01&end_date=2025-01-31"
            )
        assert r.status_code == 200
        data = r.get_json()
        assert data["species"] == "SOLE"
        assert data["start_date"] == "2025-01-01"
        assert data["end_date"] == "2025-01-31"
        assert len(data["data"]) == 1
        assert data["data"][0]["date"] == "2025-01-15"
        assert data["data"][0]["avg_price_per_kg"] == 5.5
        assert data["data"][0]["total_tonnage"] == 100.0


class TestMetricsApi:
    def test_metrics_requires_species(self, client):
        r = client.get("/api/metrics?start_date=2025-01-01&end_date=2025-01-31")
        assert r.status_code == 400
        assert "species" in r.get_json()["error"].lower()

    def test_metrics_requires_dates(self, client):
        r = client.get("/api/metrics?species=SOLE")
        assert r.status_code == 400
        assert "start_date" in r.get_json()["error"].lower() or "end_date" in r.get_json()["error"].lower()

    def test_metrics_invalid_date_format(self, client):
        r = client.get(
            "/api/metrics?species=SOLE&start_date=01/01/2025&end_date=2025-01-31"
        )
        assert r.status_code == 400
        assert "Invalid" in r.get_json()["error"]

    def test_metrics_start_after_end(self, client):
        r = client.get(
            "/api/metrics?species=SOLE&start_date=2025-01-31&end_date=2025-01-01"
        )
        assert r.status_code == 400
        assert "before" in r.get_json()["error"].lower()

    def test_metrics_success_with_mock_data(self, client):
        raw_rows = [
            {
                "market_date": date(2025, 1, 15),
                "raw_species": "SOLE 4 - GUT Gutted - A",
                "price_per_kg": 5.5,
                "weight": 100.0,
                "gear": "Trawl",
            },
        ]
        with mock_db_connection(raw_rows):
            r = client.get(
                "/api/metrics?species=SOLE&start_date=2025-01-01&end_date=2025-01-31"
            )
        assert r.status_code == 200
        data = r.get_json()
        assert data["species"] == "SOLE"
        assert "summary" in data
        assert data["summary"]["total_lots"] == 1
        assert data["summary"]["total_tonnage"] == 100.0
        assert data["summary"]["total_value"] == 550.0
        assert len(data["daily"]) == 1
        assert data["daily"][0]["lot_count"] == 1
        assert data["daily"][0]["min_price_per_kg"] == 5.5
        assert data["daily"][0]["max_price_per_kg"] == 5.5
        assert data["daily"][0]["median_price_per_kg"] == 5.5
        assert len(data["gear_breakdown"]) == 1
        assert data["gear_breakdown"][0]["gear"] == "Trawl"

    def test_metrics_empty_result_when_no_matching_species(self, client):
        raw_rows = [
            {
                "market_date": date(2025, 1, 15),
                "raw_species": "PLC 1 - GUT Gutted - A",
                "price_per_kg": 3.0,
                "weight": 50.0,
                "gear": "Trawl",
            },
        ]
        with mock_db_connection(raw_rows):
            r = client.get(
                "/api/metrics?species=SOLE&start_date=2025-01-01&end_date=2025-01-31"
            )
        assert r.status_code == 200
        data = r.get_json()
        assert data["species"] == "SOLE"
        assert data["summary"]["total_lots"] == 0
        assert data["summary"]["total_tonnage"] == 0
        assert data["summary"]["total_value"] == 0
        assert len(data["daily"]) == 0
        assert len(data["gear_breakdown"]) == 0

    def test_metrics_gear_null_becomes_unknown(self, client):
        raw_rows = [
            {
                "market_date": date(2025, 1, 15),
                "raw_species": "SOLE 4 - GUT Gutted - A",
                "price_per_kg": 5.0,
                "weight": 80.0,
                "gear": None,
            },
        ]
        with mock_db_connection(raw_rows):
            r = client.get(
                "/api/metrics?species=SOLE&start_date=2025-01-01&end_date=2025-01-31"
            )
        assert r.status_code == 200
        data = r.get_json()
        assert len(data["gear_breakdown"]) == 1
        assert data["gear_breakdown"][0]["gear"] == "Unknown"

    def test_metrics_daily_aggregate_fields(self, client):
        raw_rows = [
            {
                "market_date": date(2025, 1, 15),
                "raw_species": "SOLE 4 - GUT Gutted - A",
                "price_per_kg": 4.0,
                "weight": 50.0,
                "gear": "Trawl",
            },
            {
                "market_date": date(2025, 1, 15),
                "raw_species": "SOLE 4 - GUT Gutted - A",
                "price_per_kg": 6.0,
                "weight": 50.0,
                "gear": "Trawl",
            },
        ]
        with mock_db_connection(raw_rows):
            r = client.get(
                "/api/metrics?species=SOLE&start_date=2025-01-01&end_date=2025-01-31"
            )
        assert r.status_code == 200
        data = r.get_json()
        daily = data["daily"][0]
        assert daily["lot_count"] == 2
        assert daily["total_tonnage"] == 100.0
        assert daily["total_value"] == 500.0
        assert daily["avg_lot_size"] == 50.0
        assert daily["avg_price_per_kg"] == 5.0
        assert daily["median_price_per_kg"] == 5.0
        assert daily["min_price_per_kg"] == 4.0
        assert daily["max_price_per_kg"] == 6.0
        assert daily["price_std_dev"] == pytest.approx(1.414, rel=0.01)
        assert daily["coefficient_of_variation_pct"] == pytest.approx(28.28, rel=0.1)

    def test_metrics_multiple_days_gear_breakdown(self, client):
        raw_rows = [
            {
                "market_date": date(2025, 1, 15),
                "raw_species": "SOLE 4 - GUT Gutted - A",
                "price_per_kg": 5.0,
                "weight": 100.0,
                "gear": "Trawl",
            },
            {
                "market_date": date(2025, 1, 16),
                "raw_species": "SOLE 4 - GUT Gutted - A",
                "price_per_kg": 6.0,
                "weight": 80.0,
                "gear": "Gillnet",
            },
        ]
        with mock_db_connection(raw_rows):
            r = client.get(
                "/api/metrics?species=SOLE&start_date=2025-01-01&end_date=2025-01-31"
            )
        assert r.status_code == 200
        data = r.get_json()
        assert len(data["daily"]) == 2
        assert len(data["gear_breakdown"]) == 2
        gears = {g["gear"]: g for g in data["gear_breakdown"]}
        assert gears["Trawl"]["tonnage"] == 100.0
        assert gears["Trawl"]["total_value"] == 500.0
        assert gears["Gillnet"]["tonnage"] == 80.0
        assert gears["Gillnet"]["total_value"] == 480.0
