"""Unit tests for species normalization and date parsing."""
import pytest
from datetime import date

from app import _normalize_species, _parse_iso_date


class TestNormalizeSpecies:
    """Tests for _normalize_species."""

    def test_empty_input(self):
        assert _normalize_species("") == ""
        assert _normalize_species("   ") == ""
        assert _normalize_species(None) == ""

    def test_simple_species_old_format(self):
        assert _normalize_species("SOLE 4 - GUT Gutted - A") == "SOLE"
        assert _normalize_species("sole 4 - gut gutted - a") == "SOLE"

    def test_simple_species_new_format(self):
        assert _normalize_species("SOLE 1 - GUT Gutted - A") == "SOLE"
        assert _normalize_species("4 SOLE 1 - GUT Gutted - A") == "SOLE"
        assert _normalize_species("DAM SOLE 1 - GUT Gutted - A") == "SOLE"

    def test_th_wing_alias(self):
        assert _normalize_species("TH WING 1 - WNG Winged - A") == "THORNBACK"

    def test_butt_alias(self):
        assert _normalize_species("BUTT 1 - GUT Gutted - A") == "TURBOT"

    def test_plc_alias(self):
        assert _normalize_species("PLC 1 - GUT Gutted - A") == "PLAICE"

    def test_qualifier_stripping(self):
        assert _normalize_species("SOLE DAMAGED 1 - GUT") == "SOLE"
        assert _normalize_species("SOLE DAM 1 - GUT") == "SOLE"
        assert _normalize_species("SOLE MIXED 1 - GUT") == "SOLE"

    def test_fallback_no_grade_token(self):
        assert _normalize_species("SOME FISH 123") == "SOME FISH"


class TestParseIsoDate:
    """Tests for _parse_iso_date."""

    def test_valid_date(self):
        assert _parse_iso_date("2025-01-15", "start_date") == date(2025, 1, 15)
        assert _parse_iso_date("2024-12-31", "end_date") == date(2024, 12, 31)

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="Invalid start_date. Expected YYYY-MM-DD"):
            _parse_iso_date("15/01/2025", "start_date")
        with pytest.raises(ValueError, match="Invalid end_date"):
            _parse_iso_date("not-a-date", "end_date")

    def test_invalid_date_raises(self):
        with pytest.raises(ValueError, match="Invalid start_date"):
            _parse_iso_date("2025-02-30", "start_date")
