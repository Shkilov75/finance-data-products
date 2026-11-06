-- Staged DDL (engine: duckdb). Control views = raw side of the completeness gate (ADR-0002).
-- Written separately from raw.typed_*: one row per RAW entry (unreadable ones included),
-- signed_amount NULL when the entry is unreadable (date, key, currency, account or amount), so it counts as an entry but adds to no total.
-- Independent expressions on purpose (try_strptime of the whole string, no shared regex).

CREATE OR REPLACE VIEW raw.control_erp_a AS
WITH r AS (
    SELECT
        trim(belegnummer) AS document,
        try_cast(trim(zeile) AS INTEGER) AS line,
        try_cast(try_strptime(trim(buchungsdatum), '%d.%m.%Y') AS DATE) AS entry_date,
        nullif(trim(waehrung), '') AS currency,
        nullif(trim(konto), '') AS local_account,
        nullif(trim(sollbetrag), '') AS s,
        nullif(trim(habenbetrag), '') AS h
    FROM raw.erp_a_export
),
n AS (
    SELECT *,
        try_cast(replace(replace(s, '.', ''), ',', '.') AS DECIMAL(18,2)) AS dv,
        try_cast(replace(replace(h, '.', ''), ',', '.') AS DECIMAL(18,2)) AS cv,
        -- scale check: the text after the decimal comma has at most 2 digits
        coalesce(length(split_part(s, ',', 2)), 0) <= 2 AS s_scale_ok,
        coalesce(length(split_part(h, ',', 2)), 0) <= 2 AS h_scale_ok
    FROM r
)
SELECT
    'ERP_A' AS source_system, document, line, currency, entry_date, local_account,
    CASE WHEN entry_date IS NULL OR line IS NULL OR document = ''
              OR currency IS NULL OR local_account IS NULL THEN NULL
         WHEN s IS NOT NULL AND h IS NULL AND dv > 0 AND s_scale_ok AND s NOT LIKE '%-%' THEN dv
         WHEN h IS NOT NULL AND s IS NULL AND cv > 0 AND h_scale_ok AND h NOT LIKE '%-%' THEN -cv
    END AS signed_amount
FROM n;

CREATE OR REPLACE VIEW raw.control_erp_b AS
WITH r AS (
    SELECT
        trim(d.doc_id) AS document,
        try_cast(trim(d.l.line_no) AS INTEGER) AS line,
        try_cast(try_strptime(trim(d.posting_date), '%m/%d/%Y') AS DATE) AS entry_date,
        nullif(trim(d.currency), '') AS currency,
        nullif(trim(d.l.account), '') AS local_account,
        nullif(trim(d.l.amount), '') AS a
    FROM (SELECT doc_id, posting_date, currency, unnest(lines) AS l FROM raw.erp_b_export) AS d
)
SELECT
    'ERP_B' AS source_system, document, line, currency, entry_date, local_account,
    CASE WHEN entry_date IS NULL OR line IS NULL OR document = ''
              OR currency IS NULL OR local_account IS NULL THEN NULL
         WHEN coalesce(length(split_part(a, '.', 2)), 0) <= 2
              AND try_cast(replace(a, ',', '') AS DECIMAL(18,2)) <> 0
         THEN try_cast(replace(a, ',', '') AS DECIMAL(18,2)) END AS signed_amount
FROM r;
