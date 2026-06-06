# Branch Summaries — Convention Guide

**Maintained by:** Devandra (P5 — Documentation & Integration Lead)

---

## Branching Convention

Every person creates **one branch per day** for their work. Branch names follow this format:

```
p<person_number>/day<day_number>-<short-description>
```

### Examples

| Person | Branch Name |
|--------|------------|
| P1 Anjana   | `p1/day1-env-setup-qiskit-numa` |
| P2 Hari     | `p2/day1-repo-scaffold-task-runner` |
| P3 Smarth   | `p3/day1-task-model-scheduler-stubs` |
| P4 Vikas    | `p4/day1-metrics-schema-results-dir` |
| P5 Devandra | `p5/day1-docs-report-skeleton-requirements` |

---

## Rules

1. **Never push directly to `main`.** All work goes through Pull Requests.
2. **One PR per branch.** Do not stack branches on top of each other.
3. **Push your branch by 6 PM each day** — P5 runs the daily integration test at 6:30 PM.
4. **PR description must include:**
   - What was done
   - What files were created/modified
   - Any blockers or dependencies on another person's branch
5. **P5 reviews and merges** all PRs after the daily integration test.

---

## Branch Summary Document

When closing your branch (after PR is merged), create a summary document here:

**File:** `docs/branch_summaries/<branch-name>.md`

**Template:**
```markdown
# Branch: p<N>/day<D>-<description>

**Author:** <Name>  
**Day:** Day <D>  
**Merged:** [Yes/No] [Date]

## What Was Done
- 

## Files Created / Modified
- 

## Tests Written
- 

## Known Issues / Blockers
- 

## Notes for Next Day
- 
```

---

## Daily Integration Test (Run by P5 at 6:30 PM)

```bash
# 1. Pull all merged PRs into main
git checkout main && git pull

# 2. Install/verify dependencies
pip install -r requirements.txt

# 3. Import check
python -c "import qiskit, openqaoa, pyqubo, numpy, pandas, networkx, matplotlib, psutil"

# 4. Run all tests
pytest tests/ -v

# 5. Report status in team chat
```

---

*If your branch is not pushed by 6 PM, your tasks roll over with a flag in the next day's plan.*
