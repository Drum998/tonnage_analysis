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
