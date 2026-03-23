import os
import re
from collections import defaultdict
from datetime import date

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from sqlalchemy import create_engine, text


load_dotenv()

app = Flask(__name__)


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _build_db_url() -> str:
    host = _required_env("DB_HOST")
    user = _required_env("DB_USER")
    password = _required_env("DB_PASSWORD")
    database = _required_env("DB_DATABASE")
    port = os.getenv("DB_PORT", "3306").strip() or "3306"
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"


engine = create_engine(_build_db_url(), pool_pre_ping=True, future=True)


def _parse_iso_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except Exception as exc:
        raise ValueError(f"Invalid {field_name}. Expected YYYY-MM-DD.") from exc


def _normalize_species(raw_species: str) -> str:
    if not raw_species:
        return ""

    species = str(raw_species).strip().upper()
    if not species:
        return ""

    # Remove leading size/condition prefixes seen in newer format.
    # Examples:
    # - "4 SOLE 1 - GUT Gutted - A"
    # - "DAM SOLE 1 - GUT Gutted - A"
    cleaned = re.sub(r"^(?:\d+|DAM|SL)\s+", "", species)

    # Extract segment before quality/processing marker in both old/new styles.
    # Examples:
    # - old: "SOLE 4 - GUT Gutted - A" -> "SOLE"
    # - new: "SOLE 1 - GUT Gutted - A" -> "SOLE"
    # - new: "TH WING 1 - WNG Winged - A" -> "TH WING"
    match = re.match(r"^([A-Z ]+?)\s+\d+\s*-", cleaned)
    if match:
        base = match.group(1).strip()
    else:
        # Fallback for rows without expected grade token.
        # Use text before first '-' and remove trailing numeric tokens.
        base = cleaned.split("-", 1)[0].strip()
        base = re.sub(r"\s+\d+$", "", base).strip()

    alias_map = {
        "PLC": "PLAICE",
        "LEM": "LEMON SOLE",
        "DORY": "JOHN DORY",
        "TH WING": "THORNBACK",
        "SP WING": "SPOT WINGS",
        "BL WING": "BLONDE WING",
        "CUTT": "CUTTLE",
        "WHIT": "WHITING",
        "POLL": "POLLACK",
        "GURN": "GURNARD",
        "MEG": "MEGRIM",
        "TUB": "TUB GURNARD",
        "UN RAY": "UNDULATE RAY",
        "BRU BUTT": "TURBOT BRU",
        "BUTT": "TURBOT",
        "RED": "RED MULLET",
        "LOB": "LOBSTER",
    }

    if base in alias_map:
        return alias_map[base]

    # Normalize common qualifiers that may appear in old format.
    for qualifier in [" DAMAGED", " DAM", " MIXED", " NELSON"]:
        if base.endswith(qualifier):
            base = base[: -len(qualifier)].strip()

    return base


@app.route("/")
def index():
    return render_template("index.html")


@app.get("/api/species")
def species_options():
    query = text(
        """
        SELECT DISTINCT `Species` AS species
        FROM `brixham`
        WHERE `Species` IS NOT NULL AND `Species` <> ''
        ORDER BY `Species` ASC
        """
    )

    with engine.connect() as connection:
        rows = connection.execute(query).mappings().all()

    normalized_species = sorted(
        {
            _normalize_species(row["species"])
            for row in rows
            if _normalize_species(row["species"])
        }
    )
    return jsonify(normalized_species)


@app.get("/api/timeseries")
def timeseries():
    selected_species = request.args.get("species", "").strip()
    start_date_raw = request.args.get("start_date", "").strip()
    end_date_raw = request.args.get("end_date", "").strip()

    if not selected_species:
        return jsonify({"error": "species is required"}), 400
    if not start_date_raw or not end_date_raw:
        return jsonify({"error": "start_date and end_date are required"}), 400

    try:
        start_date = _parse_iso_date(start_date_raw, "start_date")
        end_date = _parse_iso_date(end_date_raw, "end_date")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if start_date > end_date:
        return jsonify({"error": "start_date must be before or equal to end_date"}), 400

    normalized_selected_species = _normalize_species(selected_species)
    if not normalized_selected_species:
        return jsonify({"error": "invalid species value"}), 400

    query = text(
        """
        SELECT
            DATE(`Date`) AS market_date,
            `Species` AS raw_species,
            CAST(`Price/KG` AS DECIMAL(12,4)) AS price_per_kg,
            CAST(`Weight` AS DECIMAL(12,4)) AS weight
        FROM `brixham`
        WHERE DATE(`Date`) BETWEEN :start_date AND :end_date
        """
    )

    with engine.connect() as connection:
        rows = connection.execute(
            query,
            {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        ).mappings().all()

    aggregates = defaultdict(lambda: {"price_total": 0.0, "price_count": 0, "tonnage_total": 0.0})
    for row in rows:
        if _normalize_species(row["raw_species"]) != normalized_selected_species:
            continue

        market_date = row["market_date"]
        if not market_date:
            continue

        price_per_kg = float(row["price_per_kg"] or 0.0)
        weight = float(row["weight"] or 0.0)
        bucket = aggregates[market_date]
        bucket["price_total"] += price_per_kg
        bucket["price_count"] += 1
        bucket["tonnage_total"] += weight

    data = []
    for market_date in sorted(aggregates.keys()):
        bucket = aggregates[market_date]
        avg_price = bucket["price_total"] / bucket["price_count"] if bucket["price_count"] else 0.0
        data.append(
            {
                "date": market_date.isoformat(),
                "avg_price_per_kg": avg_price,
                "total_tonnage": bucket["tonnage_total"],
            }
        )

    return jsonify(
        {
            "species": normalized_selected_species,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "data": data,
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
