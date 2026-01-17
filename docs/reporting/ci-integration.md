# CI/CD Integration Guide

MCProbe integrates seamlessly with continuous integration and continuous deployment (CI/CD) systems through JUnit XML reports and test result artifacts. This guide covers complete integration examples for popular CI platforms.

## JUnit XML for CI Systems

### Overview

JUnit XML is a widely-supported format that CI systems can parse to:
- Display test results in the UI
- Track test trends over time
- Fail builds based on test results
- Generate test reports and badges
- Integrate with third-party reporting tools

### Generating JUnit XML with Pytest

The pytest plugin automatically generates JUnit XML:

```bash
pytest scenarios/ --junit-xml=junit.xml
```

This creates a `junit.xml` file that CI systems can consume.

### Generating JUnit XML from Results

You can also generate JUnit XML from saved results:

```bash
mcprobe report --format junit --output junit.xml
```

## GitHub Actions

### Complete Workflow Example

Create `.github/workflows/mcprobe.yml`:

```yaml
name: MCProbe Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:
    inputs:
      run_scenarios:
        description: 'Run MCProbe scenario tests (requires Ollama)'
        required: false
        default: 'false'
        type: boolean

env:
  UV_CACHE_DIR: /tmp/.uv-cache
  PYTHON_VERSION: "3.12"

jobs:
  scenarios:
    name: Scenario Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          version: "latest"

      - name: Restore uv cache
        uses: actions/cache@v4
        with:
          path: /tmp/.uv-cache
          key: uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}
          restore-keys: |
            uv-${{ runner.os }}-

      - name: Set up Python
        run: uv python install ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: uv sync --frozen --dev

      - name: Install Ollama
        run: curl -fsSL https://ollama.com/install.sh | sh

      - name: Start Ollama
        run: |
          ollama serve &
          sleep 5

      - name: Pull model
        run: ollama pull llama3.2

      - name: Run scenario tests
        run: uv run pytest scenarios/ -v --junit-xml=scenario-results.xml
        continue-on-error: true

      - name: Generate HTML report
        run: uv run mcprobe report --format html --output report.html
        if: always()

      - name: Upload scenario results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: scenario-results
          path: |
            scenario-results.xml
            report.html
            test-results/

      - name: Minimize uv cache
        run: uv cache prune --ci
```

### Key Features

**Test Result Reporting:**
- JUnit XML is automatically parsed by GitHub
- Results appear in the "Tests" tab
- Failed tests show detailed error messages

**Artifact Upload:**
- HTML reports are preserved
- Test results directory is saved
- Available for download from Actions UI

**Cache Management:**
- UV cache is shared across runs
- Speeds up dependency installation

**Manual Triggers:**
- `workflow_dispatch` allows manual runs
- Useful for on-demand testing

### Viewing Results

1. **Tests Tab**: View pass/fail status and details
2. **Artifacts Section**: Download reports and results
3. **Workflow Summary**: See overview of test execution

## GitLab CI

### Complete Pipeline Example

Create `.gitlab-ci.yml`:

```yaml
stages:
  - test
  - report

variables:
  PYTHON_VERSION: "3.12"

mcprobe_tests:
  stage: test
  image: python:${PYTHON_VERSION}
  before_script:
    - pip install mcprobe pytest
    - curl -fsSL https://ollama.com/install.sh | sh
    - ollama serve &
    - sleep 5
    - ollama pull llama3.2
  script:
    - pytest scenarios/ -v --junit-xml=scenario-results.xml
  after_script:
    - mcprobe report --format html --output report.html
  artifacts:
    when: always
    reports:
      junit: scenario-results.xml
    paths:
      - report.html
      - test-results/
    expire_in: 30 days
  allow_failure: false

generate_trends:
  stage: report
  image: python:${PYTHON_VERSION}
  dependencies:
    - mcprobe_tests
  script:
    - pip install mcprobe
    - mcprobe trends --window 20 > trends-report.txt
  artifacts:
    paths:
      - trends-report.txt
    expire_in: 7 days
  when: always
```

### Key Features

**JUnit Reports Integration:**
- Results appear in GitLab's test report UI
- Trends tracked over time
- Failed tests highlighted

**Artifact Management:**
- Reports preserved for 30 days
- Downloadable from pipeline page
- Automatic cleanup

**Multi-Stage Pipeline:**
- Separate test and reporting stages
- Trend analysis as follow-up
- Dependencies tracked correctly

### Viewing Results

1. **Pipeline View**: See test counts and status
2. **Test Report Tab**: Browse individual test results
3. **Artifacts**: Download HTML reports and results

## Jenkins

### Pipeline Configuration

Create `Jenkinsfile`:

