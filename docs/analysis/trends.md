# Trend Analysis Guide

Comprehensive guide to MCProbe's trend analysis system for tracking test performance, detecting regressions, and monitoring quality over time.

## Overview

The `TrendAnalyzer` uses statistical methods to analyze historical test results and identify patterns in:
- Pass/fail rates over time
- Score trends (improving, stable, or degrading)
- Performance regressions
- Quality metrics evolution

**Key capabilities:**
- Linear regression-based trend detection
- Automatic regression identification with severity levels
- Configurable analysis windows
- Statistical significance testing

## How Trend Analysis Works

### Data Requirements

MCProbe requires a minimum number of data points for accurate analysis:

| Analysis Type | Minimum Runs | Constant |
|--------------|--------------|----------|
| Basic analysis | 2 | `MIN_DATA_POINTS_FOR_ANALYSIS` |
| Trend detection | 3 | `MIN_DATA_POINTS_FOR_TREND` |
| Regression detection | 4 | `MIN_DATA_POINTS_FOR_REGRESSION` |

**Why these minimums?**
- **2 runs**: Can calculate basic statistics (mean, variance)
- **3 runs**: Can fit a meaningful linear regression line
- **4 runs**: Can split data for before/after comparison

### Linear Regression Method

The trend detector uses simple linear regression to determine if a metric is improving, degrading, or stable:

1. **Fit a line** through the data points (oldest to newest)
2. **Calculate the slope** of the line
3. **Normalize the slope** by the value range to make it scale-independent
4. **Compare to threshold** to determine significance

**Normalization example:**
```
Raw slope: 0.02
Value range: 0.1 (max: 0.9, min: 0.8)
Normalized slope: 0.02 / 0.1 = 0.2
```

This prevents small absolute changes in high-variance scenarios from being classified as trends.

### Slope Threshold

The **slope threshold** (default: `0.05`) determines when a trend is significant enough to flag:

```python
if normalized_slope > 0.05:
    return TrendDirection.IMPROVING
elif normalized_slope < -0.05:
    return TrendDirection.DEGRADING
else:
    return TrendDirection.STABLE
```

**Configuring the threshold:**
```python
from mcprobe.analysis.trends import TrendAnalyzer
from mcprobe.persistence import ResultLoader

loader = ResultLoader(results_dir="./test-results")

# More sensitive (detect smaller changes)
analyzer = TrendAnalyzer(loader, slope_threshold=0.03)

# Less sensitive (only flag major trends)
analyzer = TrendAnalyzer(loader, slope_threshold=0.10)
```

**Choosing the right threshold:**
- **0.03**: Very sensitive, good for catching small degradations early
- **0.05** (default): Balanced sensitivity, recommended for most use cases
- **0.10**: Conservative, only flags significant trends

## TrendDirection Enum

Three possible trend directions for any metric:

```python
from mcprobe.analysis.models import TrendDirection

TrendDirection.IMPROVING   # Metric is getting better over time
TrendDirection.STABLE      # No significant change detected
TrendDirection.DEGRADING   # Metric is getting worse over time
```

**Examples:**

| Scenario | Pass Rate | Pass Trend | Avg Score | Score Trend |
|----------|-----------|------------|-----------|-------------|
| Improving quality | 100% | STABLE | 0.85 → 0.92 | IMPROVING |
| New regression | 90% → 60% | DEGRADING | 0.88 → 0.75 | DEGRADING |
| Consistent performance | 95% | STABLE | 0.91 | STABLE |

## Window Size and Its Effect

The **window size** controls how many recent test runs to analyze. This is a crucial parameter that affects:
- Trend sensitivity
- Statistical stability
- Detection speed

### Small Window (5-10 runs)

**Characteristics:**
- Detects changes quickly
- More sensitive to recent variations
- Higher chance of false positives
- Good for active development

**Use when:**
- Making rapid changes to your agent
- Debugging specific issues
- Need immediate feedback on changes

**Example:**
```bash
# Detect recent changes quickly
mcprobe trends --window 5
```

```python
trends = analyzer.analyze_scenario("my_scenario", window_size=5)
```

### Medium Window (10-20 runs, default)

**Characteristics:**
- Balanced sensitivity and stability
- Smooths out minor fluctuations
- Reliable trend detection
- Recommended for most use cases

