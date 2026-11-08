-- Gate: completeness (AC-07, AC-08, AC-09). Zero rows = PASS.
-- Compares the independent raw side (raw.control_erp_*) with the aligned entries
-- (staging.ledger_entry). One gate, two kinds of rows, one message per row:
--   1. per source system and transaction currency: difference in entry count, debit total or
--      credit total (debit total = sum of positive amounts, credit total = sum of the negated
--      negative amounts; the signed total is never used, balanced documents always sum to 0);
--   2. per entry matched by source system, document and line: missing in the aligned entries,
--      present only in the aligned entries, or date / signed amount / local account differs
--      (two entries that exchanged amounts leave the totals unchanged and are found here).
-- An unreadable raw entry counts as an entry and adds nothing to the totals, so it shows as missing.
WITH raw_entry AS (
    SELECT source_system, document, line, coalesce(currency, 'UNKNOWN') AS currency,
           entry_date, local_account, signed_amount
    FROM raw.control_erp_a
    UNION ALL
    SELECT source_system, document, line, coalesce(currency, 'UNKNOWN') AS currency,
           entry_date, local_account, signed_amount
    FROM raw.control_erp_b
),
aligned AS (
    SELECT source_system, source_document AS document, source_line AS line,
           transaction_currency AS currency, entry_date, local_account, signed_amount
    FROM staging.ledger_entry
),
raw_total AS (
    SELECT source_system, currency, count(*) AS entries,
           coalesce(sum(CASE WHEN signed_amount > 0 THEN signed_amount END), 0) AS debit_total,
           coalesce(sum(CASE WHEN signed_amount < 0 THEN -signed_amount END), 0) AS credit_total
    FROM raw_entry GROUP BY source_system, currency
),
aligned_total AS (
    SELECT source_system, currency, count(*) AS entries,
           coalesce(sum(CASE WHEN signed_amount > 0 THEN signed_amount END), 0) AS debit_total,
           coalesce(sum(CASE WHEN signed_amount < 0 THEN -signed_amount END), 0) AS credit_total
    FROM aligned GROUP BY source_system, currency
),
total_diff AS (
    SELECT coalesce(r.source_system, a.source_system) AS source_system,
           coalesce(r.currency, a.currency) AS currency,
           coalesce(r.entries, 0) AS raw_entries, coalesce(a.entries, 0) AS aligned_entries,
           coalesce(r.debit_total, 0) AS raw_debit, coalesce(a.debit_total, 0) AS aligned_debit,
           coalesce(r.credit_total, 0) AS raw_credit, coalesce(a.credit_total, 0) AS aligned_credit
    FROM raw_total AS r
    FULL OUTER JOIN aligned_total AS a
      ON a.source_system = r.source_system AND a.currency = r.currency
),
findings AS (
    SELECT 1 AS grp, source_system AS k1, currency AS k2, 1 AS k3,
           source_system || ' ' || currency || ' entries: raw ' || CAST(raw_entries AS STRING)
           || ', aligned ' || CAST(aligned_entries AS STRING) AS message
    FROM total_diff WHERE raw_entries <> aligned_entries
    UNION ALL
    SELECT 1, source_system, currency, 2,
           source_system || ' ' || currency || ' debit_total: raw ' || CAST(raw_debit AS STRING)
           || ', aligned ' || CAST(aligned_debit AS STRING)
    FROM total_diff WHERE raw_debit <> aligned_debit
    UNION ALL
    SELECT 1, source_system, currency, 3,
           source_system || ' ' || currency || ' credit_total: raw ' || CAST(raw_credit AS STRING)
           || ', aligned ' || CAST(aligned_credit AS STRING)
    FROM total_diff WHERE raw_credit <> aligned_credit
    UNION ALL
    SELECT 2, r.source_system, coalesce(r.document, '?'), coalesce(r.line, -1),
           r.source_system || ' ' || coalesce(r.document, '?') || ' line '
           || coalesce(CAST(r.line AS STRING), '?') || ': missing in aligned entries'
    FROM raw_entry AS r
    LEFT JOIN aligned AS a
           ON a.source_system = r.source_system AND a.document = r.document AND a.line = r.line
    WHERE a.document IS NULL
    UNION ALL
    SELECT 3, a.source_system, a.document, a.line,
           a.source_system || ' ' || a.document || ' line ' || CAST(a.line AS STRING)
           || ': in aligned entries but not in raw data'
    FROM aligned AS a
    LEFT JOIN raw_entry AS r
           ON a.source_system = r.source_system AND a.document = r.document AND a.line = r.line
    WHERE r.document IS NULL
    UNION ALL
    SELECT 4, r.source_system, r.document, r.line,
           r.source_system || ' ' || r.document || ' line ' || CAST(r.line AS STRING)
           || ': entry_date differs: raw ' || coalesce(CAST(r.entry_date AS STRING), 'unreadable')
           || ', aligned ' || CAST(a.entry_date AS STRING)
    FROM raw_entry AS r
    JOIN aligned AS a
      ON a.source_system = r.source_system AND a.document = r.document AND a.line = r.line
    WHERE r.entry_date IS DISTINCT FROM a.entry_date
    UNION ALL
    SELECT 5, r.source_system, r.document, r.line,
           r.source_system || ' ' || r.document || ' line ' || CAST(r.line AS STRING)
           || ': signed_amount differs: raw ' || coalesce(CAST(r.signed_amount AS STRING), 'unreadable')
           || ', aligned ' || CAST(a.signed_amount AS STRING)
    FROM raw_entry AS r
    JOIN aligned AS a
      ON a.source_system = r.source_system AND a.document = r.document AND a.line = r.line
    WHERE r.signed_amount IS DISTINCT FROM a.signed_amount
    UNION ALL
    SELECT 6, r.source_system, r.document, r.line,
           r.source_system || ' ' || r.document || ' line ' || CAST(r.line AS STRING)
           || ': local_account differs: raw ' || coalesce(r.local_account, 'unreadable')
           || ', aligned ' || a.local_account
    FROM raw_entry AS r
    JOIN aligned AS a
      ON a.source_system = r.source_system AND a.document = r.document AND a.line = r.line
    WHERE r.local_account IS DISTINCT FROM a.local_account
)
SELECT message
FROM findings
ORDER BY grp, k1, k2, k3, message;
