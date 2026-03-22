#!/usr/bin/env python3
"""
eval_runner.py — Nexus S5 Evaluation Runner
=============================================
Runs 25 assertions from eval.json and reports a pass/fail score.

Usage:
  python eval/eval_runner.py                    # run all assertions
  python eval/eval_runner.py --category ingest  # run one category
  python eval/eval_runner.py --telegram         # send results to Telegram
  python eval/eval_runner.py --fail-fast        # stop on first failure

Exit codes: 0 = all passed, 1 = some failed
"""
import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional

# Repo root is two levels up from eval/
REPO_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT / "scanners"))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
logger = logging.getLogger("eval_runner")


# ── Assertion executors ───────────────────────────────────────────────────────

def run_file_exists(assertion: dict) -> tuple[bool, str]:
    """Check that a file exists in the repo."""
    rel_path = assertion["file"]
    full_path = REPO_ROOT / rel_path
    if full_path.exists():
        return True, f"{rel_path} ✓"
    return False, f"{rel_path} NOT FOUND"


def run_file_contains(assertion: dict) -> tuple[bool, str]:
    """Check that a file contains a specific string."""
    rel_path  = assertion["file"]
    needle    = assertion["contains"]
    full_path = REPO_ROOT / rel_path

    if not full_path.exists():
        return False, f"{rel_path} NOT FOUND"

    content = full_path.read_text(encoding="utf-8", errors="ignore")
    if needle in content:
        return True, f"'{needle}' found in {rel_path} ✓"
    return False, f"'{needle}' NOT found in {rel_path}"


def run_python_logic(assertion: dict) -> tuple[bool, str]:
    """
    Import a module and call a function with kwargs, compare output.
    Supports:
      - expected: exact match
      - expected_hours: for datetime results, check timedelta within tolerance
    """
    module_name = assertion["module"]
    func_name   = assertion["function"]
    kwargs      = assertion.get("kwargs", {})

    try:
        import importlib
        mod  = importlib.import_module(module_name)
        func = getattr(mod, func_name)
        result = func(**kwargs)
    except Exception as e:
        return False, f"Import/call error: {e}"

    # Exact string match
    if "expected" in assertion:
        expected = assertion["expected"]
        if result == expected:
            return True, f"{func_name}({kwargs}) = '{result}' ✓"
        return False, f"{func_name}({kwargs}) = '{result}', expected '{expected}'"

    # Datetime/hours check — result should be ~N hours from now
    if "expected_hours" in assertion:
        hours = assertion["expected_hours"]
        if not hasattr(result, "utcoffset"):
            return False, f"Result is not a datetime: {type(result)}"
        now = datetime.now(timezone.utc)
        expected_dt = now + timedelta(hours=hours)
        diff_seconds = abs((result - expected_dt).total_seconds())
        tolerance = 60  # 1 minute tolerance
        if diff_seconds <= tolerance:
            return True, f"{func_name} deadline ≈ {hours}h from now ✓"
        return False, f"{func_name} deadline diff = {diff_seconds:.0f}s (expected ~{hours*3600}s)"

    return False, f"Unknown assertion type — no 'expected' or 'expected_hours' key"


# ── Runner ────────────────────────────────────────────────────────────────────

def run_assertion(assertion: dict) -> dict:
    """Run a single assertion and return a result dict."""
    a_id      = assertion["id"]
    category  = assertion["category"]
    desc      = assertion["description"]
    a_type    = assertion["type"]

    start = time.monotonic()

    try:
        if a_type == "file_exists":
            passed, detail = run_file_exists(assertion)
        elif a_type == "file_contains":
            passed, detail = run_file_contains(assertion)
        elif a_type == "python_logic":
            passed, detail = run_python_logic(assertion)
        else:
            passed, detail = False, f"Unknown assertion type: {a_type}"
    except Exception as e:
        passed, detail = False, f"Runner error: {e}"

    elapsed = time.monotonic() - start

    return {
        "id":       a_id,
        "category": category,
        "description": desc,
        "passed":   passed,
        "detail":   detail,
        "elapsed_ms": round(elapsed * 1000, 1),
    }


def run_all(
    assertions: list,
    category_filter: Optional[str] = None,
    fail_fast: bool = False,
) -> list:
    results = []
    for a in assertions:
        if category_filter and a["category"] != category_filter:
            continue
        r = run_assertion(a)
        results.append(r)
        status = "PASS" if r["passed"] else "FAIL"
        mark   = "✅" if r["passed"] else "❌"
        print(f"  {mark} [{r['id']}] {r['description']}")
        if not r["passed"]:
            print(f"       └─ {r['detail']}")
        if fail_fast and not r["passed"]:
            break
    return results


# ── Scoring ───────────────────────────────────────────────────────────────────

