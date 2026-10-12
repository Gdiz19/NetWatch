import re
import socket
import subprocess
import time
from datetime import datetime

from database import (
    end_outage,
    get_open_outage,
    initialize_database,
    save_measurement,
    start_outage,
)


CHECK_INTERVAL_SECONDS = 30


def get_default_gateway():
    """Find the active default IPv4 gateway on Windows."""

    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            "Get-NetIPConfiguration | "
            "Where-Object { $_.IPv4DefaultGateway -ne $null } | "
            "Select-Object -First 1 "
            "-ExpandProperty IPv4DefaultGateway | "
            "Select-Object -ExpandProperty NextHop"
        ),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    gateway = result.stdout.strip()

    if gateway:
        return gateway

    return None


def ping_host(host, count=4):
    """Ping a host and return status, latency, and packet loss."""

    result = subprocess.run(
        [
            "ping",
            "-n",
            str(count),
            "-w",
            "1000",
            host,
        ],
        capture_output=True,
        text=True,
        errors="ignore",
    )

    output = result.stdout

    loss_match = re.search(
        r"\((\d+)% loss\)",
        output,
        re.IGNORECASE,
    )

    latency_match = re.search(
        r"Average = (\d+)ms",
        output,
        re.IGNORECASE,
    )

    packet_loss = (
        int(loss_match.group(1))
        if loss_match
        else 100
    )

    latency = (
        int(latency_match.group(1))
        if latency_match
        else None
    )

    return {
        "online": packet_loss < 100,
        "latency_ms": latency,
        "packet_loss": packet_loss,
    }


def check_dns():
    """Check whether DNS can resolve a domain name."""

    try:
        ip_address = socket.gethostbyname("example.com")

        return {
            "working": True,
            "resolved_ip": ip_address,
        }

    except socket.gaierror:
        return {
            "working": False,
            "resolved_ip": None,
        }


def display_ping_result(name, result):
    """Print a ping result."""

    status = (
        "ONLINE"
        if result["online"]
        else "OFFLINE"
    )

    if result["latency_ms"] is not None:
        latency = f'{result["latency_ms"]} ms'
    else:
        latency = "N/A"

    print(
        f"{name:<10}"
        f"{status:<10}"
        f"Latency: {latency:<10}"
        f"Loss: {result['packet_loss']}%"
    )


def update_outage_status(internet_online):
    """Start or resolve an outage based on internet state."""

    open_outage = get_open_outage()

    if not internet_online and open_outage is None:
        outage_id = start_outage()

        print()
        print("!!! INTERNET OUTAGE DETECTED !!!")
        print(f"Outage ID: {outage_id}")

    elif internet_online and open_outage is not None:
        resolved = end_outage()

        duration = round(
            resolved["duration_seconds"],
            1,
        )

        print()
        print("*** INTERNET CONNECTION RESTORED ***")
        print(
            f"Outage duration: "
            f"{duration} seconds"
        )


def run_health_check():
    """Run one complete network health check."""

    timestamp = datetime.now().astimezone()

    print()
    print("=" * 65)
    print(
        "NetWatch Check - "
        f"{timestamp.strftime('%Y-%m-%d %I:%M:%S %p')}"
    )
    print("=" * 65)

    gateway = get_default_gateway()

    if gateway:
        router_result = ping_host(gateway)

        display_ping_result(
            "Router:",
            router_result,
        )

        save_measurement(
            check_type="router",
            target=gateway,
            is_healthy=router_result["online"],
            latency_ms=router_result["latency_ms"],
            packet_loss=router_result["packet_loss"],
        )

    else:
        print("Router:   Gateway could not be detected")

    internet_target = "1.1.1.1"

    internet_result = ping_host(
        internet_target
    )

    display_ping_result(
        "Internet:",
        internet_result,
    )

    save_measurement(
        check_type="internet",
        target=internet_target,
        is_healthy=internet_result["online"],
        latency_ms=internet_result["latency_ms"],
        packet_loss=internet_result["packet_loss"],
    )

    dns_result = check_dns()

    if dns_result["working"]:
        print(
            f"{'DNS:':<10}"
            f"{'WORKING':<10}"
            f"example.com -> "
            f"{dns_result['resolved_ip']}"
        )

    else:
        print(
            f"{'DNS:':<10}"
            f"{'FAILED':<10}"
        )

    save_measurement(
        check_type="dns",
        target="example.com",
        is_healthy=dns_result["working"],
        details=dns_result["resolved_ip"],
    )

    update_outage_status(
        internet_result["online"]
    )


def main():
    initialize_database()

    print()
    print("NetWatch Continuous Monitor")
    print(
        f"Checking network every "
        f"{CHECK_INTERVAL_SECONDS} seconds."
    )
    print("Press Ctrl+C to stop NetWatch.")

    try:
        while True:
            start_time = time.monotonic()

            run_health_check()

            elapsed = (
                time.monotonic()
                - start_time
            )

            sleep_time = max(
                0,
                CHECK_INTERVAL_SECONDS - elapsed,
            )

            print()
            print(
                f"Next check in "
                f"{round(sleep_time)} seconds..."
            )

            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print()
        print()
        print("NetWatch stopped.")


if __name__ == "__main__":
    main()