# Demo Plan & Sales Script

## MSSQL → Snowflake Data Migration Tool

---

## Pre-Demo Setup (5 minutes before)

1. **Clean Snowflake** — truncate all tables (data + logs) so counts start at zero
2. **Clean Azure Blob** — remove all files from the stage
3. **Prepare MSSQL** — ensure test data is seeded (100 customers, 500 orders, 50 products)
4. **Open the Streamlit app** — have Configuration tab visible on screen
5. **Open Snowflake Snowsight** — have ANALYTICS.PUBLIC schema visible in a second browser tab (for live verification)

### Quick Reset Commands

```sql
-- Snowflake cleanup
TRUNCATE TABLE DATA_MIGRATION.CONTROL.CONFIG_TABLE;
TRUNCATE TABLE DATA_MIGRATION.CONTROL.LOG_TABLE;
TRUNCATE TABLE ANALYTICS.PUBLIC.CUSTOMERS;
TRUNCATE TABLE ANALYTICS.PUBLIC.ORDERS;
TRUNCATE TABLE ANALYTICS.PUBLIC.PRODUCTS;

-- Verify clean
SELECT 'CONFIG' AS TBL, COUNT(*) FROM DATA_MIGRATION.CONTROL.CONFIG_TABLE
UNION ALL SELECT 'LOG', COUNT(*) FROM DATA_MIGRATION.CONTROL.LOG_TABLE
UNION ALL SELECT 'CUSTOMERS', COUNT(*) FROM ANALYTICS.PUBLIC.CUSTOMERS
UNION ALL SELECT 'ORDERS', COUNT(*) FROM ANALYTICS.PUBLIC.ORDERS
UNION ALL SELECT 'PRODUCTS', COUNT(*) FROM ANALYTICS.PUBLIC.PRODUCTS;

-- Clean stage files
REMOVE @DATA_MIGRATION.CONTROL.MIGRATION_STAGE/CUSTOMERS/;
REMOVE @DATA_MIGRATION.CONTROL.MIGRATION_STAGE/ORDERS/;
REMOVE @DATA_MIGRATION.CONTROL.MIGRATION_STAGE/PRODUCTS/;
```

---

## Demo Script (20 minutes)

### Opening — The Problem (2 min)

> "Today, migrating data from Azure SQL to Snowflake typically involves:
>
> - Writing custom scripts per table
> - Manually handling CDC logic, deduplication, and file cleanup
> - No visibility into what ran, what failed, or what's stale
> - Every new table means 2-3 days of developer effort
>
> We've built a **self-service migration console** that eliminates all of that."

---

### Act 1 — Configuration (3 min)

**Show the Configuration tab.**

> "Adding a new table takes 30 seconds, not 3 days."

**Live action**: Add the CUSTOMERS table config:
- Source: `TestDB.dbo.Customers`
- Target: `ANALYTICS.PUBLIC.CUSTOMERS`
- Load type: Full
- SCD Type: 1 (upsert)
- Primary Key: `CustomerID`

> "Notice it auto-syncs to Snowflake's CONFIG_TABLE — no separate config management step."

**Switch to Snowsight** → Query:
```sql
SELECT * FROM DATA_MIGRATION.CONTROL.CONFIG_TABLE;
```
→ Show the row appeared.

> "This is a single source of truth. Any team member, any server — same config."

---

### Act 2 — Execution (5 min)

**Switch to Run tab. Select all 3 tables. Mode = FULL. Click Start.**

> "We're now running 3 tables in parallel. Under the hood:
>
> 1. BCP extracts data directly from Azure SQL
> 2. Files are compressed and uploaded to Azure Blob
> 3. Snowflake COPY INTO loads them into work tables
> 4. Atomic SWAP replaces the target — zero downtime for readers
> 5. Files move to processed/ — no duplicates on next run"

**Watch the progress bar fill.** Call out the real-time counter: `2/3 completed...`

> "Total time for 650 rows across 3 tables — under 60 seconds. At scale, this runs 100+ tables in parallel with configurable thread pools."

**When complete**, show the results panel:

| Table | Status | Source Count | Target Count | Duration |
|---|---|---|---|---|
| CUSTOMERS | SUCCESS | 100 | 100 | 12s |
| ORDERS | SUCCESS | 500 | 500 | 18s |
| PRODUCTS | SUCCESS | 50 | 50 | 9s |

> "Source and target counts match exactly. That's the integrity guarantee."

---

### Act 3 — Verification (2 min)

**Switch to Snowsight:**