```groovy
pipeline {
    agent any

    environment {
        PYTHON_VERSION = '3.12'
        VENV_DIR = "${WORKSPACE}/venv"
    }

    stages {
        stage('Setup') {
            steps {
                sh '''
                    python${PYTHON_VERSION} -m venv ${VENV_DIR}
                    . ${VENV_DIR}/bin/activate
                    pip install mcprobe pytest
                '''
            }
        }

        stage('Install Ollama') {
            steps {
                sh '''
                    curl -fsSL https://ollama.com/install.sh | sh
                    ollama serve &
                    sleep 5
                    ollama pull llama3.2
                '''
            }
        }

        stage('Run Tests') {
            steps {
                sh '''
                    . ${VENV_DIR}/bin/activate
                    pytest scenarios/ -v --junit-xml=junit.xml
                '''
            }
        }

        stage('Generate Reports') {
            steps {
                sh '''
                    . ${VENV_DIR}/bin/activate
                    mcprobe report --format html --output report.html
                '''
            }
        }
    }

    post {
        always {
            // Publish JUnit test results
            junit 'junit.xml'

            // Publish HTML report
            publishHTML([
                reportDir: '.',
                reportFiles: 'report.html',
                reportName: 'MCProbe Test Report',
                keepAll: true,
                alwaysLinkToLastBuild: true
            ])

            // Archive artifacts
            archiveArtifacts artifacts: 'test-results/**,report.html,junit.xml',
                           allowEmptyArchive: true
        }

        failure {
            // Send notifications on failure
            emailext(
                subject: "MCProbe Tests Failed: ${env.JOB_NAME} - ${env.BUILD_NUMBER}",
                body: "Check console output at ${env.BUILD_URL}",
                to: "team@example.com"
            )
        }
    }
}
```

### Key Features

**Test Result Publishing:**
- JUnit plugin parses results
- Trends displayed on job page
- Test history tracked

**HTML Report Publishing:**
- Reports viewable directly in Jenkins
- Accessible from build page
- Preserved across builds

**Artifact Archiving:**
- All results saved
- Available for download
- Configurable retention

## CircleCI

### Configuration Example

Create `.circleci/config.yml`:

```yaml
version: 2.1

jobs:
  test:
    docker:
      - image: cimg/python:3.12
    steps:
      - checkout

      - restore_cache:
          keys:
            - v1-dependencies-{{ checksum "requirements.txt" }}
            - v1-dependencies-

      - run:
          name: Install dependencies
          command: |
            pip install mcprobe pytest

      - save_cache:
          paths:
            - ./venv
          key: v1-dependencies-{{ checksum "requirements.txt" }}

      - run:
          name: Install Ollama
          command: |
            curl -fsSL https://ollama.com/install.sh | sh
            ollama serve &
            sleep 5
            ollama pull llama3.2

      - run:
          name: Run tests
          command: |
            pytest scenarios/ -v --junit-xml=junit.xml

      - run:
          name: Generate reports
          command: |
            mcprobe report --format html --output report.html
          when: always

      - store_test_results:
          path: junit.xml

      - store_artifacts:
          path: report.html
          destination: reports/

      - store_artifacts:
          path: test-results/
          destination: test-results/

workflows:
  version: 2
  test:
    jobs:
      - test
```

## Azure Pipelines

### Pipeline Configuration

Create `azure-pipelines.yml`:

```yaml
trigger:
  - main

pool:
  vmImage: 'ubuntu-latest'

variables:
  python.version: '3.12'

steps:
- task: UsePythonVersion@0
  inputs:
    versionSpec: '$(python.version)'
  displayName: 'Use Python $(python.version)'

- script: |
    pip install mcprobe pytest
  displayName: 'Install dependencies'

- script: |
    curl -fsSL https://ollama.com/install.sh | sh
    ollama serve &
    sleep 5
    ollama pull llama3.2
  displayName: 'Setup Ollama'

- script: |
    pytest scenarios/ -v --junit-xml=junit.xml
  displayName: 'Run tests'
  continueOnError: true

- script: |
    mcprobe report --format html --output report.html
  displayName: 'Generate HTML report'
  condition: always()

- task: PublishTestResults@2
  inputs:
    testResultsFiles: '**/junit.xml'
    testRunTitle: 'MCProbe Tests'
  condition: always()

- task: PublishBuildArtifacts@1
  inputs:
    pathToPublish: 'report.html'
    artifactName: 'mcprobe-report'
  condition: always()

- task: PublishBuildArtifacts@1
  inputs:
    pathToPublish: 'test-results'
    artifactName: 'test-results'
  condition: always()
```

## Artifact Handling Best Practices

### What to Upload

**Always upload:**
- JUnit XML (for CI parsing)
- HTML reports (for human review)
- Test results directory (for trend analysis)

**Optionally upload:**
- JSON exports (for further analysis)
- Log files
- Screenshots (if applicable)

### Retention Policies

**Short-term (7 days):**
- Development branch results
- Pull request runs
- Debug artifacts

**Long-term (30-90 days):**
- Main branch results
- Release test results
- Production validation runs

**Permanent:**
- Release validation results
- Compliance test records

### Example Retention Configuration

**GitHub Actions:**
```yaml
- name: Upload artifacts
  uses: actions/upload-artifact@v4
  with:
    name: test-results
    path: test-results/
    retention-days: 30  # Customize retention
```

