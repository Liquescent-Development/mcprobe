# Stability Checking

Comprehensive guide to checking scenario stability in MCProbe, including detailed metrics, interpretation, and best practices.

## Overview

The stability check provides detailed analysis of a **single scenario's consistency** over time. Unlike flaky detection which checks all scenarios, stability checking gives you deep insights into one specific scenario's behavior.

**Key capabilities:**
- Pass rate calculation
- Score mean and standard deviation
- Coefficient of variation analysis
- Explicit stability determination
- Minimum run enforcement

**When to use:**
- Investigating specific scenario issues
- Validating fixes to flaky tests
- Pre-deployment verification of critical scenarios
- Establishing baseline metrics

## What Stability Check Measures

### Core Metrics

The stability check returns the following metrics:

```python
{
    "scenario_name": str,           # Scenario being analyzed
    "run_count": int,               # Number of historical runs
    "pass_rate": float,             # Percentage that passed (0.0-1.0)
    "mean_score": float,            # Average score across runs
    "score_std": float,             # Standard deviation of scores
    "is_stable": bool,              # Overall stability determination
    "reasons": list[str]            # Explanation of stability status
}
```

### Metric Definitions

**scenario_name**
- Name of the scenario being analyzed
- Must match exactly (case-sensitive)

**run_count**
- Total number of times scenario has been executed
- Used to determine if enough data exists for analysis
- Minimum required: configurable (default 5)

**pass_rate**
- Percentage of runs where all correctness criteria passed
- Range: 0.0 (0%) to 1.0 (100%)
- Formula: `passed_count / total_count`

**mean_score**
- Average score across all runs (both passing and failing)
- Range: 0.0 to 1.0
- Higher is better

**score_std**
- Standard deviation of scores
- Measures score consistency
- Lower is more consistent
- Range: 0.0+ (no upper limit, but typically < 0.3)

**is_stable**
- Overall stability determination (True/False/None)
- True: Scenario is stable
- False: Scenario is unstable (flaky)
- None: Insufficient data for determination

**reasons**
- Human-readable explanations
- Lists specific stability issues or confirms stability
- Example: `["Unstable pass rate: 65%", "High score variance: CV=18%"]`

## Stability Criteria

A scenario is considered **stable** if it meets ALL of the following:

### 1. Pass Rate Stability

Pass rate must be outside the flaky range:

```python
# From mcprobe/analysis/flaky.py
STABILITY_PASS_RATE_HIGH = 0.95  # Above this = stable
STABILITY_PASS_RATE_LOW = 0.05   # Below this = stable (consistently failing)
```

**Stable pass rates:**
- **≥ 95%**: Consistently passing (good)
- **≤ 5%**: Consistently failing (bad, but stable)

**Unstable pass rates:**
- **5% - 95%**: In flaky range (inconsistent)

**Why this range?**
- A scenario that always fails (< 5%) is stable, just broken
- A scenario that mostly passes (> 95%) is reliably working
- Anything in between is unpredictable

**Examples:**

| Pass Rate | Stable? | Interpretation |
|-----------|---------|----------------|
| 100% | ✅ Yes | Perfect stability |
| 97% | ✅ Yes | Highly reliable |
| 85% | ❌ No | Flaky - sometimes fails |
| 50% | ❌ No | Completely unreliable |
| 15% | ❌ No | Flaky - sometimes passes |
| 3% | ✅ Yes | Consistently failing (fix the scenario!) |
| 0% | ✅ Yes | Always fails (broken, but predictable) |

### 2. Score Consistency (Coefficient of Variation)

Score variance must be low relative to the mean:

```python
# From mcprobe/analysis/flaky.py
STABILITY_CV_THRESHOLD = 0.15
```

**Coefficient of Variation (CV)** = `score_std / mean_score`

**Stable scores:**
- **CV ≤ 0.15**: Consistent quality

**Unstable scores:**
- **CV > 0.15**: High variance in quality

**Interpreting CV values:**

| CV | Status | Interpretation | Example Scores |
|----|--------|----------------|----------------|
| < 0.05 | Excellent | Very consistent | 0.90, 0.91, 0.89, 0.90, 0.92 |
| 0.05-0.10 | Good | Minor variation | 0.85, 0.88, 0.90, 0.87, 0.84 |
| 0.10-0.15 | Acceptable | Moderate variation | 0.80, 0.88, 0.85, 0.92, 0.78 |
| **> 0.15** | **Unstable** | **High variation** | **0.70, 0.95, 0.75, 0.90, 0.68** |

