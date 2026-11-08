-- DuckDB adapter. Control views = raw side of the completeness gate (ADR-0002).
-- Written separately from raw.typed_*: one row per RAW entry (unreadable ones included),
-- signed_amount NULL when the entry is unreadable (date, key, currency, account or amount), so it counts as an entry but adds to no total.
-- Independent expressions on purpose: a date is read by formatting the parsed date back to the
-- source text, line and amount formats are full-match patterns written here, not shared with raw.typed_*.
-- line_text keeps the trimmed source text of the line so a duplicate with an unreadable line is still found.

CREATE OR REPLACE VIEW raw.control_erp_a AS
WITH r AS (
    SELECT
        nullif(trim(belegnummer), '') AS document,
        trim(zeile) AS line_text,
        CASE WHEN regexp_full_match(trim(zeile), '[0-9]+') THEN try_cast(trim(zeile) AS INTEGER) END AS line,
        CASE WHEN strftime(try_strptime(trim(buchungsdatum), '%d.%m.%Y'), '%d.%m.%Y') = trim(buchungsdatum)
             THEN try_cast(try_strptime(trim(buchungsdatum), '%d.%m.%Y') AS DATE) END AS entry_date,
        nullif(trim(waehrung), '') AS currency,
        nullif(trim(konto), '') AS local_account,
        nullif(trim(sollbetrag), '') AS s,
        nullif(trim(habenbetrag), '') AS h
    FROM raw.erp_a_export
),
n AS (
    SELECT *,
        CASE WHEN regexp_full_match(s, '([0-9]{1,3}(\.[0-9]{3})*|[0-9]+)(,[0-9]{1,2})?')
             THEN try_cast(replace(replace(s, '.', ''), ',', '.') AS DECIMAL(18,2)) END AS dv,
        CASE WHEN regexp_full_match(h, '([0-9]{1,3}(\.[0-9]{3})*|[0-9]+)(,[0-9]{1,2})?')
             THEN try_cast(replace(replace(h, '.', ''), ',', '.') AS DECIMAL(18,2)) END AS cv
    FROM r
)
SELECT
    'ERP_A' AS source_system, document, line, line_text, currency, entry_date, local_account,
    CASE WHEN entry_date IS NULL OR line IS NULL OR document IS NULL
              OR currency IS NULL OR local_account IS NULL THEN NULL
         WHEN s IS NOT NULL AND h IS NULL AND dv > 0 THEN dv
         WHEN h IS NOT NULL AND s IS NULL AND cv > 0 THEN -cv
    END AS signed_amount
FROM n;

CREATE OR REPLACE VIEW raw.control_erp_b AS
WITH r AS (
    SELECT
        nullif(trim(d.doc_id), '') AS document,
        trim(d.l.line_no) AS line_text,
        CASE WHEN regexp_full_match(trim(d.l.line_no), '[0-9]+') THEN try_cast(trim(d.l.line_no) AS INTEGER) END AS line,
        CASE WHEN strftime(try_strptime(trim(d.posting_date), '%m/%d/%Y'), '%m/%d/%Y') = trim(d.posting_date)
             THEN try_cast(try_strptime(trim(d.posting_date), '%m/%d/%Y') AS DATE) END AS entry_date,
        nullif(trim(d.currency), '') AS currency,
        nullif(trim(d.l.account), '') AS local_account,
        CASE WHEN regexp_full_match(trim(d.l.amount), '-?([0-9]{1,3}(,[0-9]{3})*|[0-9]+)(\.[0-9]{1,2})?')
             THEN try_cast(replace(trim(d.l.amount), ',', '') AS DECIMAL(18,2)) END AS a
    FROM (SELECT doc_id, posting_date, currency, unnest(lines) AS l FROM raw.erp_b_export) AS d
)
SELECT
    'ERP_B' AS source_system, document, line, line_text, currency, entry_date, local_account,
    CASE WHEN entry_date IS NULL OR line IS NULL OR document IS NULL
              OR currency IS NULL OR local_account IS NULL THEN NULL
         WHEN a <> 0 THEN a END AS signed_amount
FROM r;
