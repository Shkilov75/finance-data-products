-- Exceptions report (AC-02): one record per aligned entry whose description has no translation.
-- Translated only on exact whole-text equality (no case-insensitive or word-level matching) and
-- only when the translation list gives a non-empty text; an empty target stays untranslated.
SELECT e.source_system,
       e.source_document,
       e.source_line,
       e.original_description
FROM staging.ledger_entry AS e
LEFT JOIN raw.description_translation AS t
       ON t.source_system = e.source_system
      AND t.original_description = e.original_description
      AND nullif(t.common_description, '') IS NOT NULL
WHERE t.original_description IS NULL
ORDER BY e.source_system, e.source_document, e.source_line;
