# Flaky Test Detection

Comprehensive guide to detecting and fixing flaky (inconsistent) test scenarios in MCProbe using statistical analysis.

## Overview

A **flaky test** is one that exhibits non-deterministic behavior - sometimes passing and sometimes failing without any changes to the code being tested. Flaky tests undermine confidence in your test suite and can mask real issues.

MCProbe's `FlakyDetector` uses statistical methods to identify scenarios with inconsistent behavior:
- Pass/fail rate analysis
- Score variance measurement
- Coefficient of variation calculation
- Historical pattern detection

## What Makes a Test Flaky?

### Common Flaky Characteristics

**1. Inconsistent Pass/Fail Results**
```
Run 1: PASS (score: 0.92)
Run 2: FAIL (score: 0.45)
Run 3: PASS (score: 0.88)
Run 4: FAIL (score: 0.52)
Run 5: PASS (score: 0.90)
```
Pass rate: 60% (flaky range)

**2. High Score Variance**
```
Run 1: PASS (score: 0.95)
Run 2: PASS (score: 0.62)
Run 3: PASS (score: 0.88)
Run 4: PASS (score: 0.71)
Run 5: PASS (score: 0.93)
```
All pass, but scores vary wildly (coefficient of variation: 0.18)

**3. Unpredictable Behavior**
```
Same scenario, same configuration, different results:
- Sometimes completes in 3 turns, sometimes 8 turns
- Sometimes uses correct tools, sometimes doesn't
- Sometimes provides accurate answer, sometimes doesn't
```

### Why Flaky Tests Are Problematic

**Undermines Trust:**
- Developers ignore legitimate failures
- "It's just flaky" becomes the default response
- Real bugs get missed

**Wastes Time:**
- Re-running tests to see if they "pass this time"
- Investigating false positives
- Delayed deployments waiting for green builds

**Hides Real Issues:**
- Actual regressions get attributed to flakiness
- Quality degradation goes unnoticed
- Root causes remain unfixed

## Detection Criteria

MCProbe uses two primary methods to detect flakiness:

### 1. Pass/Fail Inconsistency

A scenario is flaky if its **pass rate falls in the flaky range**.

**Default flaky range: 20% - 80%**

```python
# From mcprobe/analysis/flaky.py
pass_fail_threshold = (0.2, 0.8)  # (min, max)
```

**Why this range?**
- **< 20%**: Consistently failing (not flaky, just broken)
- **20% - 80%**: Inconsistent (flaky behavior)
- **> 80%**: Mostly passing (stable, though could still have high score variance)

**Examples:**

| Pass Rate | Interpretation |
|-----------|----------------|
| 5% | Consistently failing - not flaky, needs fixing |
| 35% | **FLAKY** - inconsistent pass/fail |
| 50% | **FLAKY** - coin flip behavior |
| 75% | **FLAKY** - unreliable |
| 92% | Mostly stable (check score variance) |
| 100% | Consistent passing (check score variance) |

**Severity for pass/fail flakiness:**
```python
if 0.2 < pass_rate < 0.8:
    severity = "high"  # Critical instability
```

### 2. Score Variance (Coefficient of Variation)

Even if a scenario always passes, it can be flaky if scores vary significantly.

**Coefficient of Variation (CV)** = `standard_deviation / mean`

**Default threshold: CV > 0.25**

```python
# From mcprobe/analysis/flaky.py
cv_threshold = 0.25
```

**Why CV instead of standard deviation?**
CV normalizes variance relative to the mean, making it scale-independent:
- Score 0.90 ± 0.05 (CV = 0.056) is more stable than
- Score 0.50 ± 0.05 (CV = 0.100) even though both have same std dev

**Interpreting CV values:**