**Calculation example:**
```
Scores: [0.88, 0.91, 0.87, 0.89, 0.90]
Mean: 0.89
Std Dev: 0.015
CV: 0.015 / 0.89 = 0.017 (1.7%)
Status: Stable (CV < 0.15)
```

### Combined Stability Determination

Both criteria must be met for stability:

```python
is_stable = True
reasons = []

# Check pass rate
if 0.05 < pass_rate < 0.95:
    is_stable = False
    reasons.append(f"Unstable pass rate: {pass_rate:.0%}")

# Check score variance
cv = score_std / mean_score
if cv > 0.15:
    is_stable = False
    reasons.append(f"High score variance: CV={cv:.0%}")

if is_stable:
    reasons = ["Scenario is stable"]
```

## CLI Usage

### Basic Usage

```bash
# Check stability of a scenario
mcprobe stability-check "Scenario Name"

# Require more runs for analysis
mcprobe stability-check "Scenario Name" --min-runs 10

# Custom results directory
mcprobe stability-check "Scenario Name" --results-dir ./my-results
```

**Important:** Scenario name must match exactly (case-sensitive).

### Output Examples

#### Stable Scenario

```bash
$ mcprobe stability-check "Weather Query Test"
```

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Stability Check: Weather Query Test ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Run Count          15
Pass Rate         100%
Mean Score        0.95
Score Std Dev     0.023

✓ Scenario is stable
```

**Interpretation:**
- 15 runs is sufficient for analysis
- 100% pass rate (well above 95% threshold)
- Mean score 0.95 is excellent
- Std dev 0.023 is very low
- CV = 0.023 / 0.95 = 0.024 (2.4%, well below 15% threshold)
- **Result: Stable and high quality**

#### Unstable Scenario (Pass Rate)

```bash
$ mcprobe stability-check "API Authentication"
```

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Stability Check: API Authentication ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Run Count          12
Pass Rate          67%
Mean Score         0.78
Score Std Dev      0.145

✗ Scenario is unstable
  - Unstable pass rate: 67%
```

**Interpretation:**
- 67% pass rate is in the flaky range (5%-95%)
- Sometimes passes, sometimes fails
- **Result: Unstable - fix pass/fail inconsistency**

#### Unstable Scenario (Score Variance)

```bash
$ mcprobe stability-check "Complex Workflow"
```

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Stability Check: Complex Workflow ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Run Count          18
Pass Rate          94%
Mean Score         0.82
Score Std Dev      0.165

✗ Scenario is unstable
  - High score variance: CV=20%
```

**Interpretation:**
- Pass rate 94% is acceptable (but close to threshold)
- CV = 0.165 / 0.82 = 0.201 (20.1%)
- CV > 15% threshold indicates inconsistent quality
- **Result: Unstable - reduce score variance**

#### Multiple Issues

```bash
$ mcprobe stability-check "Flaky Test"
```

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Stability Check: Flaky Test ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Run Count          20
Pass Rate          55%
Mean Score         0.68
Score Std Dev      0.182

✗ Scenario is unstable
  - Unstable pass rate: 55%
  - High score variance: CV=27%
```

**Interpretation:**
- Both criteria failing
- 55% pass rate = coin flip behavior
- CV = 27% = very inconsistent scores
- **Result: Severely unstable - high priority fix**

#### Insufficient Data

```bash
$ mcprobe stability-check "New Test"
```

```
┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Stability Check: New Test ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━┛

Insufficient data for stability analysis
Run count: 3 (need at least 5)
```

**Interpretation:**
- Only 3 runs exist
- Need at least 5 for statistical significance
- **Action: Run scenario 2+ more times**

#### Consistently Failing (but Stable)

```bash
$ mcprobe stability-check "Broken Test"
```

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Stability Check: Broken Test ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━┛

Run Count          10
Pass Rate           0%
Mean Score         0.42
Score Std Dev      0.035

