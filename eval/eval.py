"""
RepPath Eval Script
===================
Runs 10 test cases against the live /api/chat endpoint and scores each plan
on three sub-metrics:

  1. Structure    — all required JSON fields present, correct day count
  2. Goal alignment — rep ranges match the goal
  3. Hard rules   — no same movement pattern on consecutive days

Usage:
  python eval/eval.py

Requires the backend to be running at http://localhost:8000.
"""

import json
import time
import requests
from pathlib import Path

API_URL = "http://localhost:8000/api/chat"
CASES_PATH = Path(__file__).parent / "test_cases.json"

# Movement pattern keywords for back-to-back detection
SQUAT_PATTERNS = ["squat", "lunge", "leg press", "step up", "split squat"]
HINGE_PATTERNS = ["deadlift", "romanian", "rdl", "hip thrust", "kettlebell swing"]
PUSH_PATTERNS  = ["bench press", "push up", "overhead press", "dip", "chest press"]
PULL_PATTERNS  = ["row", "pull up", "pulldown", "chin up", "face pull"]

ALL_PATTERNS = {
    "squat": SQUAT_PATTERNS,
    "hinge": HINGE_PATTERNS,
    "push":  PUSH_PATTERNS,
    "pull":  PULL_PATTERNS,
}

DAYS_ORDER = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
]

# Rep range expectations by goal
# Strength max raised to 12 to allow accessories (8-12 reps per updated system prompt)
# Endurance min set to 8 — resistance exercises in endurance programs legitimately use 8-12 reps
GOAL_REP_RULES = {
    "strength":    {"max": 12},
    "hypertrophy": {"min": 6, "max": 20},
    "fat_loss":    {"min": 8},
    "endurance":   {"min": 8},
}

# Time-based units — skip these exercises in rep range checks
TIME_UNITS = ["second", "seconds", "minute", "minutes", "sec", "min", "s"]


