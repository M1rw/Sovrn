-- Ensure canonical worker/internal persistence is idempotent per job.
-- 1) Deduplicate historical rows for the same job_id (keep latest by created_at).
WITH ranked AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY job_id
            ORDER BY created_at DESC, id DESC
        ) AS rn
    FROM site_generations
    WHERE job_id IS NOT NULL
)
DELETE FROM site_generations
WHERE id IN (
    SELECT id
    FROM ranked
    WHERE rn > 1
);

-- 2) Enforce uniqueness at the database level.
CREATE UNIQUE INDEX IF NOT EXISTS uq_site_generations_job_id
ON site_generations(job_id)
WHERE job_id IS NOT NULL;
