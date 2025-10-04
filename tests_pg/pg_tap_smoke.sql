-- pgTAP smoke tests placeholder
-- To run with pg_prove against a running Postgres with pgTAP installed.

-- 1) Extension exists
SELECT plan(1);

-- Check pgvector extension present (name may vary by image)
SELECT has_extension('vector') AS ok \gset
SELECT ok, diag('pgvector extension installed') FROM (SELECT :ok) s;

SELECT finish();