| CV | Interpretation | Example Scores |
|----|----------------|----------------|
| < 0.10 | Very consistent | 0.90, 0.91, 0.89, 0.92, 0.90 |
| 0.10 - 0.15 | Moderately consistent | 0.85, 0.92, 0.88, 0.83, 0.91 |
| 0.15 - 0.25 | Some variance | 0.75, 0.90, 0.82, 0.88, 0.78 |
| **> 0.25** | **High variance (flaky)** | 0.60, 0.95, 0.72, 0.88, 0.65 |

**Calculation example:**
```python
scores = [0.95, 0.72, 0.88, 0.65, 0.91]
mean = 0.822
std_dev = 0.127
cv = 0.127 / 0.822 = 0.154  # Below 0.25 threshold, not flaky
```

**Severity for score variance:**
```python
if cv > 0.25:
    severity = "medium"  # Moderate instability
```

### Detection Logic

The detector checks both criteria:

```python
# Pseudo-code showing detection flow
for each scenario:
    if insufficient_runs:
        skip

    # Check 1: Pass/fail inconsistency
    if 0.2 < pass_rate < 0.8:
        flag_as_flaky(reason="Inconsistent pass/fail", severity="high")
        continue  # Don't check variance for already-flaky scenarios

    # Check 2: Score variance (for passing runs only)
    if len(passing_runs) >= min_runs:
        cv = calculate_cv(passing_scores)
        if cv > 0.25:
            flag_as_flaky(reason="High score variance", severity="medium")
```

## Configurable Thresholds

All detection parameters are configurable:

```python
from mcprobe.analysis.flaky import FlakyDetector
from mcprobe.persistence import ResultLoader

loader = ResultLoader(results_dir="./test-results")
detector = FlakyDetector(loader)

# Detect with custom settings
flaky = detector.detect_flaky_scenarios(
    min_runs=10,                      # Need 10+ runs for analysis
    pass_fail_threshold=(0.15, 0.85), # Stricter flaky range
    cv_threshold=0.20                 # More sensitive to variance
)
```

**Parameter guide:**

**min_runs** (default: 5)
- Minimum number of runs required for statistical significance
- Lower = faster detection, but less reliable
- Higher = more reliable, but requires more data
- Recommended: 5-10 for development, 10-20 for production

**pass_fail_threshold** (default: (0.2, 0.8))
- Range of pass rates considered flaky
- Stricter: (0.15, 0.85) - flag more scenarios
- Looser: (0.3, 0.7) - only obvious flakiness
- Recommended: Keep default unless you have specific needs

**cv_threshold** (default: 0.25)
- Coefficient of variation threshold for score variance
- Lower = more sensitive (flag more scenarios)
- Higher = less sensitive (only major variance)
- Recommended: 0.20-0.30 range

## Severity Levels

Flaky scenarios are classified by severity:

### High Severity

**Criteria:**
- Pass rate between 20% and 80%
- Critical instability

**Characteristics:**
- Coin-flip behavior
- Completely unreliable
- Blocks CI/CD pipelines
- High priority to fix

**Example:**
```
Scenario: "API Authentication Test"
Pass Rate: 45%
Runs: 20 (9 passed, 11 failed)
Severity: high
Reason: Inconsistent pass/fail results
```

**Action required:**
Immediate investigation and fix - this test cannot be trusted.

### Medium Severity

**Criteria:**
- Pass rate > 80% (mostly passes)
- BUT coefficient of variation > 0.25
- Moderate instability

**Characteristics:**
- Usually passes but with varying quality
- Inconsistent scores
- May indicate subtle issues
- Should be fixed but less urgent

**Example:**
```
Scenario: "Complex Workflow Test"
Pass Rate: 90%
CV: 0.28
Runs: 15 (all passed, but scores: 0.95, 0.65, 0.88, 0.71, 0.92, ...)
Severity: medium
Reason: High score variance (CV=28%)
```

**Action required:**
Investigate inconsistency, improve test determinism.

### Low Severity

**Note:** MCProbe currently uses "high" and "medium" severity. Low severity is not currently assigned by the detector but is mentioned here for API consistency with other analysis tools.

