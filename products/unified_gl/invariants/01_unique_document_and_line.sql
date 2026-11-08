-- Invariant: one export holds a document and line only once (AC-06).
-- Runs on the control views (raw records, unreadable entries included), before any readability rule:
-- a readable line is compared as a whole number, an unreadable one by its trimmed source text,
-- an empty document by the placeholder '?'.
-- Zero rows = fine. A returned row stops the run (exit 2) and names the offender.
SELECT source_system || ' ' || document || ' line ' || line_key
       || ' appears ' || CAST(count(*) AS VARCHAR) || ' times in the export' AS offender
FROM (
    SELECT source_system, coalesce(document, '?') AS document,
           coalesce(CAST(line AS VARCHAR), line_text, '?') AS line_key
    FROM raw.control_erp_a
    UNION ALL
    SELECT source_system, coalesce(document, '?') AS document,
           coalesce(CAST(line AS VARCHAR), line_text, '?') AS line_key
    FROM raw.control_erp_b
) AS entries
GROUP BY source_system, document, line_key
HAVING count(*) > 1
ORDER BY source_system, document, line_key;
