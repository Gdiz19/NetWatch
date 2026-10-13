from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.database import (
    get_latest_measurement,
    get_measurement_count,
    get_recent_measurements,
    get_recent_outages,
    initialize_database,
)


app = FastAPI(
    title="NetWatch API",
    description="API for the NetWatch network health monitoring system.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    """Make sure the database exists when the API starts."""

    initialize_database()


def measurement_to_dict(measurement):
    """Convert a database measurement row into JSON-friendly data."""

    if measurement is None:
        return None

    (
        recorded_at,
        check_type,
        target,
        is_healthy,
        latency_ms,
        packet_loss,
        details,
    ) = measurement

    return {
        "recorded_at": recorded_at,
        "check_type": check_type,
        "target": target,
        "is_healthy": bool(is_healthy),
        "latency_ms": latency_ms,
        "packet_loss": packet_loss,
        "details": details,
    }


def outage_to_dict(outage):
    """Convert an outage database row into JSON-friendly data."""

    (
        outage_id,
        started_at,
        ended_at,
        duration_seconds,
    ) = outage

    return {
        "id": outage_id,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_seconds": duration_seconds,
        "active": ended_at is None,
    }


@app.get("/")
def root():
    return {
        "name": "NetWatch API",
        "message": "Network monitoring API is running.",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "NetWatch API",
    }


@app.get("/status")
def network_status():
    router = get_latest_measurement("router")
    internet = get_latest_measurement("internet")
    dns = get_latest_measurement("dns")

    return {
        "router": measurement_to_dict(router),
        "internet": measurement_to_dict(internet),
        "dns": measurement_to_dict(dns),
        "measurement_count": get_measurement_count(),
    }


@app.get("/measurements")
def measurements(
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
    ),
):
    rows = get_recent_measurements(limit)

    return {
        "count": len(rows),
        "measurements": [
            measurement_to_dict(row)
            for row in rows
        ],
    }


@app.get("/outages")
def outages(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
):
    rows = get_recent_outages(limit)

    return {
        "count": len(rows),
        "outages": [
            outage_to_dict(row)
            for row in rows
        ],
    }