**Use when:**
- Running regular CI/CD checks
- Monitoring production systems
- General quality tracking

**Example:**
```bash
# Default balanced analysis
mcprobe trends --window 10
```

```python
trends = analyzer.analyze_scenario("my_scenario", window_size=10)
```

### Large Window (20-50+ runs)

**Characteristics:**
- Very stable trend detection
- Resistant to outliers and noise
- Slower to detect changes
- Good for long-term analysis

**Use when:**
- Analyzing historical patterns
- Generating monthly/quarterly reports
- Validating long-term improvements

**Example:**
```bash
# Long-term trend analysis
mcprobe trends --window 30
```

```python
trends = analyzer.analyze_scenario("my_scenario", window_size=30)
```

### Window Size Comparison

Given this data for a scenario:
```
Runs 1-10:  Scores [0.90, 0.91, 0.89, 0.92, 0.90, 0.91, 0.90, 0.92, 0.91, 0.90]
Runs 11-20: Scores [0.85, 0.84, 0.86, 0.85, 0.84, 0.85, 0.86, 0.85, 0.84, 0.85]
```

**Window 5 (recent 5 runs only):**
- Data: [0.85, 0.86, 0.85, 0.84, 0.85]
- Trend: STABLE (recent runs are consistently ~0.85)
- **Misses** the earlier high scores

**Window 10:**
- Data: [0.91, 0.90, 0.85, 0.84, 0.86, 0.85, 0.84, 0.85, 0.86, 0.85]
- Trend: DEGRADING (clear downward slope)
- **Detects** the regression

**Window 20:**
- Data: All 20 runs
- Trend: DEGRADING (confirms the pattern)
- Most stable, but slower to react

## Understanding Trend Output

### ScenarioTrends Model

The complete data structure returned by `analyze_scenario()`:

```python
from mcprobe.analysis.models import ScenarioTrends, TrendDirection

trends = ScenarioTrends(
    scenario_name="Weather Query Test",
    run_count=15,

    # Pass/fail metrics
    pass_rate=0.93,              # 93% of runs passed
    pass_trend=TrendDirection.STABLE,

    # Score metrics
    current_score=0.91,          # Latest run score
    avg_score=0.88,              # Average across window
    min_score=0.82,              # Lowest score in window
    max_score=0.95,              # Highest score in window
    score_trend=TrendDirection.IMPROVING,
    score_variance=0.0123,       # Variance of scores

    # Performance metrics
    avg_duration=12.5,           # Average runtime (seconds)
    avg_tool_calls=8.2,          # Average tools used
    avg_tokens=1250.5            # Average tokens consumed
)
```

### Key Metrics Explained

**pass_rate** (0.0 - 1.0)
- Percentage of runs that passed all correctness criteria
- 1.0 = perfect reliability
- < 0.8 = concerning stability

**current_score** (0.0 - 1.0)
- The score from the most recent run
- Useful for spotting immediate issues
- Compare to `avg_score` to see if latest is typical

**avg_score** (0.0 - 1.0)
- Mean score across the analysis window
- Primary quality metric
- Should trend upward as you improve your agent

**score_variance**
- Statistical variance of scores
- Lower = more consistent
- High variance may indicate flakiness

**score_trend**
- Statistical trend direction for scores
- Based on linear regression slope
- Accounts for natural variance

**pass_trend**
- Trend for pass/fail results
- Treats passing as 1.0, failing as 0.0
- More sensitive than pass_rate for detecting issues

## Regression Detection

Regression detection compares **recent performance** to **earlier performance** to identify degradations.

### How It Works

1. **Split historical data** into two halves:
   - Earlier half: baseline performance
   - Recent half: current performance

2. **Compare metrics**:
   - Pass rate: `earlier_pass_rate - recent_pass_rate`
   - Score: `earlier_avg_score - recent_avg_score`

3. **Check thresholds**:
   - If drop exceeds threshold, flag as regression
   - Calculate severity based on magnitude

### Regression Thresholds

Default thresholds for flagging regressions:

```python
# Pass rate must drop by at least 10% to flag
pass_rate_threshold = 0.1

# Score must drop by at least 0.1 (10 points) to flag
score_threshold = 0.1
```