def compute_score(results: list, categories: dict) -> dict:
    """Compute weighted score per category and overall."""
    by_cat: dict[str, list] = {}
    for r in results:
        by_cat.setdefault(r["category"], []).append(r)

    cat_scores = {}
    total_weight   = 0
    weighted_score = 0.0

    for cat, meta in categories.items():
        cat_results = by_cat.get(cat, [])
        if not cat_results:
            cat_scores[cat] = {"pass": 0, "total": 0, "pct": 0, "weight": meta["weight"]}
            continue
        passed = sum(1 for r in cat_results if r["passed"])
        total  = len(cat_results)
        pct    = passed / total * 100
        cat_scores[cat] = {
            "pass": passed, "total": total, "pct": pct, "weight": meta["weight"]
        }
        weight = meta["weight"]
        total_weight   += weight
        weighted_score += pct * weight

    overall = weighted_score / total_weight if total_weight > 0 else 0
    total_pass  = sum(1 for r in results if r["passed"])
    total_count = len(results)

    return {
        "overall_pct":  round(overall, 1),
        "pass":         total_pass,
        "total":        total_count,
        "categories":   cat_scores,
        "pass_rate":    f"{total_pass}/{total_count}",
    }


# ── Report ────────────────────────────────────────────────────────────────────

def print_report(score: dict, results: list):
    print("\n" + "═" * 55)
    print("  NEXUS S5 EVAL REPORT")
    print("═" * 55)
    print(f"  Score:     {score['overall_pct']}%  ({score['pass_rate']} assertions passed)")
    print(f"  Threshold: 80%")
    passed = score["overall_pct"] >= 80
    print(f"  Status:    {'✅ PASS' if passed else '❌ FAIL — below 80% threshold'}")
    print()
    print("  By category:")
    for cat, s in score["categories"].items():
        bar = "█" * int(s["pct"] / 10) + "░" * (10 - int(s["pct"] / 10))
        print(f"  {cat:15s} {bar} {s['pct']:5.1f}%  ({s['pass']}/{s['total']})")
    print("═" * 55)

    # List failures
    failures = [r for r in results if not r["passed"]]
    if failures:
        print(f"\n  ❌ Failures ({len(failures)}):")
        for r in failures:
            print(f"    [{r['id']}] {r['description']}")
            print(f"         {r['detail']}")
    else:
        print("\n  🎉 All assertions passed!")
    print()


def format_telegram_report(score: dict, results: list) -> str:
    now_str  = datetime.now(timezone.utc).strftime("%b %d %H:%M UTC")
    passed   = score["overall_pct"] >= 80
    verdict  = "✅ PASS" if passed else "❌ FAIL"
    failures = [r for r in results if not r["passed"]]

    cat_lines = []
    for cat, s in score["categories"].items():
        emoji = "✅" if s["pct"] == 100 else ("⚠️" if s["pct"] >= 60 else "❌")
        cat_lines.append(f"  {emoji} {cat}: {s['pct']:.0f}% ({s['pass']}/{s['total']})")

    fail_section = ""
    if failures:
        fail_lines = "\n".join(f"  ❌ [{r['id']}] {r['description']}" for r in failures[:8])
        fail_section = f"\n\n<b>Failures:</b>\n{fail_lines}"
        if len(failures) > 8:
            fail_section += f"\n  … and {len(failures)-8} more"

    return (
        f"🧪 <b>NEXUS EVAL REPORT</b> — {now_str}\n\n"
        f"Score: <b>{score['overall_pct']}%</b>  ({score['pass_rate']})\n"
        f"Status: <b>{verdict}</b>\n\n"
        f"<b>By category:</b>\n"
        + "\n".join(cat_lines)
        + fail_section
        + f"\n\n🔗 https://nexus.zonewise.ai"
    )[:4096]


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Nexus S5 Eval Runner")
    parser.add_argument("--category", "-c", help="Run only one category")
    parser.add_argument("--telegram", "-t", action="store_true", help="Send results to Telegram")
    parser.add_argument("--fail-fast", "-f", action="store_true", help="Stop on first failure")
    parser.add_argument("--output", "-o", help="Write JSON results to file")
    parser.add_argument(
        "--eval-file",
        default=str(Path(__file__).parent / "eval.json"),
        help="Path to eval.json",
    )
    args = parser.parse_args()

    # Load eval config
    with open(args.eval_file) as f:
        config = json.load(f)

    assertions = config["assertions"]
    categories = config["categories"]

    print(f"\n🧪 Nexus S5 Eval — {len(assertions)} assertions")
    if args.category:
        print(f"   Category filter: {args.category}")
    print()

    # Run
    results = run_all(assertions, category_filter=args.category, fail_fast=args.fail_fast)

    # Score
    score = compute_score(results, categories)
    print_report(score, results)

    # Optional JSON output
    if args.output:
        output_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "score":     score,
            "results":   results,
        }
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2, default=str)
        print(f"  Results written to {args.output}")

    # Optional Telegram
    if args.telegram:
        try:
            from notifier import send_telegram
            text = format_telegram_report(score, results)
            ok   = send_telegram(text)
            print(f"  Telegram: {'sent ✓' if ok else 'failed ✗'}")
        except Exception as e:
            print(f"  Telegram failed: {e}")

    # Exit code
    passed = score["overall_pct"] >= 80
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
