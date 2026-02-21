#!/usr/bin/env python3
"""Health monitor for Postiz Docker Compose stack."""

import argparse
import os
import sys
import time
from pathlib import Path

scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from health_checker import HealthChecker, HealthStatus
from health_notifier import HealthNotifier
from health_storage import HealthStorage

DEFAULT_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "60"))


def run_once(verbose: bool = False) -> int:
    """Run health checks once. Returns 0 if all healthy, 1 if unhealthy, 2 on error."""
    try:
        checker = HealthChecker()
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    storage = HealthStorage()
    notifier = HealthNotifier(storage)

    results = checker.check_all_services()
    all_healthy = True
    transitions = []

    for result in results:
        if verbose:
            icon = "+" if result.status == HealthStatus.HEALTHY else "x"
            print(f"  {icon} {result.service_name}: {result.status.value} ({result.response_time_ms}ms)")

        if result.status != HealthStatus.HEALTHY:
            all_healthy = False

        transition_id = notifier.process_result(result)
        if transition_id:
            transitions.append({"service": result.service_name, "status": result.status.value})

    if verbose and transitions:
        print(f"\nState transitions: {len(transitions)}")
        for t in transitions:
            print(f"  - {t['service']} -> {t['status']}")

    return 0 if all_healthy else 1


def run_continuous(interval: int = DEFAULT_INTERVAL, verbose: bool = False) -> int:
    """Run health checks continuously at specified interval."""
    try:
        checker = HealthChecker()
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    storage = HealthStorage()
    notifier = HealthNotifier(storage)

    print(f"Starting continuous health monitoring (interval: {interval}s)")

    try:
        while True:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            if verbose:
                print(f"[{timestamp}] Running health checks...")

            results = checker.check_all_services()
            for result in results:
                tid = notifier.process_result(result)
                if tid:
                    print(f"[{timestamp}] TRANSITION: {result.service_name} -> {result.status.value}")

            if verbose:
                print(f"[{timestamp}] Check complete")

            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopping health monitor")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Health monitor for Postiz Docker Compose stack")
    parser.add_argument("--once", action="store_true", help="Run checks once and exit")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help=f"Seconds between checks (default: {DEFAULT_INTERVAL})")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed output")
    args = parser.parse_args()

    if args.once:
        sys.exit(run_once(verbose=args.verbose))
    else:
        sys.exit(run_continuous(interval=args.interval, verbose=args.verbose))


if __name__ == "__main__":
    main()
