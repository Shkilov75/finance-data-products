-- Staged DDL (engine: duckdb). Promoted by `implement` into products/unified_gl/adapters/duckdb/.
-- Loads the five committed synthetic inputs into schema raw exactly as they arrived (all text).
-- Paths are relative to the repository root, where `fdp run` is started.

-- ERP A: flat delimited text, semicolon, German column names, every value kept as text.
CREATE OR REPLACE TABLE raw.erp_a_export AS
SELECT *
FROM read_csv(
    'products/unified_gl/data/erp_a_export_synthetic.csv',
    delim = ';', header = true, all_varchar = true,
    columns = {
        'belegnummer':  'VARCHAR',
        'zeile':        'VARCHAR',
        'buchungsdatum':'VARCHAR',
        'konto':        'VARCHAR',
        'sollbetrag':   'VARCHAR',
        'habenbetrag':  'VARCHAR',
        'waehrung':     'VARCHAR',
        'buchungstext': 'VARCHAR'
    }
);

-- ERP B: one JSON array of document objects, the lines stay nested (AC-03, ADR-0005).
CREATE OR REPLACE TABLE raw.erp_b_export AS
SELECT *
FROM read_json(
    'products/unified_gl/data/erp_b_export_synthetic.json',
    format = 'array',
    columns = {
        'doc_id':       'VARCHAR',
        'posting_date': 'VARCHAR',
        'currency':     'VARCHAR',
        'lines':        'STRUCT(line_no VARCHAR, account VARCHAR, amount VARCHAR, memo VARCHAR)[]'
    }
);

CREATE OR REPLACE TABLE raw.account_mapping AS
SELECT *
FROM read_csv(
    'products/unified_gl/data/account_mapping_synthetic.csv',
    header = true, all_varchar = true,
    columns = {'source_system': 'VARCHAR', 'local_account': 'VARCHAR', 'group_account': 'VARCHAR'}
);

CREATE OR REPLACE TABLE raw.description_translation AS
SELECT *
FROM read_csv(
    'products/unified_gl/data/description_translation_synthetic.csv',
    header = true, all_varchar = true,
    columns = {
        'source_system': 'VARCHAR', 'original_description': 'VARCHAR', 'common_description': 'VARCHAR'
    }
);

-- Loaded, not read in this step (roadmap step 3 reads it).
CREATE OR REPLACE TABLE raw.exchange_rate AS
SELECT *
FROM read_csv(
    'products/unified_gl/data/rates_synthetic.csv',
    header = true, all_varchar = true,
    columns = {'date': 'VARCHAR', 'currency': 'VARCHAR', 'rate_to_usd': 'VARCHAR'}
);
