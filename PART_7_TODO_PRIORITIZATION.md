# Part 7: TODO Prioritization Matrix

## Goal

Determine and prioritize the remaining TODOs for the MTA Ridership Recovery Dashboard.

## Method

This draft uses an impact/effort matrix:

- **Impact**: How much the task protects the course requirements, final dashboard quality, data reliability, or submission readiness.
- **Effort**: How much implementation time, coordination, and testing the task will likely require.

## Prioritization Matrix

| | **Low Effort** | **Higher Effort** |
|---|---|---|
| **High Impact** | **Do first**<br><br>1. Verify the scheduled ETL workflow has a successful GitHub Actions run.<br>2. Capture evidence for Part 6: green workflow run, ETL logs, row counts, and date ranges.<br>3. Protect credentials: make sure service account keys stay out of git and only GitHub Secrets / local Streamlit secrets are used.<br>4. Add a quick BigQuery freshness check query to the documentation. | **Schedule next**<br><br>1. Add ETL guardrails before replacing production tables: validate row counts, date ranges, and required columns before upload.<br>2. Remove the 50,000-row source API limit risk by adding pagination or a full-row-count check.<br>3. Add a combined MTA + COVID analysis view so the dashboard directly answers the third research question.<br>4. Expand validation and tests to cover both current MTA column names and the COVID dataset. |
| **Lower Impact** | **Do if time**<br><br>1. Update README links for Part 6, Part 7, and the data-flow diagram.<br>2. Add final dashboard screenshots or a short demo recording for presentation/submission.<br>3. Rename the notebook file to remove the extra space in `mta_ridership_project .ipynb` if the team still uses it. | **Defer / parking lot**<br><br>1. Build a forecasting model for future ridership.<br>2. Add many more external datasets beyond MTA and COVID.<br>3. Build a full operational monitoring dashboard for ETL health.<br>4. Create an admin interface for rerunning ETL jobs or managing credentials. |

## Final Priority Order

| Priority | TODO | Owner | Acceptance Criteria |
|---|---|---|---|
| P0 | Verify Part 6 scheduled ETL | TBD | GitHub Actions shows a successful `Scheduled ETL` run, and logs show row counts plus min/max dates for both BigQuery tables. |
| P0 | Save submission evidence | TBD | A screenshot or link is ready for CourseWorks showing the successful workflow run and this matrix. |
| P0 | Protect credentials | TBD | No local service account JSON or Streamlit secret file is committed; production credentials are stored in `GCP_SA_KEY` GitHub Secret. |
| P1 | Add ETL guardrails | TBD | The loader refuses to replace BigQuery tables when a source fetch is empty, truncated, missing required columns, or outside the expected date range. |
| P1 | Handle API pagination / 50,000-row limit | TBD | The ETL loads all source rows or fails loudly when the source count exceeds the rows pulled. |
| P1 | Add combined MTA + COVID analysis | TBD | The Streamlit app includes one view aligning COVID cases and transit recovery by date, with a clear chart or summary that addresses research question 3. |
| P1 | Expand validation coverage | TBD | Tests cover current `_pct_of_comparable_pre_pandemic_day` MTA columns, legacy column aliases, and COVID case fields. |
| P2 | Polish documentation and final media | TBD | README links to the workflow/writeups, and the team has screenshots or a short demo of the final dashboard. |
| P3 | Optional advanced analysis | TBD | Forecasting, extra datasets, or monitoring UI are only started after P0-P2 items are complete. |

## Evidence We Used

- `PART_6_WRITEUP.md` identifies the main reliability risks: full refresh overwrite risk, no retry logic, secret expiration, schema drift, and the 50,000-row source API limit.
- `.github/workflows/etl.yml` now runs the ETL daily and supports manual runs through `workflow_dispatch`.
- `load_data_to_bq.py` currently does a full table replacement with `if_exists="replace"`, so pre-upload validation is the most important next engineering improvement.
- The dashboard currently has a strong MTA analysis flow and a separate COVID page; combining them would better answer the third research question.
- Local verification on 2026-04-22: `.venv/bin/python -m pytest` passed 10 tests, and `.venv/bin/python -m ruff check .` passed.

## Meeting Notes To Confirm

Participants:

- Haixin Liu
- Hanghai Li

Recommended decisions:

- P0 items must be completed before final submission evidence is collected.
- P1 items are the next development tasks if the project continues.
- P2 items improve presentation quality after reliability and research coverage are handled.
- P3 items are intentionally deferred unless all higher priorities are complete.