**Could indicate:**
- Borderline flakiness
- May warrant monitoring
- Not yet critical

## CLI Usage

### Basic Flaky Detection

```bash
# Detect flaky scenarios with defaults
mcprobe flaky

# Require more runs for confidence
mcprobe flaky --min-runs 10

# Use custom results directory
mcprobe flaky --results-dir ./my-results
```

**Output when flaky scenarios found:**
```
Flaky Scenarios
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Scenario           ┃ Pass Rate ┃ Runs ┃ Severity ┃ Reason                          ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Weather Query      │       60% │   10 │   high   │ Inconsistent pass/fail results  │
│ Complex Workflow   │       90% │   15 │  medium  │ High score variance (CV=28%)    │
│ Error Handling     │       35% │   12 │   high   │ Inconsistent pass/fail results  │
└────────────────────┴───────────┴──────┴──────────┴─────────────────────────────────┘

Found 3 flaky scenario(s)
```

**Output when no flaky scenarios:**
```
No flaky scenarios detected.
```

**Output with insufficient data:**
```
No flaky scenarios detected.

Note: Some scenarios have fewer than 5 runs and were not analyzed:
  - New Scenario (3 runs)
  - Recent Test (2 runs)
```

### Fail on Flaky (CI/CD Quality Gate)

Use `--fail-on-flaky` to exit with code 1 if flaky tests are detected:

```bash
# Fail build if flaky tests exist
mcprobe flaky --fail-on-flaky
echo $?  # 1 if flaky scenarios found, 0 otherwise
```

**GitHub Actions example:**
```yaml
- name: Run tests
  run: mcprobe run scenarios/

- name: Check for flaky tests
  run: mcprobe flaky --min-runs 10 --fail-on-flaky
```

**CI script example:**
```bash
#!/bin/bash
set -e

# Run test suite
mcprobe run scenarios/

# Enforce no flaky tests
if ! mcprobe flaky --min-runs 5 --fail-on-flaky; then
  echo "❌ Flaky tests detected - build failed"
  exit 1
fi

echo "✅ No flaky tests - proceeding with deployment"
```

### Combining with Other Commands

```bash
# Full analysis workflow
mcprobe run scenarios/          # Run tests
mcprobe trends                  # Check trends
mcprobe flaky --fail-on-flaky   # Enforce stability
mcprobe report --format html    # Generate report
```

## Programmatic API Usage

### Basic Detection

```python
from mcprobe.analysis.flaky import FlakyDetector
from mcprobe.persistence import ResultLoader

# Initialize
loader = ResultLoader(results_dir="./test-results")
detector = FlakyDetector(loader)

# Detect flaky scenarios
flaky_scenarios = detector.detect_flaky_scenarios(min_runs=5)

# Process results
if flaky_scenarios:
    print(f"Found {len(flaky_scenarios)} flaky scenario(s):")
    for scenario in flaky_scenarios:
        print(f"\n{scenario.scenario_name}:")
        print(f"  Pass rate: {scenario.pass_rate:.0%}")
        print(f"  Severity: {scenario.severity}")
        print(f"  Reason: {scenario.reason}")
        print(f"  Run count: {scenario.run_count}")

        if scenario.coefficient_of_variation:
            print(f"  CV: {scenario.coefficient_of_variation:.2%}")
else:
    print("No flaky scenarios detected")
```

### Filter by Severity

```python
# Get high-severity flaky tests only
high_severity = [
    s for s in flaky_scenarios
    if s.severity == "high"
]

if high_severity:
    print("CRITICAL FLAKY TESTS:")
    for scenario in high_severity:
        print(f"  - {scenario.scenario_name} ({scenario.pass_rate:.0%} pass rate)")
```

### Custom Thresholds