✓ Scenario is stable
```

**Interpretation:**
- 0% pass rate is "stable" (consistently failing)
- Low score variance (CV = 8.3%)
- **Result: Stable but broken - fix the test or code**

## Interpreting Results

### Pass Rate Interpretation

| Pass Rate | Status | Action Required |
|-----------|--------|-----------------|
| 100% | Excellent | None - maintain quality |
| 95-99% | Very Good | Monitor occasional failures |
| **90-94%** | **Borderline** | **Investigate - close to unstable** |
| **5-89%** | **Unstable** | **Fix immediately - unreliable** |
| 1-4% | Consistently Failing | Fix scenario or code |
| 0% | Always Fails | Fix scenario or code |

### Mean Score Interpretation

| Mean Score | Quality | Interpretation |
|------------|---------|----------------|
| 0.95-1.00 | Excellent | Outstanding performance |
| 0.90-0.94 | Very Good | High quality, minor issues |
| 0.80-0.89 | Good | Acceptable, room for improvement |
| 0.70-0.79 | Fair | Needs improvement |
| 0.60-0.69 | Poor | Significant issues |
| < 0.60 | Very Poor | Critical issues |

### Score Standard Deviation Interpretation

| Std Dev | Consistency | Interpretation |
|---------|-------------|----------------|
| < 0.05 | Excellent | Very consistent results |
| 0.05-0.10 | Good | Minor variation |
| 0.10-0.15 | Fair | Moderate variation |
| **> 0.15** | **Poor** | **High variation (if mean > 0)** |

**Note:** Standard deviation alone can be misleading. A mean score of 0.5 with std dev of 0.1 is more concerning than mean 0.9 with std dev 0.1. That's why we use CV (std/mean).

### Coefficient of Variation Interpretation

| CV | Status | Action |
|----|--------|--------|
| < 0.05 | Excellent | None - very stable |
| 0.05-0.10 | Good | Normal variation, acceptable |
| 0.10-0.15 | Acceptable | Monitor for increases |
| **> 0.15** | **Unstable** | **Reduce variance** |
| > 0.25 | Very Unstable | Immediate attention needed |

## Programmatic API Usage

### Basic Stability Check

```python
from mcprobe.analysis.flaky import FlakyDetector
from mcprobe.persistence import ResultLoader

# Initialize
loader = ResultLoader(results_dir="./test-results")
detector = FlakyDetector(loader)

# Check stability
result = detector.stability_check(
    scenario_name="Weather Query Test",
    min_runs=5
)

# Process results
print(f"Scenario: {result['scenario_name']}")
print(f"Runs: {result['run_count']}")

if result['is_stable'] is None:
    print(f"Insufficient data: {result['reason']}")
elif result['is_stable']:
    print("✓ Stable")
    print(f"  Pass rate: {result['pass_rate']:.0%}")
    print(f"  Mean score: {result['mean_score']:.2f}")
else:
    print("✗ Unstable")
    for reason in result['reasons']:
        print(f"  - {reason}")
```

### Detailed Analysis

```python
# Get full metrics
result = detector.stability_check("My Scenario", min_runs=10)

if result['is_stable'] is not None:
    pass_rate = result['pass_rate']
    mean_score = result['mean_score']
    score_std = result['score_std']

    # Calculate CV manually
    cv = score_std / mean_score if mean_score > 0 else 0

    print(f"Pass Rate: {pass_rate:.1%}")
    print(f"Mean Score: {mean_score:.3f}")
    print(f"Score Std Dev: {score_std:.3f}")
    print(f"Coefficient of Variation: {cv:.1%}")

    # Detailed assessment
    if pass_rate >= 0.95:
        print("✓ Pass rate: Excellent")
    elif pass_rate <= 0.05:
        print("✓ Pass rate: Consistently failing (stable but broken)")
    else:
        print(f"✗ Pass rate: Flaky ({pass_rate:.0%})")

    if cv <= 0.15:
        print(f"✓ Score variance: Acceptable (CV={cv:.1%})")
    else:
        print(f"✗ Score variance: Too high (CV={cv:.1%})")
```

### Batch Stability Checks

```python
# Check multiple critical scenarios
critical_scenarios = [
    "User Authentication",
    "Payment Processing",
    "Data Export",
    "API Integration"
]

results = {}
for scenario in critical_scenarios:
    results[scenario] = detector.stability_check(scenario, min_runs=10)

# Report
print("Critical Scenario Stability Report\n")
for scenario, result in results.items():
    if result['is_stable'] is None:
        status = "⚠ Insufficient data"
    elif result['is_stable']:
        status = "✓ Stable"
    else:
        status = "✗ Unstable"

    print(f"{scenario}: {status}")
    if result['is_stable'] is not None:
        print(f"  Pass rate: {result['pass_rate']:.0%}, "
              f"Mean score: {result['mean_score']:.2f}")
```

### Pre-Deployment Verification

```python
import sys

