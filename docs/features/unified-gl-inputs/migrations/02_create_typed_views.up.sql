-- Staged DDL (engine: duckdb). Typed views = the view contract of ADR-0001.
-- Contract: fixed names and types; a value that cannot be read in its source format is NULL, never guessed.
-- ERP A date  DD.MM.YYYY (strict), number German "1.234,56"; at most 2 decimals, no sign.
-- ERP B date  MM/DD/YYYY (strict), number US "-1,234.56"; at most 2 decimals, optional leading minus.

CREATE OR REPLACE VIEW raw.typed_erp_a AS
SELECT
    'ERP_A'                                                        AS source_system,
    trim(belegnummer)                                              AS document,
    TRY_CAST(trim(zeile) AS INTEGER)                               AS line,
    CASE WHEN regexp_matches(trim(buchungsdatum), '^[0-9]{2}\.[0-9]{2}\.[0-9]{4}$')
         THEN TRY_CAST(TRY_STRPTIME(trim(buchungsdatum), '%d.%m.%Y') AS DATE) END
                                                                   AS entry_date,
    coalesce(trim(sollbetrag), '') <> ''                           AS debit_filled,
    coalesce(trim(habenbetrag), '') <> ''                          AS credit_filled,
    CASE WHEN regexp_matches(trim(sollbetrag),
              '^([0-9]{1,3}(\.[0-9]{3})+|[0-9]+)(,[0-9]{1,2})?$')
         THEN TRY_CAST(replace(replace(trim(sollbetrag), '.', ''), ',', '.') AS DECIMAL(18,2)) END
                                                                   AS debit,
    CASE WHEN regexp_matches(trim(habenbetrag),
              '^([0-9]{1,3}(\.[0-9]{3})+|[0-9]+)(,[0-9]{1,2})?$')
         THEN TRY_CAST(replace(replace(trim(habenbetrag), '.', ''), ',', '.') AS DECIMAL(18,2)) END
                                                                   AS credit,
    nullif(trim(waehrung), '')                                     AS currency,
    nullif(trim(konto), '')                                        AS local_account,
    coalesce(trim(buchungstext), '')                               AS description
FROM raw.erp_a_export;

CREATE OR REPLACE VIEW raw.typed_erp_b AS
SELECT
    'ERP_B'                                                        AS source_system,
    trim(d.doc_id)                                                 AS document,
    TRY_CAST(trim(d.l.line_no) AS INTEGER)                         AS line,
    CASE WHEN regexp_matches(trim(d.posting_date), '^[0-9]{2}/[0-9]{2}/[0-9]{4}$')
         THEN TRY_CAST(TRY_STRPTIME(trim(d.posting_date), '%m/%d/%Y') AS DATE) END
                                                                   AS entry_date,
    CASE WHEN regexp_matches(trim(d.l.amount),
              '^-?([0-9]{1,3}(,[0-9]{3})+|[0-9]+)(\.[0-9]{1,2})?$')
         THEN TRY_CAST(replace(trim(d.l.amount), ',', '') AS DECIMAL(18,2)) END
                                                                   AS amount,
    nullif(trim(d.currency), '')                                   AS currency,
    nullif(trim(d.l.account), '')                                  AS local_account,
    coalesce(trim(d.l.memo), '')                                   AS description
FROM (
    SELECT doc_id, posting_date, currency, unnest(lines) AS l
    FROM raw.erp_b_export
) AS d;
