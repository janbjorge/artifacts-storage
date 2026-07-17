from __future__ import annotations

import os
import statistics
import sys
from itertools import groupby

from utils import benchmark_loader

# ANSI color codes for terminal output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Ratios of the baseline median. Calibrated by a backtest over the full
# history (~15k samples): single runs are too noisy to gate on (1% land
# below 0.28x the window median), but the median of the newest 3 samples
# against the 0.7 ratio produced ~11 isolated false flags across two
# years while catching every sustained regression.
FAIL_RATIO = 0.7
WARN_RATIO = 0.8
CURRENT_SAMPLES = 3
WINDOW_SIZE = 30
MIN_SAMPLES = 5


def compare_with_main() -> None:
    """
    Gate the median of the newest benchmark samples against the median of
    the preceding main-branch window, per (driver, strategy) pair.
    Exit with status 1 if any pair falls below FAIL_RATIO of its baseline.
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
        main = sorted(
            (r for r in results if r.github_ref_name == "main"),
            key=lambda x: x.created_at,
        )

        if branch_name != "main":
            other = sorted(
                (r for r in results if r.github_ref_name == branch_name),
                key=lambda x: x.created_at,
            )
            current = other[-CURRENT_SAMPLES:]
            baseline = main[-WINDOW_SIZE:]
        else:
            # Main run: gate the newest samples against the window before them.
            current = main[-CURRENT_SAMPLES:]
            baseline = main[:-CURRENT_SAMPLES][-WINDOW_SIZE:]

        if not current or len(baseline) < MIN_SAMPLES:
            continue

        current_rate = statistics.median([r.rate for r in current])
        baseline_median = statistics.median([r.rate for r in baseline])
        fail_threshold = baseline_median * FAIL_RATIO
        warn_threshold = baseline_median * WARN_RATIO

        if current_rate < fail_threshold:
            status_indicator = f"{RED}✗ FAIL{RESET}"
            exit_status = 1
        elif current_rate < warn_threshold:
            status_indicator = f"{YELLOW}⚠ WARN{RESET}"
        else:
            status_indicator = f"{GREEN}✓ PASS{RESET}"

        print(f"{BOLD}Driver: {driver} ({strategy}){RESET} {status_indicator}")
        print(
            f"Baseline (n={len(baseline)}): median {baseline_median:.1f} | "
            f"warn < {warn_threshold:.1f} | fail < {fail_threshold:.1f}"
        )
        print(
            f"Current rate ({branch_name}, median of {len(current)} samples): "
            f"{current_rate:.1f}"
        )
        print("-" * 40)

    sys.exit(exit_status)


if __name__ == "__main__":
    print("Loading and comparing benchmark results...")
    compare_with_main()
