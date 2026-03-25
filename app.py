import os
import re
import statistics
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


@app.route("/metrics")
def metrics_page():
    return render_template("metrics.html")


@app.route("/metrics/guide")
def metrics_guide_page():
    return render_template("metrics_guide.html")


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


@app.get("/api/metrics")
def metrics():
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
            CAST(`Weight` AS DECIMAL(12,4)) AS weight,
            COALESCE(NULLIF(TRIM(`Gear`), ''), 'Unknown') AS gear
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

    # Daily aggregates (filtered by species)
    daily_buckets = defaultdict(
        lambda: {
            "prices": [],
            "price_total": 0.0,
            "lot_count": 0,
            "tonnage_total": 0.0,
            "value_total": 0.0,
        }
    )
    gear_totals = defaultdict(
        lambda: {"tonnage": 0.0, "value": 0.0, "lots": 0, "price_total": 0.0}
    )
    period_totals = {"lots": 0, "tonnage": 0.0, "value": 0.0, "price_sum": 0.0}

    for row in rows:
        if _normalize_species(row["raw_species"]) != normalized_selected_species:
            continue

        market_date = row["market_date"]
        if not market_date:
            continue

        price_per_kg = float(row["price_per_kg"] or 0.0)
        weight = float(row["weight"] or 0.0)
        gear = str(row["gear"] or "Unknown").strip() or "Unknown"
        value = price_per_kg * weight

        bucket = daily_buckets[market_date]
        bucket["prices"].append(price_per_kg)
        bucket["price_total"] += price_per_kg
        bucket["lot_count"] += 1
        bucket["tonnage_total"] += weight
        bucket["value_total"] += value

        g = gear_totals[gear]
        g["tonnage"] += weight
        g["value"] += value
        g["lots"] += 1
        g["price_total"] += price_per_kg

        period_totals["lots"] += 1
        period_totals["tonnage"] += weight
        period_totals["value"] += value
        period_totals["price_sum"] += price_per_kg

    daily_data = []
    for market_date in sorted(daily_buckets.keys()):
        b = daily_buckets[market_date]
        n = b["lot_count"]
        avg_price = b["price_total"] / n if n else 0.0
        median_price = (
            statistics.median(b["prices"]) if len(b["prices"]) >= 1 else 0.0
        )
        stdev_price = (
            statistics.stdev(b["prices"]) if len(b["prices"]) >= 2 else 0.0
        )
        cv = (stdev_price / avg_price * 100) if avg_price else 0.0
        avg_lot_size = b["tonnage_total"] / n if n else 0.0

        daily_data.append(
            {
                "date": market_date.isoformat(),
                "lot_count": n,
                "total_value": round(b["value_total"], 2),
                "total_tonnage": round(b["tonnage_total"], 2),
                "avg_lot_size": round(avg_lot_size, 2),
                "avg_price_per_kg": round(avg_price, 4),
                "median_price_per_kg": round(median_price, 4),
                "min_price_per_kg": round(min(b["prices"]), 4) if b["prices"] else 0.0,
                "max_price_per_kg": round(max(b["prices"]), 4) if b["prices"] else 0.0,
                "price_std_dev": round(stdev_price, 4),
                "coefficient_of_variation_pct": round(cv, 2),
            }
        )

    gear_breakdown = []
    total_tonnage_all = sum(g["tonnage"] for g in gear_totals.values())
    for gear, g in sorted(gear_totals.items()):
        avg_price = g["value"] / g["tonnage"] if g["tonnage"] else 0.0
        gear_breakdown.append(
            {
                "gear": gear,
                "tonnage": round(g["tonnage"], 2),
                "total_value": round(g["value"], 2),
                "lot_count": g["lots"],
                "avg_price_per_kg": round(avg_price, 4),
                "share_of_tonnage_pct": round(
                    g["tonnage"] / total_tonnage_all * 100, 1
                )
                if total_tonnage_all
                else 0.0,
            }
        )

    total_lots = period_totals["lots"]
    overall_avg_price = (
        period_totals["price_sum"] / total_lots if total_lots else 0.0
    )

    summary = {
        "total_lots": total_lots,
        "total_tonnage": round(period_totals["tonnage"], 2),
        "total_value": round(period_totals["value"], 2),
        "overall_avg_price_per_kg": round(overall_avg_price, 4),
    }

    # WoW and MoM from daily_data (compare first vs last week, first vs last month)
    wow_change = None
    mom_change = None
    if len(daily_data) >= 8:
        last_week = daily_data[-7:]
        prev_week = daily_data[-14:-7]
        if prev_week:
            last_val = sum(d["total_value"] for d in last_week)
            prev_val = sum(d["total_value"] for d in prev_week)
            if prev_val:
                wow_change = round((last_val - prev_val) / prev_val * 100, 1)
    if len(daily_data) >= 31:
        last_month = daily_data[-30:]
        prev_month = daily_data[-60:-30]
        if prev_month:
            last_val = sum(d["total_value"] for d in last_month)
            prev_val = sum(d["total_value"] for d in prev_month)
            if prev_val:
                mom_change = round((last_val - prev_val) / prev_val * 100, 1)

    # Price-tonnage correlation over daily points
    price_tonnage_corr = None
    if len(daily_data) >= 2:
        prices = [d["avg_price_per_kg"] for d in daily_data]
        tonnages = [d["total_tonnage"] for d in daily_data]
        try:
            price_tonnage_corr = round(
                statistics.correlation(prices, tonnages), 4
            )
        except statistics.StatisticsError:
            pass

    return jsonify(
        {
            "species": normalized_selected_species,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "summary": summary,
            "wow_change_pct": wow_change,
            "mom_change_pct": mom_change,
            "price_tonnage_correlation": price_tonnage_corr,
            "daily": daily_data,
            "gear_breakdown": gear_breakdown,
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