**Examples:**

| Earlier | Recent | Drop | Flagged? |
|---------|--------|------|----------|
| Pass: 95% | Pass: 90% | 5% | No (< 10% threshold) |
| Pass: 95% | Pass: 80% | 15% | **Yes** (> 10% threshold) |
| Score: 0.90 | Score: 0.88 | 0.02 | No (< 0.1 threshold) |
| Score: 0.90 | Score: 0.75 | 0.15 | **Yes** (> 0.1 threshold) |

### Severity Levels

Regressions are classified into three severity levels based on the **magnitude of change**:

```python
# From mcprobe/analysis/trends.py
SEVERITY_HIGH_THRESHOLD = 0.3      # 30% change
SEVERITY_MEDIUM_THRESHOLD = 0.15   # 15% change
```

**High Severity** (change > 30%):
- Critical degradation requiring immediate attention
- Example: Pass rate drops from 90% to 60% (33% change)
- Example: Score drops from 0.90 to 0.60 (33% change)

**Medium Severity** (15% < change ≤ 30%):
- Significant degradation needing investigation
- Example: Pass rate drops from 90% to 75% (17% change)
- Example: Score drops from 0.90 to 0.75 (17% change)

**Low Severity** (change ≤ 15%):
- Minor degradation worth monitoring
- Example: Pass rate drops from 90% to 85% (6% change)
- Example: Score drops from 0.90 to 0.85 (6% change)

### Regression Model

```python
from mcprobe.analysis.models import Regression

regression = Regression(
    scenario_name="Weather Query Test",
    metric="pass_rate",          # or "score"
    previous_value=0.95,         # Earlier half average
    current_value=0.75,          # Recent half average
    change_percent=-21.05,       # -21.05% change
    severity="high"              # high/medium/low
)
```

### Custom Thresholds

Adjust sensitivity based on your needs:

```python
# More sensitive - catch smaller regressions
regressions = analyzer.detect_regressions(
    pass_rate_threshold=0.05,  # Flag 5% drops
    score_threshold=0.05       # Flag 0.05 score drops
)

# Less sensitive - only major issues
regressions = analyzer.detect_regressions(
    pass_rate_threshold=0.20,  # Flag 20% drops
    score_threshold=0.15       # Flag 0.15 score drops
)
```

## CLI Usage

### Analyze All Scenarios

```bash
# Default: 10-run window
mcprobe trends

# Larger window for stability
mcprobe trends --window 20

# Smaller window for quick feedback
mcprobe trends --window 5

# Custom results directory
mcprobe trends --results-dir ./my-results
```

**Output example:**
```
Trend Analysis
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Scenario            ┃ Runs ┃ Pass Rate ┃ Pass Trend ┃ Avg Score ┃ Score Trend ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Weather Query       │   20 │       95% │     ↑      │      0.92 │      →      │
│ Greeting Test       │   20 │      100% │     →      │      0.98 │      ↑      │
│ Error Handling      │   15 │       80% │     ↓      │      0.75 │      ↓      │
└─────────────────────┴──────┴───────────┴────────────┴───────────┴─────────────┘

⚠ Detected Regressions:
  [high] Error Handling: pass_rate dropped 15.0% (0.95 → 0.80)
  [high] Error Handling: score dropped 18.2% (0.88 → 0.72)
```

### Analyze Specific Scenario

```bash
# Detailed analysis of one scenario
mcprobe trends --scenario "Weather Query Test"

# With custom window
mcprobe trends --scenario "My Test" --window 30
```

**Output example:**
```
Trend Analysis
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Scenario            ┃ Runs ┃ Pass Rate ┃ Pass Trend ┃ Avg Score ┃ Score Trend ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Weather Query Test  │   20 │       95% │     ↑      │      0.92 │      →      │
└─────────────────────┴──────┴───────────┴────────────┴───────────┴─────────────┘

No regressions detected.
```

### Understanding CLI Output

**Trend Indicators:**
- `↑` (green): Metric is improving over time
- `→` (gray): Metric is stable (no significant change)
- `↓` (red): Metric is degrading over time

**Pass Rate:**
- Shown as percentage (0-100%)
- Calculated over the analysis window
- 100% = all runs in window passed

