-- Run summary (AC-01, AC-14): one row per source system and transaction currency present in the
-- aligned entries. The currency list comes from the entries, never from the rates file.
SELECT source_system,
       transaction_currency,
       count(*) AS entries,
       coalesce(sum(CASE WHEN signed_amount > 0 THEN signed_amount END), 0) AS debit_total,
       coalesce(sum(CASE WHEN signed_amount < 0 THEN -signed_amount END), 0) AS credit_total
FROM staging.ledger_entry
GROUP BY source_system, transaction_currency
ORDER BY source_system, transaction_currency;
