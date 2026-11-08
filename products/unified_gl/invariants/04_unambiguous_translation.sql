-- Invariant: each original description of a source system has at most one row in the translation
-- list (AC-02, AC-06). A repeated row would fan out the translation join in staging and show up
-- as a repeated entry_id, so this check runs before the entry-id check. Zero rows = fine.
SELECT source_system || ' ' || original_description || ' appears ' || CAST(count(*) AS VARCHAR)
       || ' times in description_translation_synthetic.csv' AS offender
FROM raw.description_translation
GROUP BY source_system, original_description
HAVING count(*) > 1
ORDER BY source_system, original_description;
