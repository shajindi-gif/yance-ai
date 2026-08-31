-- Run once in yance_prod through DMS with an RDS privileged account.
CREATE EXTENSION IF NOT EXISTS vector;

SELECT extname, extversion
FROM pg_extension
WHERE extname = 'vector';

-- After the application migration, verify the exact revision.
SELECT version_num FROM alembic_version;

