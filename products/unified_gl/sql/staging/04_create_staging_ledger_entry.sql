-- Engine-neutral SQL (DuckDB and Spark SQL). The aligned entry set (glossary: Aligned entry set).
-- No PRIMARY KEY / UNIQUE on purpose: uniqueness is an invariant check (ADR-0003) so a repeated key
-- stops the run with a typed error that names source system, document and line (AC-06),
-- instead of a generic constraint error from the engine.

CREATE TABLE IF NOT EXISTS staging.ledger_entry (
    entry_id             STRING        NOT NULL,  -- md5(source_system|source_document|source_line)
    source_system        STRING        NOT NULL,  -- 'ERP_A' | 'ERP_B'
    source_document      STRING        NOT NULL,
    source_line          INTEGER       NOT NULL,
    entry_date           DATE          NOT NULL,
    signed_amount        DECIMAL(18,2) NOT NULL,  -- debit > 0, credit < 0, never 0
    transaction_currency STRING        NOT NULL,
    local_account        STRING        NOT NULL,
    group_account        STRING,                 -- NULL = no mapping row (mapping gate, AC-10)
    description          STRING        NOT NULL,  -- common language, original text if untranslated
    original_description STRING        NOT NULL   -- as the source wrote it (needed by AC-02 report)
);

INSERT INTO staging.ledger_entry
WITH unified AS (
    SELECT source_system, document, line, entry_date,
           CASE WHEN debit_filled AND NOT credit_filled THEN debit
                WHEN credit_filled AND NOT debit_filled THEN -credit
           END AS signed_amount,
           currency, local_account, description
    FROM raw.typed_erp_a
    UNION ALL
    SELECT source_system, document, line, entry_date, amount,
           currency, local_account, description
    FROM raw.typed_erp_b
),
readable AS (   -- AC-09: an entry that is not readable is not accepted, the gate reports it lost
    SELECT * FROM unified
    WHERE entry_date IS NOT NULL
      AND signed_amount IS NOT NULL AND signed_amount <> 0
      AND document <> '' AND line IS NOT NULL
      AND currency IS NOT NULL AND local_account IS NOT NULL
)
SELECT
    md5(r.source_system || '|' || r.document || '|' || CAST(r.line AS STRING)) AS entry_id,
    r.source_system,
    r.document,
    r.line,
    r.entry_date,
    r.signed_amount,
    r.currency,
    r.local_account,
    m.group_account,
    coalesce(nullif(t.common_description, ''), r.description),
    r.description
FROM readable AS r
LEFT JOIN raw.account_mapping AS m
       ON m.source_system = r.source_system AND m.local_account = r.local_account
LEFT JOIN raw.description_translation AS t
       ON t.source_system = r.source_system AND t.original_description = r.description
ORDER BY r.source_system, r.document, r.line;
