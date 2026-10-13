import re
import socket
import subprocess
import time
import ipaddress
import json
from datetime import datetime

from backend.database import (
    end_outage,
    get_open_outage,
    initialize_database,
    save_measurement,
    start_outage,
    save_device,
)

NO_WINDOW = getattr(
    subprocess,
    "CREATE_NO_WINDOW",
    0,
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
        creationflags=NO_WINDOW,
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
        creationflags=NO_WINDOW,
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

def discover_local_devices():
    """Read Windows' local IPv4 neighbor table."""

    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            "Get-NetNeighbor -AddressFamily IPv4 | "
            "Where-Object { "
            "$_.LinkLayerAddress -and "
            "$_.LinkLayerAddress -ne '00-00-00-00-00-00' -and "
            "$_.State -ne 'Permanent' "
            "} | "
            "Select-Object "
            "IPAddress,LinkLayerAddress,State,InterfaceAlias | "
            "ConvertTo-Json -Compress"
        ),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        creationflags=NO_WINDOW,
    )

    output = result.stdout.strip()

    if not output:
        return []

    try:
        raw_devices = json.loads(output)
    except json.JSONDecodeError:
        return []

    if isinstance(raw_devices, dict):
        raw_devices = [raw_devices]

    devices = []

    for device in raw_devices:
        ip_text = device.get("IPAddress")

        try:
            ip = ipaddress.ip_address(ip_text)
        except ValueError:
            continue

        if (
            not ip.is_private
            or ip.is_loopback
            or ip.is_multicast
            or ip.is_link_local
        ):
            continue

        devices.append(
            {
                "ip_address": ip_text,
                "mac_address": device.get(
                    "LinkLayerAddress"
                ),
                "neighbor_state": device.get(
                    "State"
                ),
                "interface_alias": device.get(
                    "InterfaceAlias"
                ),
            }
        )

    return devices

def check_local_devices():
    """Discover local devices and update their status."""

    devices = discover_local_devices()

    responding_count = 0

    for device in devices:
        ping_result = ping_host(
            device["ip_address"],
            count=1,
        )

        is_online = ping_result["online"]

        if is_online:
            responding_count += 1

        save_device(
            ip_address=device["ip_address"],
            mac_address=device["mac_address"],
            interface_alias=device["interface_alias"],
            neighbor_state=device["neighbor_state"],
            is_online=is_online,
        )

    print(
        f"Devices:   {len(devices)} discovered, "
        f"{responding_count} responding"
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

    check_local_devices()


def run_monitor_loop(stop_event=None):
    """Continuously monitor the network until stopped."""

    initialize_database()

    print()
    print("NetWatch Continuous Monitor")
    print(
        f"Checking network every "
        f"{CHECK_INTERVAL_SECONDS} seconds."
    )

    try:
        while (
            stop_event is None
            or not stop_event.is_set()
        ):
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

            if stop_event is None:
                time.sleep(sleep_time)

            else:
                if stop_event.wait(sleep_time):
                    break

    except KeyboardInterrupt:
        pass

    print()
    print("NetWatch monitoring stopped.")


def main():
    run_monitor_loop()


if __name__ == "__main__":
    main()