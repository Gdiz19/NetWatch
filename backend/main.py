import threading
from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from backend.monitor import run_monitor_loop

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

from backend.database import (
    get_devices,
    get_latest_measurement,
    get_measurement_count,
    get_measurements_by_type,
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

monitor_stop_event = threading.Event()
monitor_thread = None

@app.on_event("startup")
def startup_event():
    """Initialize NetWatch and start background monitoring."""

    global monitor_thread

    initialize_database()

    monitor_stop_event.clear()

    monitor_thread = threading.Thread(
        target=run_monitor_loop,
        args=(monitor_stop_event,),
        daemon=True,
    )

    monitor_thread.start()

@app.on_event("shutdown")
def shutdown_event():
    """Stop the background monitor when FastAPI shuts down."""

    monitor_stop_event.set()

    if (
        monitor_thread is not None
        and monitor_thread.is_alive()
    ):
        monitor_thread.join(timeout=5)

def device_to_dict(device):
    """Convert a database device row into JSON-friendly data."""

    (
        device_id,
        ip_address,
        mac_address,
        interface_alias,
        neighbor_state,
        first_seen,
        last_seen,
        last_online,
        is_online,
    ) = device

    return {
        "id": device_id,
        "ip_address": ip_address,
        "mac_address": mac_address,
        "interface_alias": interface_alias,
        "neighbor_state": neighbor_state,
        "first_seen": first_seen,
        "last_seen": last_seen,
        "last_online": last_online,
        "responding": bool(is_online),
    }


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

@app.get("/history")
def history(
    limit: int = Query(
        default=120,
        ge=1,
        le=1000,
    ),
):
    rows = get_measurements_by_type(
        "internet",
        limit,
    )

    return {
        "count": len(rows),
        "measurements": [
            measurement_to_dict(row)
            for row in rows
        ],
    }

@app.get("/stats")
def stats(
    limit: int = Query(
        default=500,
        ge=1,
        le=5000,
    ),
):
    rows = get_measurements_by_type(
        "internet",
        limit,
    )

    if not rows:
        return {
            "sample_size": 0,
            "average_latency_ms": None,
            "minimum_latency_ms": None,
            "maximum_latency_ms": None,
            "average_packet_loss": None,
            "uptime_percent": None,
        }

    latency_values = [
        row[4]
        for row in rows
        if row[4] is not None
    ]

    packet_loss_values = [
        row[5]
        for row in rows
        if row[5] is not None
    ]

    healthy_count = sum(
        1
        for row in rows
        if bool(row[3])
    )

    sample_size = len(rows)

    average_latency = (
        sum(latency_values) / len(latency_values)
        if latency_values
        else None
    )

    minimum_latency = (
        min(latency_values)
        if latency_values
        else None
    )

    maximum_latency = (
        max(latency_values)
        if latency_values
        else None
    )

    average_packet_loss = (
        sum(packet_loss_values) / len(packet_loss_values)
        if packet_loss_values
        else None
    )

    uptime_percent = (
        healthy_count / sample_size
    ) * 100

    return {
        "sample_size": sample_size,
        "average_latency_ms": (
            round(average_latency, 1)
            if average_latency is not None
            else None
        ),
        "minimum_latency_ms": minimum_latency,
        "maximum_latency_ms": maximum_latency,
        "average_packet_loss": (
            round(average_packet_loss, 2)
            if average_packet_loss is not None
            else None
        ),
        "uptime_percent": round(
            uptime_percent,
            2,
        ),
    }

@app.get("/devices")
def devices():
    rows = get_devices()

    return {
        "count": len(rows),
        "devices": [
            device_to_dict(row)
            for row in rows
        ],
    }

if FRONTEND_DIST.exists():
    app.mount(
        "/assets",
        StaticFiles(
            directory=FRONTEND_DIST / "assets"
        ),
        name="frontend-assets",
    )


@app.get(
    "/dashboard",
    include_in_schema=False,
)
def dashboard():
    """Serve the NetWatch production dashboard."""

    index_file = FRONTEND_DIST / "index.html"

    if not index_file.exists():
        return {
            "error": (
                "Frontend has not been built. "
                "Run npm run build inside frontend."
            )
        }

    return FileResponse(index_file)