```python
# More sensitive detection
flaky_scenarios = detector.detect_flaky_scenarios(
    min_runs=10,
    pass_fail_threshold=(0.15, 0.85),  # Wider flaky range
    cv_threshold=0.20                   # Lower variance threshold
)

# Conservative detection (fewer false positives)
flaky_scenarios = detector.detect_flaky_scenarios(
    min_runs=15,
    pass_fail_threshold=(0.3, 0.7),    # Narrower flaky range
    cv_threshold=0.30                   # Higher variance threshold
)
```

### Integration with CI/CD

```python
# ci_quality_gate.py
import sys
from mcprobe.analysis.flaky import FlakyDetector
from mcprobe.persistence import ResultLoader

def main():
    loader = ResultLoader()
    detector = FlakyDetector(loader)

    # Detect flaky scenarios
    flaky = detector.detect_flaky_scenarios(min_runs=10)

    # Fail on high-severity flaky tests
    high_severity = [s for s in flaky if s.severity == "high"]

    if high_severity:
        print(f"❌ FAILED: {len(high_severity)} high-severity flaky test(s)")
        for scenario in high_severity:
            print(f"  - {scenario.scenario_name}: {scenario.reason}")
        sys.exit(1)

    # Warn on medium-severity
    medium_severity = [s for s in flaky if s.severity == "medium"]
    if medium_severity:
        print(f"⚠ WARNING: {len(medium_severity)} medium-severity flaky test(s)")
        for scenario in medium_severity:
            print(f"  - {scenario.scenario_name}: {scenario.reason}")

    print("✅ PASSED: No critical flaky tests")
    sys.exit(0)

if __name__ == "__main__":
    main()
```

### Export Flaky Test Data

```python
import json

# Detect flaky scenarios
flaky_scenarios = detector.detect_flaky_scenarios(min_runs=10)

# Convert to JSON
flaky_data = [
    {
        "scenario": s.scenario_name,
        "pass_rate": s.pass_rate,
        "runs": s.run_count,
        "severity": s.severity,
        "reason": s.reason,
        "cv": s.coefficient_of_variation,
        "variance": s.score_variance
    }
    for s in flaky_scenarios
]

# Save to file
with open("flaky-tests.json", "w") as f:
    json.dump(flaky_data, f, indent=2)
```

## Strategies for Fixing Flaky Tests

### 1. Make Evaluation Criteria More Specific

**Problem:** Vague criteria lead to inconsistent judgments

**Before (flaky):**
```yaml
evaluation:
  correctness_criteria:
    - Agent provides helpful response
    - Agent addresses the question
```

**After (stable):**
```yaml
evaluation:
  correctness_criteria:
    - Agent calls get_weather tool exactly once
    - Agent calls get_weather with location="London"
    - Agent includes temperature value in response
    - Agent responds within 5 turns
```

### 2. Reduce Non-Determinism

**Problem:** Agent behavior varies due to randomness

**Strategies:**
- Use specific queries instead of vague ones
- Set max turns to limit variation
- Specify exact expected tools
- Use deterministic test data

**Example:**
```yaml
# Before (flaky)
synthetic_user:
  initial_query: "Tell me about the weather"

# After (stable)
synthetic_user:
  initial_query: "What's the current temperature in London, UK?"
  max_turns: 5

evaluation:
  tool_usage:
    expected_tools:
      - get_current_weather
    expected_tool_calls: 1
```

### 3. Control Environmental Factors

**Problem:** External dependencies cause inconsistency

**Strategies:**
- Use mock MCP servers for testing
- Ensure stable model availability
- Control temperature/randomness settings
- Use consistent test environment

**Example:**
```yaml
# Use deterministic settings
agent_config:
  temperature: 0.0  # Minimum randomness
  model: "llama3.2"  # Consistent model
```

### 4. Fix Tool Usage Issues

**Problem:** Inconsistent tool call patterns

**Check for:**
- Missing required parameters
- Optional parameters causing variation
- Tool errors being handled differently
- Race conditions in async tools

**Solution:**
```yaml
evaluation:
  tool_usage:
    required_tools:
      - get_current_weather  # Must be called
    forbidden_tools:
      - get_forecast  # Should not be called
    max_tool_calls: 5  # Limit variation
```

