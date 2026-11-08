-- Invariant: each local account of a source system has exactly one row in the account mapping
-- (AC-11), whether the group accounts differ or repeat. Zero rows = fine.
SELECT source_system || ' ' || local_account || ' appears ' || CAST(count(*) AS STRING)
       || ' times in account_mapping_synthetic.csv' AS offender
FROM raw.account_mapping
GROUP BY source_system, local_account
HAVING count(*) > 1
ORDER BY source_system, local_account;