def generate_plan(tc: dict) -> dict | None:
    """
    Simulate a complete intake conversation and return the generated plan.
    Sends a pre-built conversation history that mirrors what a user would type.
    """
    inp = tc["input"]
    messages = [
        {"role": "assistant", "content": "Hey! I'm RepPath. What's your primary goal?"},
        {"role": "user",      "content": f"My goal is {inp['goal'].replace('_', ' ')}"},
        {"role": "assistant", "content": "Got it. How many days per week can you train?"},
        {"role": "user",      "content": str(inp["days_per_week"])},
        {"role": "assistant", "content": "How long have you been training consistently?"},
        {"role": "user",      "content": inp["experience_level"]},
        {"role": "assistant", "content": "How long do you want this program — 4, 8, or 12 weeks?"},
        {"role": "user",      "content": str(inp["weeks"])},
        {"role": "assistant", "content": "Any injuries or movements to avoid?"},
        {"role": "user",      "content": ", ".join(inp["injuries"]) if inp["injuries"] else "no"},
        {"role": "assistant", "content": "What equipment do you have access to?"},
        {"role": "user",      "content": inp["equipment"]},
        {"role": "assistant", "content": "Here's your summary. Does this look right?"},
        {"role": "user",      "content": "yes"},
    ]

    try:
        resp = requests.post(API_URL, json={"messages": messages}, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data.get("plan")
    except Exception as e:
        print(f"  ERROR calling API: {e}")
        return None


def score_structure(plan: dict, expected: dict) -> tuple[float, list[str]]:
    """Check required fields and day count."""
    issues = []
    required = expected.get("required_fields", [])

    for field in required:
        if field not in plan:
            issues.append(f"Missing field: '{field}'")

    actual_days = len(plan.get("schedule", []))
    expected_days = expected.get("days_per_week", 0)
    if actual_days != expected_days:
        issues.append(f"Day count: expected {expected_days}, got {actual_days}")

    if plan.get("weeks") != expected.get("weeks"):
        issues.append(f"Weeks: expected {expected['weeks']}, got {plan.get('weeks')}")

    score = 1.0 if not issues else max(0.0, 1.0 - (len(issues) * 0.25))
    return score, issues


def score_goal_alignment(plan: dict, expected: dict) -> tuple[float, list[str]]:
    """Check that rep ranges match the goal."""
    issues = []
    goal = plan.get("goal", "")
    rules = GOAL_REP_RULES.get(goal, {})

    if not rules:
        return 1.0, []

    violations = 0
    total = 0

    for day in plan.get("schedule", []):
        if not isinstance(day, dict):
            continue
        for ex in day.get("exercises", []):
            if not isinstance(ex, dict):
                continue
            reps_str = str(ex.get("reps", ""))

            # Skip time-based exercises — duration is not a rep count
            if any(unit in reps_str.lower() for unit in TIME_UNITS):
                continue

            try:
                first_num = int(reps_str.split("-")[0].split()[0])
            except (ValueError, IndexError):
                continue

            total += 1
            if "max" in rules and first_num > rules["max"]:
                issues.append(
                    f"{ex.get('name', '?')}: {reps_str} reps exceeds max {rules['max']} for {goal}"
                )
                violations += 1
            if "min" in rules and first_num < rules["min"]:
                issues.append(
                    f"{ex.get('name', '?')}: {reps_str} reps below min {rules['min']} for {goal}"
                )
                violations += 1

    score = 1.0 if total == 0 else max(0.0, 1.0 - (violations / total))
    return round(score, 2), issues


def score_hard_rules(plan: dict, expected: dict) -> tuple[float, list[str]]:
    """Check no same movement pattern appears on consecutive days."""
    issues = []

    schedule = plan.get("schedule", [])
    day_patterns: dict[str, set] = {}

    for day_data in schedule:
        if not isinstance(day_data, dict):
            continue
        day = day_data.get("day", "")
        if not day:
            continue
        patterns_today = set()
        for ex in day_data.get("exercises", []):
            if not isinstance(ex, dict):
                continue
            name_lower = ex.get("name", "").lower()
            for pattern_name, keywords in ALL_PATTERNS.items():
                if any(kw in name_lower for kw in keywords):
                    patterns_today.add(pattern_name)
        day_patterns[day] = patterns_today

    # Check truly consecutive calendar days (not just adjacent training days)
    # Monday/Wednesday with a rest day Tuesday is NOT a violation
    for i in range(len(DAYS_ORDER) - 1):
        d1, d2 = DAYS_ORDER[i], DAYS_ORDER[i + 1]
        if d1 in day_patterns and d2 in day_patterns:
            overlap = day_patterns[d1] & day_patterns[d2]
            if overlap:
                issues.append(
                    f"Back-to-back pattern violation: {overlap} on {d1} and {d2}"
                )

    score = 1.0 if not issues else 0.0
    return score, issues


def run_eval():
    cases = json.loads(CASES_PATH.read_text())
    results = []

    print(f"\n{'='*60}")
    print("RepPath Eval — Composite Score")
    print(f"{'='*60}\n")

    for tc in cases:
        print(f"[{tc['id']}] {tc['description']}")
        plan = generate_plan(tc)

        if plan is None:
            print("  ✗ No plan returned — skipping\n")
            results.append({
                "id": tc["id"],
                "description": tc["description"],
                "structure": 0.0,
                "goal_alignment": 0.0,
                "hard_rules": 0.0,
                "composite": 0.0,
                "error": "No plan returned"
            })
            continue

        s_score, s_issues = score_structure(plan, tc["expected"])
        g_score, g_issues = score_goal_alignment(plan, tc["expected"])
        h_score, h_issues = score_hard_rules(plan, tc["expected"])
        composite = round((s_score + g_score + h_score) / 3, 2)

        print(f"  Structure:     {s_score:.2f}  {s_issues if s_issues else '✓'}")
        print(f"  Goal align:    {g_score:.2f}  {g_issues[:2] if g_issues else '✓'}")
        print(f"  Hard rules:    {h_score:.2f}  {h_issues if h_issues else '✓'}")
        print(f"  Composite:     {composite:.2f}\n")

        results.append({
            "id": tc["id"],
            "description": tc["description"],
            "structure": s_score,
            "goal_alignment": g_score,
            "hard_rules": h_score,
            "composite": composite,
            "issues": s_issues + g_issues + h_issues
        })

        time.sleep(4)  # avoid rate limiting

    # Summary
    avg_structure = sum(r["structure"] for r in results) / len(results)
    avg_goal = sum(r["goal_alignment"] for r in results) / len(results)
    avg_hard = sum(r["hard_rules"] for r in results) / len(results)
    avg_composite = sum(r["composite"] for r in results) / len(results)

    print(f"{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"  Structure avg:      {avg_structure:.2f}")
    print(f"  Goal alignment avg: {avg_goal:.2f}")
    print(f"  Hard rules avg:     {avg_hard:.2f}")
    print(f"  COMPOSITE AVG:      {avg_composite:.2f}  (n={len(results)})")
    print(f"{'='*60}\n")

    # Save results
    out_path = Path(__file__).parent / "results.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"Results saved to {out_path}\n")


if __name__ == "__main__":
    run_eval()