```sql
SELECT COUNT(*) FROM ANALYTICS.PUBLIC.CUSTOMERS;  -- 100
SELECT COUNT(*) FROM ANALYTICS.PUBLIC.ORDERS;     -- 500
SELECT COUNT(*) FROM ANALYTICS.PUBLIC.PRODUCTS;   -- 50
```

> "Live data, verified. Now let's look at the audit trail."

```sql
SELECT BATCH_ID, MSSQL_TABLE_NAME, FINAL_STATUS,
       MSSQL_TABLE_COUNT, SF_TABLE_COUNT, JOB_DURATION
FROM DATA_MIGRATION.CONTROL.LOG_TABLE;
```

> "Every run is logged — who ran what, when, how long, how many rows. Full compliance trail."

---

### Act 4 — Incremental CDC (5 min)

> "Now the real power — handling changes without moving the entire table."

---

#### Step 4.1 — Show Current State in Snowflake

**Switch to Snowsight:**

```sql
SELECT COUNT(*) FROM ANALYTICS.PUBLIC.CUSTOMERS;  -- 100
SELECT COUNT(*) FROM ANALYTICS.PUBLIC.ORDERS;     -- 500
```

> "We have our baseline. Now let's simulate real-world changes in the source system."

---

#### Step 4.2 — Make Changes in MSSQL (Switch to SSMS / Azure Data Studio)

> "I'm going to simulate what happens in production — customers update their profiles, new orders come in."

**Run in MSSQL:**

```sql
USE TestDB;

-- 5 customers update their email and phone
UPDATE dbo.Customers SET
    Email = 'updated_' + CAST(CustomerID AS VARCHAR) + '@newdomain.com',
    Phone = '999-000-' + RIGHT('0000' + CAST(CustomerID AS VARCHAR), 4),
    ModifiedDate = GETDATE()
WHERE CustomerID IN (1, 2, 3, 4, 5);

-- 3 brand new customers sign up
INSERT INTO dbo.Customers (FirstName, LastName, Email, Phone, City, State, Country, CreatedDate, ModifiedDate)
VALUES
    ('Demo', 'NewUser1', 'demo.user1@test.com', '555-0001', 'New York', 'NY', 'USA', GETDATE(), GETDATE()),
    ('Demo', 'NewUser2', 'demo.user2@test.com', '555-0002', 'London', NULL, 'UK', GETDATE(), GETDATE()),
    ('Demo', 'NewUser3', 'demo.user3@test.com', '555-0003', 'Mumbai', 'MH', 'India', GETDATE(), GETDATE());

-- 10 new orders placed
INSERT INTO dbo.Orders (CustomerID, OrderDate, TotalAmount, Status, ShippingAddress, CreatedDate, ModifiedDate)
VALUES
    (1, GETDATE(), 299.99, 'Pending', '123 Demo St, NY', GETDATE(), GETDATE()),
    (2, GETDATE(), 149.50, 'Pending', '456 Test Ave, CA', GETDATE(), GETDATE()),
    (3, GETDATE(), 599.00, 'Confirmed', '789 Live Rd, TX', GETDATE(), GETDATE()),
    (5, GETDATE(), 89.99, 'Pending', '321 Show Ln, WA', GETDATE(), GETDATE()),
    (10, GETDATE(), 450.00, 'Shipped', '654 Prod Blvd, FL', GETDATE(), GETDATE()),
    (15, GETDATE(), 75.25, 'Pending', '987 Run Way, IL', GETDATE(), GETDATE()),
    (20, GETDATE(), 1250.00, 'Confirmed', '147 Scale Dr, CO', GETDATE(), GETDATE()),
    (25, GETDATE(), 34.99, 'Pending', '258 Fast Ct, GA', GETDATE(), GETDATE()),
    (30, GETDATE(), 675.00, 'Shipped', '369 Bulk Pl, AZ', GETDATE(), GETDATE()),
    (50, GETDATE(), 199.99, 'Pending', '741 Batch Rd, OR', GETDATE(), GETDATE());
```

**Verify in MSSQL:**

```sql
SELECT COUNT(*) FROM dbo.Customers;  -- 103
SELECT COUNT(*) FROM dbo.Orders;     -- 510
```

> "Source now has 103 customers (5 updated + 3 new) and 510 orders (10 new). But we don't want to re-move all 103 customers and 510 orders. That's wasteful."

---

#### Step 4.3 — Update Config to Incremental (Switch to Streamlit App)

> "In the Configuration tab, I'll change CUSTOMERS and ORDERS to incremental mode."

**In the app**: Edit each table config:
- Load Type: `incremental`
- CDC Columns: `ModifiedDate`
- CDC Type: `TIMESTAMP`

> "The tool will now look at the last successful run timestamp and only extract rows modified after that point."

---

