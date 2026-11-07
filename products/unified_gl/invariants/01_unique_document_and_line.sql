-- Invariant: one export holds a document and line only once (AC-06).
-- Runs on the control views (raw records, unreadable entries included), before any readability rule.
-- Zero rows = fine. A returned row stops the run (exit 2) and names the offender.
SELECT source_system || ' ' || document || ' line ' || CAST(line AS VARCHAR)
       || ' appears ' || CAST(count(*) AS VARCHAR) || ' times in the export' AS offender
FROM (
    SELECT source_system, document, line FROM raw.control_erp_a
    UNION ALL
    SELECT source_system, document, line FROM raw.control_erp_b
) AS entries
WHERE line IS NOT NULL
GROUP BY source_system, document, line
HAVING count(*) > 1
ORDER BY source_system, document, line;
