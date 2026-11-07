-- Gate: mapping (AC-10). Zero rows = PASS.
-- An aligned entry whose local account has no row in the account mapping for its source system
-- keeps an empty group account. One row per source system and local account.
SELECT source_system || ' ' || local_account || ' has no group account in the account mapping ('
       || CAST(count(*) AS VARCHAR) || ' entries)' AS message
FROM staging.ledger_entry
WHERE group_account IS NULL
GROUP BY source_system, local_account
ORDER BY source_system, local_account;