def verify_critical_scenarios(scenarios, min_pass_rate=0.95, max_cv=0.10):
    """Verify critical scenarios meet strict stability requirements."""
    loader = ResultLoader()
    detector = FlakyDetector(loader)

    all_stable = True

    for scenario in scenarios:
        result = detector.stability_check(scenario, min_runs=10)

        if result['is_stable'] is None:
            print(f"✗ {scenario}: Insufficient data")
            all_stable = False
            continue

        pass_rate = result['pass_rate']
        mean_score = result['mean_score']
        score_std = result['score_std']
        cv = score_std / mean_score if mean_score > 0 else 0

        # Strict requirements
        if pass_rate < min_pass_rate:
            print(f"✗ {scenario}: Pass rate {pass_rate:.0%} < {min_pass_rate:.0%}")
            all_stable = False
        elif cv > max_cv:
            print(f"✗ {scenario}: CV {cv:.1%} > {max_cv:.1%}")
            all_stable = False
        else:
            print(f"✓ {scenario}: Pass {pass_rate:.0%}, CV {cv:.1%}")

    return all_stable

# Use in deployment script
if __name__ == "__main__":
    critical = ["Login Flow", "Checkout Process", "Data Sync"]

    if verify_critical_scenarios(critical, min_pass_rate=0.98, max_cv=0.08):
        print("\n✓ All critical scenarios stable - deployment approved")
        sys.exit(0)
    else:
        print("\n✗ Critical scenarios unstable - deployment blocked")
        sys.exit(1)
```

### Tracking Stability Over Time

```python
import json
from datetime import datetime

def log_stability(scenario_name):
    """Log stability metrics for tracking over time."""
    loader = ResultLoader()
    detector = FlakyDetector(loader)

    result = detector.stability_check(scenario_name, min_runs=5)

    if result['is_stable'] is not None:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "scenario": scenario_name,
            "run_count": result['run_count'],
            "pass_rate": result['pass_rate'],
            "mean_score": result['mean_score'],
            "score_std": result['score_std'],
            "is_stable": result['is_stable']
        }

        with open("stability-history.jsonl", "a") as f:
            f.write(json.dumps(log_entry) + "\n")

# Run regularly
log_stability("Critical Scenario")
```

## Use Cases

### 1. Investigating Specific Flaky Test

**Workflow:**
```bash
# Step 1: Detect flaky scenarios
mcprobe flaky
# Output: "Weather Query" appears flaky

# Step 2: Get detailed stability metrics
mcprobe stability-check "Weather Query"
# Output shows pass rate 65%, CV 22%

# Step 3: Fix the scenario (make criteria more specific)
# Edit scenarios/weather-query.yaml

# Step 4: Run multiple times to re-test
for i in {1..10}; do
  mcprobe run scenarios/weather-query.yaml
done

# Step 5: Verify fix
mcprobe stability-check "Weather Query"
# Output should show pass rate > 95%, CV < 15%
```

### 2. Pre-Deployment Critical Scenario Verification

```bash
# Verify critical scenarios before deployment
mcprobe stability-check "User Login" --min-runs 10
mcprobe stability-check "Payment Processing" --min-runs 10
mcprobe stability-check "Data Export" --min-runs 10

# All should show stable before deploying
```

### 3. Establishing Baseline Metrics

```bash
# After creating new scenario, establish baseline
for i in {1..15}; do
  mcprobe run scenarios/new-scenario.yaml
done

# Record baseline
mcprobe stability-check "new-scenario" > baseline-metrics.txt
cat baseline-metrics.txt
```

### 4. Validating Test Improvements

**Before improvement:**
```bash
$ mcprobe stability-check "My Test"
Pass Rate: 75%
CV: 18%
✗ Unstable
```

**After improvement:**
```bash
$ mcprobe stability-check "My Test"
Pass Rate: 98%
CV: 6%
✓ Stable
```

### 5. Debugging Intermittent Failures

```bash
# Scenario sometimes fails in CI
# Run locally multiple times
for i in {1..20}; do
  mcprobe run scenarios/intermittent-failure.yaml
done

# Check stability metrics
mcprobe stability-check "intermittent-failure"
# Reveals: Pass rate 85%, CV 25%
# Action: Fix pass rate inconsistency and score variance
```

## When to Use Stability Check vs Flaky Detection

### Use Stability Check When:

✅ **Investigating specific scenario**
- You know which scenario is problematic
- Need detailed metrics for one test
- Debugging a specific issue

✅ **Validating fixes**
- After fixing a flaky test
- Confirming improvements
- Before/after comparison

✅ **Deep dive analysis**
- Need exact CV value
- Want specific stability reasons
- Establishing baseline metrics

✅ **Pre-deployment verification**
- Checking critical scenarios one-by-one
- Need detailed pass for compliance
- Generating detailed reports

**Example:**
```bash
# After fixing flaky test
mcprobe stability-check "Fixed Test" --min-runs 15
```

### Use Flaky Detection When:

✅ **Checking all scenarios**
- Don't know which tests are flaky
- Regular monitoring
- CI/CD quality gates

✅ **Quick overview**
- Need summary of problem areas
- Identifying which tests need attention
- Generating flaky test lists

✅ **CI/CD enforcement**
- Fail build on any flaky test
- Automated quality gates
- Preventing flaky tests from merging

**Example:**
```bash
# CI quality gate
mcprobe flaky --fail-on-flaky
```

### Use Both When:

✅ **Comprehensive analysis**
```bash
# Step 1: Find flaky tests
mcprobe flaky