**Avg Score:**
- Shown as decimal (0.00-1.00)
- Average across window
- Higher is better

**Regression Warnings:**
- Listed after the table if any detected
- Shows severity level in brackets
- Includes metric name and change percentage
- Shows before/after values

## Programmatic API Usage

### Basic Analysis

```python
from mcprobe.analysis.trends import TrendAnalyzer
from mcprobe.persistence import ResultLoader

# Initialize
loader = ResultLoader(results_dir="./test-results")
analyzer = TrendAnalyzer(loader)

# Analyze one scenario
trends = analyzer.analyze_scenario("my_scenario", window_size=10)

if trends:
    print(f"Pass rate: {trends.pass_rate:.0%}")
    print(f"Pass trend: {trends.pass_trend}")
    print(f"Avg score: {trends.avg_score:.2f}")
    print(f"Score trend: {trends.score_trend}")
    print(f"Current vs avg: {trends.current_score:.2f} vs {trends.avg_score:.2f}")
else:
    print("Insufficient data for analysis")
```

### Analyze All Scenarios

```python
# Get trends for all scenarios
all_trends = analyzer.analyze_all(window_size=10)

# Filter degrading scenarios
degrading = [
    t for t in all_trends
    if t.score_trend == TrendDirection.DEGRADING
]

print(f"Found {len(degrading)} degrading scenarios:")
for trend in degrading:
    print(f"  - {trend.scenario_name}: {trend.avg_score:.2f}")
```

### Detect Regressions

```python
# Detect with default thresholds
regressions = analyzer.detect_regressions()

# Or custom thresholds
regressions = analyzer.detect_regressions(
    pass_rate_threshold=0.05,
    score_threshold=0.05
)

# Process results
if regressions:
    print(f"Found {len(regressions)} regression(s)")

    for reg in regressions:
        print(f"\n{reg.scenario_name}:")
        print(f"  Metric: {reg.metric}")
        print(f"  Change: {reg.change_percent:.1f}%")
        print(f"  Previous: {reg.previous_value:.2f}")
        print(f"  Current: {reg.current_value:.2f}")
        print(f"  Severity: {reg.severity}")
```

### Filter by Severity

```python
# Get high-severity regressions only
high_severity = [
    r for r in regressions
    if r.severity == "high"
]

if high_severity:
    print("CRITICAL REGRESSIONS:")
    for reg in high_severity:
        print(f"  - {reg.scenario_name}: {reg.metric} {reg.change_percent:.1f}%")
```

### Custom Slope Threshold

```python
# More sensitive trend detection
sensitive_analyzer = TrendAnalyzer(
    loader,
    slope_threshold=0.03
)

trends = sensitive_analyzer.analyze_scenario("my_scenario")
print(f"Score trend: {trends.score_trend}")  # More likely to detect IMPROVING/DEGRADING
```

### Exporting Trend Data

```python
import json

# Analyze all scenarios
all_trends = analyzer.analyze_all(window_size=20)

# Convert to JSON-serializable format
trend_data = [
    {
        "scenario": t.scenario_name,
        "runs": t.run_count,
        "pass_rate": t.pass_rate,
        "pass_trend": t.pass_trend.value,
        "avg_score": t.avg_score,
        "score_trend": t.score_trend.value,
        "score_variance": t.score_variance,
    }
    for t in all_trends
]

# Save to file
with open("trends.json", "w") as f:
    json.dump(trend_data, f, indent=2)
```

## Best Practices for Tracking Trends

### 1. Establish Baselines

Run each scenario multiple times (10-20) before monitoring trends:

```bash
# Create baseline
for i in {1..15}; do
  mcprobe run scenarios/my-scenario.yaml
done

# Now trends will be meaningful
mcprobe trends --scenario "my-scenario"
```

### 2. Regular Monitoring

Set up daily/weekly trend checks:

```bash
#!/bin/bash
# daily-trends.sh

mcprobe trends --window 10 > daily-trends.txt

# Email if regressions found
if grep -q "high.*Regression" daily-trends.txt; then
  mail -s "MCProbe: High Severity Regression" team@example.com < daily-trends.txt
fi
```

### 3. Choose Appropriate Windows

Match window size to your use case:

