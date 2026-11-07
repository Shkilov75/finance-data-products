-- Invariant: no two aligned entries share an entry_id (AC-06).
-- Zero rows = fine. Names source system, document and line of every entry that shares an id.
SELECT e.source_system || ' ' || e.source_document || ' line ' || CAST(e.source_line AS VARCHAR)
       || ' shares entry_id ' || e.entry_id AS offender
FROM staging.ledger_entry AS e
WHERE e.entry_id IN (
    SELECT entry_id FROM staging.ledger_entry GROUP BY entry_id HAVING count(*) > 1
)
ORDER BY e.source_system, e.source_document, e.source_line;
