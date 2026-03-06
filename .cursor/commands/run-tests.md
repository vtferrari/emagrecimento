# Run All Tests and Fix Failures

Execute the full test suite and fix any failures.

## Steps

1. Run: `pytest -v --tb=short`
2. If any test fails:
   - Read the failure output
   - Fix the code (do not change the test unless it is wrong)
   - Re-run pytest until all pass
3. Report: "All X tests passed" or list remaining failures
