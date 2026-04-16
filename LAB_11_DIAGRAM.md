# Lab 11 Data Flow Diagram

Open this file in Markdown Preview to render the Mermaid diagram.

```mermaid
%%{init: {'theme': 'neutral', 'flowchart': {'curve': 'linear', 'nodeSpacing': 35, 'rankSpacing': 55}}}%%
flowchart TD
    A["MTA operations generate daily ridership and traffic estimates"]:::source
    B["NYC health reporting systems generate daily COVID case counts"]:::source

    C["Open NY API<br/>Dataset: vxuj-8kew"]:::api
    D["NYC Open Data API<br/>Dataset: rc75-m7u3"]:::api

    S["GitHub Actions cron scheduler<br/>Runs daily at 06:00 UTC"]:::scheduler

    E["Python batch loader<br/>load_data_to_bq.py"]:::loader
    F["Cleaning and type conversion<br/>pandas parsing + column renaming"]:::loader
    G["BigQuery tables<br/>mta_data.daily_ridership<br/>mta_data.nyc_covid_cases"]:::storage
    H["Shared query utilities<br/>utils.py"]:::app
    I["Streamlit pages<br/>dashboard + analysis views"]:::app
    J["User-facing output<br/>charts, KPIs, and recovery analysis"]:::output

    R1["Risk: upstream definitions or collection methods change"]:::risk
    R2["Risk: API outage, timeout, or schema drift"]:::risk
    R3["Risk: authentication failure or bad full refresh"]:::risk
    R4["Risk: permissions, cache, or query errors"]:::risk
    R5["Risk: secret expired or workflow disabled by GitHub"]:::risk

    A --> C
    B --> D
    S --> E
    C --> E
    D --> E
    E --> F --> G --> H --> I --> J

    A -.-> R1
    B -.-> R1
    C -.-> R2
    D -.-> R2
    S -.-> R5
    E -.-> R3
    G -.-> R4
    H -.-> R4
    I -.-> R4

    classDef source fill:#d2e3fc,stroke:#5b9cf6,color:#202124,stroke-width:2px;
    classDef api fill:#e4d7ff,stroke:#8b5cf6,color:#202124,stroke-width:2px;
    classDef loader fill:#fde7c3,stroke:#f59e0b,color:#202124,stroke-width:2px;
    classDef storage fill:#fbd3d0,stroke:#e56b5d,color:#202124,stroke-width:2px;
    classDef app fill:#d7f1ea,stroke:#2ea76d,color:#202124,stroke-width:2px;
    classDef output fill:#dbeafe,stroke:#3b82f6,color:#202124,stroke-width:2px;
    classDef scheduler fill:#e0f2fe,stroke:#0284c7,color:#202124,stroke-width:2px;
    classDef risk fill:#fff4cc,stroke:#d97706,color:#7c2d12,stroke-width:2px;
```

## What Happens

- A GitHub Actions cron job triggers the ETL workflow daily at 06:00 UTC.
- Two upstream organizations generate the source data.
- The workflow pulls both datasets from public JSON APIs.
- `load_data_to_bq.py` authenticates via a GCP service account secret, cleans the data, and fully refreshes two BigQuery tables.
- `utils.py` queries BigQuery and prepares data for the app.
- Streamlit renders charts and analysis for the user.
- The workflow can also be triggered manually via `workflow_dispatch`.

## What Can Go Wrong

- Source definitions or field names may change upstream.
- Public APIs may fail, timeout, or return unexpected schemas.
- A failed batch load can overwrite a previously good table.
- BigQuery permissions, caching, or app queries may fail.
- The GCP service account key stored in GitHub Secrets may expire or be revoked.
- GitHub may automatically disable the scheduled workflow after 60 days of repo inactivity.

If Mermaid Preview is unavailable, use [LAB_11_DIAGRAM.svg](./LAB_11_DIAGRAM.svg) as the screenshot version.