```python
# Quick feedback during development
dev_trends = analyzer.analyze_all(window_size=5)

# CI/CD quality gates
ci_trends = analyzer.analyze_all(window_size=10)

# Monthly reports
monthly_trends = analyzer.analyze_all(window_size=50)
```

### 4. Track Multiple Metrics

Don't rely on just pass rate or score alone:

```python
trends = analyzer.analyze_scenario("my_scenario")

# Check all metrics
if trends.pass_trend == TrendDirection.DEGRADING:
    print("⚠ Pass rate is degrading")

if trends.score_trend == TrendDirection.DEGRADING:
    print("⚠ Quality is degrading")

if trends.score_variance > 0.05:
    print("⚠ High variance - possible flakiness")

if trends.avg_duration > 30.0:
    print("⚠ Slow execution")
```

### 5. Set Up Quality Gates

Fail CI if trends degrade:

```python
# quality-gate.py
from mcprobe.analysis.trends import TrendAnalyzer
from mcprobe.persistence import ResultLoader
import sys

loader = ResultLoader()
analyzer = TrendAnalyzer(loader)

# Check for regressions
regressions = analyzer.detect_regressions(
    pass_rate_threshold=0.10,
    score_threshold=0.10
)

# Fail on high severity
high_severity = [r for r in regressions if r.severity == "high"]
if high_severity:
    print(f"FAILED: {len(high_severity)} high-severity regressions")
    for reg in high_severity:
        print(f"  {reg.scenario_name}: {reg.metric} {reg.change_percent:.1f}%")
    sys.exit(1)

print("PASSED: No high-severity regressions")
```

### 6. Document Expected Trends

Keep notes on why trends change:

```bash
# After major refactor
mcprobe run scenarios/
mcprobe trends > post-refactor-trends.txt

# Compare to baseline
echo "Refactored authentication system on $(date)" >> trends-log.txt
cat post-refactor-trends.txt >> trends-log.txt
```

### 7. Combine with Flaky Detection

Trends + flaky detection = complete picture:

```python
from mcprobe.analysis.flaky import FlakyDetector

flaky_detector = FlakyDetector(loader)

# Check trends
trends = analyzer.analyze_scenario("my_scenario")

# Check stability
flaky_scenarios = flaky_detector.detect_flaky_scenarios(min_runs=10)
scenario_is_flaky = any(f.scenario_name == "my_scenario" for f in flaky_scenarios)

if trends.score_trend == TrendDirection.DEGRADING and scenario_is_flaky:
    print("⚠ CRITICAL: Degrading AND flaky - high priority issue")
elif trends.score_trend == TrendDirection.DEGRADING:
    print("⚠ Degrading trend - investigate")
elif scenario_is_flaky:
    print("⚠ Flaky behavior - improve stability")
else:
    print("✓ Healthy scenario")
```

### 8. Archive Historical Data

Keep long-term trends for retrospectives:

```bash
# Monthly trend archive
mkdir -p archives/trends
mcprobe trends --window 100 > "archives/trends/$(date +%Y-%m).txt"
```

## Related Documentation

- [CLI Analysis Commands](../cli/analysis.md) - Complete CLI reference
- [Flaky Test Detection](flaky-detection.md) - Detecting inconsistent tests
- [Stability Checking](stability.md) - Scenario stability metrics
- [Reporting](../reporting/formats.md) - Generating reports from trends

## Technical Reference

**Source code:**
- `/Users/kiener/code/mcprobe/src/mcprobe/analysis/trends.py` - TrendAnalyzer implementation
- `/Users/kiener/code/mcprobe/src/mcprobe/analysis/models.py` - Data models

**Key constants:**
```python
MIN_DATA_POINTS_FOR_TREND = 3
MIN_DATA_POINTS_FOR_REGRESSION = 4
MIN_DATA_POINTS_FOR_ANALYSIS = 2
SEVERITY_HIGH_THRESHOLD = 0.3
SEVERITY_MEDIUM_THRESHOLD = 0.15
```

**Default parameters:**
```python
slope_threshold = 0.05          # TrendAnalyzer
window_size = 10                # analyze_scenario()
pass_rate_threshold = 0.1       # detect_regressions()
score_threshold = 0.1           # detect_regressions()
```