**GitLab CI:**
```yaml
artifacts:
  expire_in: 30 days  # Or "never" for permanent
  paths:
    - test-results/
```

## Fail Thresholds and Quality Gates

### Failing Builds on Test Failures

**Pytest (default behavior):**
```bash
pytest scenarios/  # Exits with code 1 on failure
```

**Custom threshold:**
```bash
pytest scenarios/ --junit-xml=junit.xml || EXIT_CODE=$?

# Calculate pass rate
PASSED=$(grep -c 'status="passed"' junit.xml || echo 0)
TOTAL=$(grep -c '<testcase' junit.xml || echo 1)
PASS_RATE=$((PASSED * 100 / TOTAL))

# Enforce 80% pass rate
if [ $PASS_RATE -lt 80 ]; then
  echo "Pass rate ${PASS_RATE}% is below threshold of 80%"
  exit 1
fi
```

### Quality Gates in Python

```python
from pathlib import Path
from mcprobe.persistence import ResultLoader

loader = ResultLoader(Path("test-results"))
results = loader.load_all(limit=100)

# Calculate metrics
total = len(results)
passed = sum(1 for r in results if r.judgment_result.passed)
pass_rate = passed / total if total > 0 else 0
avg_score = sum(r.judgment_result.score for r in results) / total if total > 0 else 0

# Enforce thresholds
PASS_RATE_THRESHOLD = 0.80
AVG_SCORE_THRESHOLD = 75.0

if pass_rate < PASS_RATE_THRESHOLD:
    print(f"FAIL: Pass rate {pass_rate:.1%} below threshold {PASS_RATE_THRESHOLD:.1%}")
    exit(1)

if avg_score < AVG_SCORE_THRESHOLD:
    print(f"FAIL: Average score {avg_score:.1f} below threshold {AVG_SCORE_THRESHOLD}")
    exit(1)

print(f"PASS: Quality gates met (pass rate: {pass_rate:.1%}, avg score: {avg_score:.1f})")
```

### GitHub Actions Quality Gate Example

```yaml
- name: Run tests
  run: pytest scenarios/ -v --junit-xml=junit.xml
  continue-on-error: true

- name: Check quality gates
  run: |
    python -c "
    from pathlib import Path
    from mcprobe.persistence import ResultLoader

    loader = ResultLoader(Path('test-results'))
    results = loader.load_all()

    passed = sum(1 for r in results if r.judgment_result.passed)
    total = len(results)
    pass_rate = passed / total if total > 0 else 0

    if pass_rate < 0.80:
        print(f'❌ Pass rate {pass_rate:.1%} below 80%')
        exit(1)

    print(f'✅ Pass rate: {pass_rate:.1%}')
    "
```

## Notifications and Alerts

### GitHub Actions - Slack Notification

```yaml
- name: Send Slack notification
  if: failure()
  uses: slackapi/slack-github-action@v1
  with:
    webhook-url: ${{ secrets.SLACK_WEBHOOK }}
    payload: |
      {
        "text": "MCProbe tests failed",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "❌ MCProbe tests failed in *${{ github.repository }}*\n<${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}|View Results>"
            }
          }
        ]
      }
```

### Email Notifications

**Jenkins** (built-in):
```groovy
post {
    failure {
        emailext(
            subject: "MCProbe Tests Failed: ${env.JOB_NAME}",
            body: "See ${env.BUILD_URL} for details",
            to: "team@example.com"
        )
    }
}
```

## Performance Optimization

### Caching Dependencies

**GitHub Actions:**
```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
```

**GitLab CI:**
```yaml
cache:
  paths:
    - .pip-cache/
  key: ${CI_COMMIT_REF_SLUG}
```

### Parallel Execution

Run tests in parallel for faster results:

```bash
pytest scenarios/ -n auto --junit-xml=junit.xml
```

Requires `pytest-xdist`:
```bash
pip install pytest-xdist
```

### Conditional Execution

Run expensive tests only on main branch:

```yaml
- name: Run full test suite
  if: github.ref == 'refs/heads/main'
  run: pytest scenarios/ --junit-xml=junit.xml

- name: Run smoke tests
  if: github.ref != 'refs/heads/main'
  run: pytest scenarios/ -m smoke --junit-xml=junit.xml
```

## Troubleshooting

### JUnit XML Not Recognized

Ensure proper file path:
```bash
pytest scenarios/ --junit-xml=junit.xml
```

Check file exists:
```bash
ls -la junit.xml
```

### Artifacts Not Uploaded

Verify path configuration:
```yaml
- uses: actions/upload-artifact@v4
  with:
    name: results
    path: test-results/  # Must exist
```

Check directory exists:
```bash
mkdir -p test-results
```

### Tests Pass Locally But Fail in CI

Common issues:
- Different Python versions
- Missing dependencies
- Environment-specific configuration
- Timing issues (increase timeouts in CI)

## Next Steps

- [HTML Reports](html-reports.md) - Generate visual reports
- [JSON Export](json-export.md) - Export for custom analysis
- [Pytest Integration](../pytest/integration.md) - Advanced pytest usage