#### Step 4.4 — Run Incremental Migration (Switch to Run Tab)

**Select CUSTOMERS + ORDERS → Mode = FULL → Click Start.**

> "Watch the source count — it won't be 100 or 500. It will be just the delta."

**When complete**, show results:

| Table | Status | Source Count | Target Count | Duration |
|---|---|---|---|---|
| CUSTOMERS | SUCCESS | 8 | 103 | 8s |
| ORDERS | SUCCESS | 10 | 510 | 6s |

> "8 rows extracted from Customers — 5 updated + 3 new. 10 rows from Orders — all new.
> That's a **92% reduction** in data movement compared to the full load."

---

#### Step 4.5 — Verify in Snowflake (Switch to Snowsight)

```sql
-- Total counts reflect the changes
SELECT COUNT(*) FROM ANALYTICS.PUBLIC.CUSTOMERS;  -- 103
SELECT COUNT(*) FROM ANALYTICS.PUBLIC.ORDERS;     -- 510

-- Updated customers have new values (SCD1 = overwrite)
SELECT CustomerID, Email, Phone
FROM ANALYTICS.PUBLIC.CUSTOMERS
WHERE CustomerID IN (1, 2, 3, 4, 5);
-- Email: updated_1@newdomain.com, updated_2@newdomain.com...

-- New customers were inserted
SELECT * FROM ANALYTICS.PUBLIC.CUSTOMERS WHERE FirstName = 'Demo';
-- 3 new rows

-- Compare run history: Full vs Incremental
SELECT
    BATCH_ID, MSSQL_TABLE_NAME, LOAD_TYPE,
    MSSQL_TABLE_COUNT AS ROWS_MOVED,
    JOB_DURATION AS SECONDS
FROM DATA_MIGRATION.CONTROL.LOG_TABLE
ORDER BY JOB_START_TIME;
```

> "Look at the LOG_TABLE — first run moved 100 rows, second run moved only 8. Same table, 92% less work. At enterprise scale with millions of rows, this saves hours of compute time and significant Snowflake credits."

---

#### Step 4.6 — Key Talking Point

> "The tool automatically tracks the high-watermark. Every successful run's timestamp is stored in LOG_TABLE. The next incremental run picks up exactly where the last one left off. No manual bookkeeping. No missed rows. No duplicates."

---

### Act 5 — SCD Type 2 History (2 min, optional)

> "For tables that need full change history — like customer addresses, pricing, or compliance data — we support SCD Type 2."

> "Instead of overwriting the old row, we:
> 1. Mark it as expired (`IS_CURRENT = FALSE`, `EFF_END_DATE = now`)
> 2. Insert the new version (`IS_CURRENT = TRUE`, `EFF_START_DATE = now`)
>
> You can always answer: 'What was this customer's email last month?'"

**If time permits — show in Snowflake:**

```sql
-- After SCD2 run, CustomerID=1 has 2 rows:
SELECT CustomerID, Email, IS_CURRENT, EFF_START_DATE, EFF_END_DATE
FROM ANALYTICS.PUBLIC.CUSTOMERS
WHERE CustomerID = 1
ORDER BY EFF_START_DATE DESC;
-- Row 1: new email, IS_CURRENT=TRUE, EFF_END_DATE=NULL
-- Row 2: old email, IS_CURRENT=FALSE, EFF_END_DATE=<timestamp>
```

> "Full audit trail at the row level. Regulators love this."

---

### Closing — The Business Case (2 min)

> "To summarize what we're delivering:"

| Without This Tool | With This Tool |
|---|---|
| 2-3 days per table | 30 seconds per table |
| Manual scripts, no reuse | Config-driven, reusable |
| No visibility into failures | Full audit trail + real-time UI |
| Downtime during loads | Zero-downtime atomic swap |
| Developer-only operation | Self-service for ops teams |
| Sequential execution | Parallel — 100+ tables concurrent |

> "The tool is deployment-ready. It runs anywhere — a VM, a container, a scheduled job. One `.env` file change and it points to any environment."

---

## Objection Handling

