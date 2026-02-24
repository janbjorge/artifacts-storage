from __future__ import annotations

import os
import statistics
import sys
from itertools import groupby

from models import BenchmarkResult
from utils import benchmark_loader

# ANSI color codes for terminal output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def compare_with_dev_branch() -> None:
    """
    Compare benchmark results between the main branch and the current branch.
    Exit with status 1 if the latest benchmark rate from the current branch is
    lower than the threshold.
    """
    branch_name = os.getenv("REF_NAME", "main")
    exit_status = 0

    all_results = sorted(
        (x for _, x in benchmark_loader()),
        key=lambda x: (x.driver, x.strategy),
    )

    for (driver, strategy), group in groupby(
        all_results,
        key=lambda x: (x.driver, x.strategy),
    ):
        results = list(group)
        main = [r for r in results if r.github_ref_name == "main"]
        other = [r for r in results if r.github_ref_name == branch_name]

        if main and other:
            median = statistics.median([r.rate for r in main]) * 0.9
            threshold = median * 0.9
            latest_other_rate = max(other, key=lambda x: x.created_at).rate

            # Determine if check passed or failed
            check_passed = latest_other_rate >= threshold
            status_indicator = (
                f"{GREEN}✓ PASS{RESET}" if check_passed else f"{RED}✗ FAIL{RESET}"
            )

            print(f"{BOLD}Driver: {driver} ({strategy}){RESET} {status_indicator}")
            print(
                f"Main branch median rate: {median:.1f} | "
                f"Threshold (90% of median): {threshold:.1f}"
            )
            print(f"Latest rate ({branch_name} branch): {latest_other_rate:.1f}")
            print("-" * 40)

            if latest_other_rate < threshold:
                exit_status = 1

    sys.exit(exit_status)


if __name__ == "__main__":
    print("Loading and comparing benchmark results...")
    compare_with_dev_branch()
