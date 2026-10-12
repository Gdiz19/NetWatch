import re
import socket
import subprocess


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
    """Ping a host and return its status, latency, and packet loss."""

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
    """Print a ping result in a readable format."""

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


def main():
    print()
    print("NetWatch - Network Health Check")
    print("-" * 60)

    gateway = get_default_gateway()

    if gateway:
        print(f"Gateway:   {gateway}")
        print()

        router_result = ping_host(gateway)

        display_ping_result(
            "Router:",
            router_result,
        )

    else:
        print("Gateway:   Unable to detect")
        print()

    internet_result = ping_host("1.1.1.1")

    display_ping_result(
        "Internet:",
        internet_result,
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

    print("-" * 60)
    print()


if __name__ == "__main__":
    main()