# Step 2: Investigate each one
mcprobe stability-check "Flaky Test 1"
mcprobe stability-check "Flaky Test 2"
```

✅ **Pre-deployment checklist**
```bash
# All scenarios overview
mcprobe flaky

# Critical scenarios deep dive
mcprobe stability-check "Critical Scenario 1"
mcprobe stability-check "Critical Scenario 2"
```

## Best Practices for Maintaining Stability

### 1. Regular Stability Checks

**Development workflow:**
```bash
# After modifying scenario
for i in {1..10}; do
  mcprobe run scenarios/modified-scenario.yaml
done

mcprobe stability-check "modified-scenario"
```

### 2. Minimum Run Requirements

**Recommended minimums:**
- **Development:** 5-10 runs
- **CI/CD:** 10-15 runs
- **Production monitoring:** 15-20 runs
- **Baseline establishment:** 20+ runs

```python
# Different requirements for different environments
dev_result = detector.stability_check("scenario", min_runs=5)
prod_result = detector.stability_check("scenario", min_runs=15)
```

### 3. Track Stability Trends

```bash
# Weekly stability report
echo "=== Stability Report $(date) ===" >> stability-log.txt
mcprobe stability-check "Critical Test 1" >> stability-log.txt
mcprobe stability-check "Critical Test 2" >> stability-log.txt
```

### 4. Set Strict Thresholds for Critical Scenarios

```python
# Critical scenarios require higher stability
critical_scenarios = ["Login", "Payment", "Checkout"]

for scenario in critical_scenarios:
    result = detector.stability_check(scenario, min_runs=20)

    if result['pass_rate'] < 0.98:  # Require 98% for critical
        print(f"✗ {scenario} below critical threshold")

    cv = result['score_std'] / result['mean_score']
    if cv > 0.10:  # Require CV < 10% for critical
        print(f"✗ {scenario} has too much score variance")
```

### 5. Document Stability Requirements

Create a `STABILITY.md` file:
```markdown
# Stability Requirements

## Critical Scenarios
Must maintain:
- Pass rate ≥ 98%
- CV ≤ 10%
- Min 20 runs for verification

## Standard Scenarios
Must maintain:
- Pass rate ≥ 95%
- CV ≤ 15%
- Min 10 runs for verification
```

### 6. Automate Stability Monitoring

```python
# monitor.py - Run as cron job
from mcprobe.analysis.flaky import FlakyDetector
from mcprobe.persistence import ResultLoader

loader = ResultLoader()
detector = FlakyDetector(loader)

scenarios = loader.list_scenarios()
unstable = []

for scenario in scenarios:
    result = detector.stability_check(scenario, min_runs=5)
    if result['is_stable'] is False:
        unstable.append(scenario)

if unstable:
    print(f"⚠ {len(unstable)} unstable scenarios detected:")
    for s in unstable:
        print(f"  - {s}")
    # Send alert email, Slack message, etc.
```

## Related Documentation

- [CLI Analysis Commands](../cli/analysis.md) - Complete CLI reference
- [Flaky Test Detection](flaky-detection.md) - Detecting flaky scenarios at scale
- [Trend Analysis](trends.md) - Tracking performance trends over time
- [Scenario Best Practices](../scenarios/best-practices.md) - Writing stable scenarios

## Technical Reference

**Source code:**
- `/Users/kiener/code/mcprobe/src/mcprobe/analysis/flaky.py` - stability_check() method
- `/Users/kiener/code/mcprobe/src/mcprobe/analysis/models.py` - Data models

**Key constants:**
```python
STABILITY_PASS_RATE_HIGH = 0.95   # Pass rate threshold for stability
STABILITY_PASS_RATE_LOW = 0.05    # Lower bound (consistently failing)
STABILITY_CV_THRESHOLD = 0.15     # Coefficient of variation threshold
```

**Default parameters:**
```python
min_runs = 5  # stability_check()
```

**Return structure:**
```python
{
    "scenario_name": str,
    "run_count": int,
    "pass_rate": float | None,
    "mean_score": float | None,
    "score_std": float | None,
    "is_stable": bool | None,
    "reasons": list[str] | str
}
```