### 5. Improve Test Data Quality

**Problem:** Ambiguous test data leads to different interpretations

**Strategies:**
- Use clear, unambiguous queries
- Provide complete context
- Avoid edge cases in basic tests
- Use realistic but controlled scenarios

**Example:**
```yaml
# Before (flaky)
synthetic_user:
  initial_query: "Weather?"

# After (stable)
synthetic_user:
  initial_query: "What is the current weather in London, UK? I need the temperature."
  context: "User is planning to visit London today and needs to know what to wear."
```

### 6. Add Timing Constraints

**Problem:** Varying execution time affects results

**Solution:**
```yaml
synthetic_user:
  max_turns: 5          # Limit conversation length
  timeout_seconds: 30   # Prevent hanging

evaluation:
  efficiency_metrics:
    max_turns: 5
    max_tool_calls: 3
```

### 7. Isolate Tests

**Problem:** Tests interfere with each other

**Strategies:**
- Use independent scenarios
- Clear state between runs
- Avoid shared resources
- Test one behavior per scenario

### 8. Use Stability Check During Development

Run the scenario multiple times and check stability:

```bash
# Run scenario 15 times
for i in {1..15}; do
  mcprobe run scenarios/my-test.yaml
done

# Check stability
mcprobe stability-check "my-test"
```

**Interpret results:**
- Pass rate < 95%: Fix pass/fail inconsistency
- Score std dev > 0.05: Reduce score variance
- CV > 0.15: Investigate quality inconsistency

## Common Causes of Flakiness

### 1. LLM Non-Determinism

**Cause:** Language models are probabilistic

**Symptoms:**
- Different responses to same prompt
- Varying tool call patterns
- Inconsistent reasoning

**Fix:**
- Set temperature to 0 (or very low)
- Use more specific prompts
- Add explicit constraints in scenario

### 2. Timing Issues

**Cause:** Race conditions, timeouts, delays

**Symptoms:**
- Sometimes completes quickly, sometimes slowly
- Occasional timeouts
- Different results based on response speed

**Fix:**
- Add appropriate timeouts
- Use max_turns to limit variability
- Ensure MCP servers respond consistently

### 3. Ambiguous Evaluation

**Cause:** Vague correctness criteria

**Symptoms:**
- Judge sometimes passes, sometimes fails same behavior
- Inconsistent scoring for similar conversations

**Fix:**
- Make criteria specific and measurable
- Use tool_usage checks for concrete expectations
- Add turn_limit and other constraints

### 4. External Dependencies

**Cause:** Unstable MCP servers, network issues

**Symptoms:**
- Flakiness only with certain tools
- Errors appear randomly
- Network-related failures

**Fix:**
- Use reliable MCP servers
- Add retry logic where appropriate
- Mock external dependencies for tests

### 5. State Pollution

**Cause:** Previous runs affecting current run

**Symptoms:**
- First run passes, subsequent runs fail
- Results vary based on execution order

**Fix:**
- Ensure clean state for each run
- Avoid shared resources
- Isolate test scenarios

### 6. Insufficient Context

**Cause:** Agent lacks necessary information

**Symptoms:**
- Sometimes agent succeeds, sometimes asks for clarification
- Varying conversation lengths

**Fix:**
- Provide complete context in initial_query
- Add context field with relevant information
- Make queries self-contained

## Best Practices

### During Development

**1. Test new scenarios multiple times:**
```bash
# Verify stability before committing
for i in {1..10}; do
  mcprobe run scenarios/new-test.yaml
done

mcprobe flaky --min-runs 5
```

**2. Use stability-check for detailed metrics:**
```bash
mcprobe stability-check "new-test"
```

**3. Fix flakiness immediately:**
Don't let flaky tests accumulate - fix them as soon as detected.

### In CI/CD

**1. Enforce no flaky tests:**
```yaml
- name: Detect flaky tests
  run: mcprobe flaky --min-runs 10 --fail-on-flaky
```