| Question They'll Ask | Your Answer |
|---|---|
| "What if a run fails midway?" | Each table is independent. Failed tables are logged with the exact step that failed. Re-run just those tables with LOAD mode — no re-extraction needed. |
| "What about large tables (100M+ rows)?" | Files are automatically split into 512MB gzip chunks and uploaded in parallel. Snowflake loads chunks concurrently via COPY INTO. |
| "How do we schedule this?" | The app is the UI layer. The same `pipeline.py` can be called from cron, Airflow, or any scheduler with a one-line Python call. |
| "What about security?" | Credentials are in `.env` (never committed). SAS tokens are time-bound. Snowflake uses role-based access. All connections use TLS. |
| "Can it run without the UI?" | Yes. `pipeline.py` is a standalone Python module. The Streamlit app is optional — you can run headless via CLI or import it into any orchestrator. |
| "What if the target table doesn't exist?" | The tool expects tables to exist (DDL is a one-time setup). Auto-DDL generation can be added as a Phase 2 enhancement. |
| "How does it handle schema changes?" | Today it requires manual config update. Phase 2 can add schema drift detection and auto-ALTER. |
| "What's the cost impact?" | Incremental loads reduce data movement by 90%+. Work-table pattern avoids scanning production tables. Parallel execution reduces warehouse active time. |

---

## One-Liner Pitches (Use Situationally)

**For CTO / VP Engineering:**
> "We've eliminated 90% of the manual effort in MSSQL-to-Snowflake migration — config-driven, parallel, auditable, and deployable in under an hour."

**For Data Engineering Lead:**
> "Self-service migration console with BCP extraction, SCD merge logic, atomic loads, and a full audit trail — no more one-off scripts per table."

**For Business / Analytics Manager:**
> "Your team can add a new table to the pipeline in 30 seconds and trust that the numbers match — source count equals target count, every time."

**For Security / Compliance:**
> "Every migration run is logged with timestamps, row counts, SQL statements used, and pass/fail status. Full traceability from source to target."

---

## ROI Narrative

### Time Savings

```
Traditional approach:
  - 2-3 days per table (scripting + testing + debugging)
  - 100 tables = 200-300 developer days

With this tool:
  - 30 seconds per table (config only)
  - 100 tables = 1 hour of configuration
  - Ongoing runs: fully automated
```

### Risk Reduction

- **Zero-downtime loads** — production queries are never interrupted
- **Atomic operations** — a failed load doesn't leave partial data
- **Automatic deduplication** — files move to processed/ after load, can't be double-loaded
- **Source-target count validation** — discrepancies are visible immediately

### Cost Optimization

- **Incremental CDC** — move only changed rows, not full tables
- **GZip compression** — 60-80% reduction in blob storage and network transfer
- **Parallel execution** — warehouse runs for minutes, not hours
- **Work-table pattern** — no scanning of production tables during merge

---

## Phase 2 Roadmap (if asked)

| Feature | Value |
|---|---|
| Auto-DDL generation | Create target tables from source schema automatically |
| Schema drift detection | Alert when source schema changes, auto-ALTER target |
| Scheduling via Airflow/Cron | Headless execution with built-in retry logic |
| Email/Slack notifications | Alert on failure or count mismatch |
| Data quality checks | Row count thresholds, null checks, referential integrity |
| Multi-source support | Add PostgreSQL, MySQL, Oracle as sources |
| Encryption at rest | Encrypt sensitive columns before upload |

---

## Demo Checklist

```
□ MSSQL test data seeded (650 rows across 3 tables)
□ Snowflake tables exist but are empty
□ Azure Blob is clean (no leftover files)
□ .env credentials working (test with a quick BCP)
□ BCP and azcopy installed and accessible
□ Streamlit app running on port 8501
□ Snowsight open in second tab for live verification
□ SSMS / Azure Data Studio open for MSSQL changes (Act 4)
□ demo_queries.sql open in Snowsight worksheet (for quick copy-paste)
□ Screen sharing configured (if remote demo)
□ Backup plan: screenshots of successful run (if live demo fails)
```

---

## Demo Flow Summary (Visual)

```
┌────────────────────────────────────────────────────────────────────┐
│                         20-MINUTE DEMO                              │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  [2 min] THE PROBLEM                                               │
│     ↓                                                              │
│  [3 min] ACT 1: CONFIG (Streamlit → Snowsight verify)              │
│     ↓                                                              │
│  [5 min] ACT 2: FULL LOAD (Streamlit Run → parallel execution)     │
│     ↓                                                              │
│  [2 min] ACT 3: VERIFY (Snowsight → counts + audit trail)          │
│     ↓                                                              │
│  [5 min] ACT 4: INCREMENTAL (MSSQL changes → run → verify delta)   │
│     ↓                                                              │
│  [2 min] ACT 5: SCD2 HISTORY (optional, if audience cares)         │
│     ↓                                                              │
│  [2 min] CLOSING (business case + ROI)                              │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘

WINDOWS TO SWITCH BETWEEN:
  [Ctrl+1] VS Code / Terminal     — show code structure
  [Ctrl+2] Snowsight              — verify data, audit trail
  [Ctrl+3] Streamlit App          — config, run, results
  [Ctrl+4] SSMS / Azure Data Studio — MSSQL source changes
```