**2. Run critical tests multiple times:**
```bash
# Run critical scenarios 5 times to verify stability
for i in {1..5}; do
  mcprobe run scenarios/critical/
done
```

**3. Separate flaky test detection:**
```yaml
# Run flaky detection as separate job
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Run tests
        run: mcprobe run scenarios/

  quality:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - name: Check for flakiness
        run: mcprobe flaky --fail-on-flaky
```

### Monitoring

**1. Regular flaky test reports:**
```bash
# Weekly flaky test check
mcprobe flaky --min-runs 10 > weekly-flaky-report.txt
```

**2. Track flaky test count over time:**
```python
# monitor-flakiness.py
from mcprobe.analysis.flaky import FlakyDetector
from mcprobe.persistence import ResultLoader
import json
from datetime import datetime

loader = ResultLoader()
detector = FlakyDetector(loader)

flaky = detector.detect_flaky_scenarios(min_runs=10)

# Log flaky count
log_entry = {
    "timestamp": datetime.now().isoformat(),
    "flaky_count": len(flaky),
    "high_severity": len([s for s in flaky if s.severity == "high"]),
    "medium_severity": len([s for s in flaky if s.severity == "medium"])
}

with open("flaky-history.jsonl", "a") as f:
    f.write(json.dumps(log_entry) + "\n")
```

**3. Alert on new flaky tests:**
```bash
# Compare current to baseline
mcprobe flaky --min-runs 10 > current-flaky.txt

if [ $(wc -l < current-flaky.txt) -gt $(wc -l < baseline-flaky.txt) ]; then
  echo "New flaky tests detected!" | mail -s "Flaky Test Alert" team@example.com
fi
```

## When to Use Flaky Detection vs Stability Check

### Use Flaky Detection When:
- Checking all scenarios at once
- Setting up CI/CD quality gates
- Regular monitoring (weekly, monthly)
- Need quick overview of problem areas

**Example:**
```bash
# Check all scenarios for flakiness
mcprobe flaky --fail-on-flaky
```

### Use Stability Check When:
- Investigating specific scenario
- Debugging a known flaky test
- Need detailed metrics for one scenario
- Validating a fix

**Example:**
```bash
# Deep dive into specific scenario
mcprobe stability-check "Weather Query Test"
```

### Use Both When:
- Comprehensive quality analysis
- Pre-deployment verification
- Establishing baselines

**Example:**
```bash
# Full stability analysis
mcprobe flaky
mcprobe stability-check "Critical Scenario 1"
mcprobe stability-check "Critical Scenario 2"
```

## Related Documentation

- [CLI Analysis Commands](../cli/analysis.md) - Complete CLI reference for flaky detection
- [Stability Checking](stability.md) - Detailed stability metrics
- [Trend Analysis](trends.md) - Tracking performance over time
- [Scenario Best Practices](../scenarios/best-practices.md) - Writing stable scenarios

## Technical Reference

**Source code:**
- `/Users/kiener/code/mcprobe/src/mcprobe/analysis/flaky.py` - FlakyDetector implementation
- `/Users/kiener/code/mcprobe/src/mcprobe/analysis/models.py` - FlakyScenario model

**Key constants:**
```python
STABILITY_PASS_RATE_HIGH = 0.95
STABILITY_PASS_RATE_LOW = 0.05
STABILITY_CV_THRESHOLD = 0.15
```

**Default parameters:**
```python
min_runs = 5                           # detect_flaky_scenarios()
pass_fail_threshold = (0.2, 0.8)       # detect_flaky_scenarios()
cv_threshold = 0.25                    # detect_flaky_scenarios()
```

**FlakyScenario Model:**
```python
class FlakyScenario(BaseModel):
    scenario_name: str
    pass_rate: float
    score_variance: float | None = None
    coefficient_of_variation: float | None = None
    reason: str
    severity: str  # "high" or "medium"
    run_count: int = 0
```
