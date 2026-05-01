-- ============================================================
-- 03_indexes.sql
-- Performance indexes for common query patterns
-- Run after 01_schema.sql
-- ============================================================

-- Feed ordered by newest first (default review view)
CREATE INDEX IF NOT EXISTS idx_expenses_created_at
    ON public.expenses (created_at DESC);

-- Filter by status (Pending / Acknowledged)
CREATE INDEX IF NOT EXISTS idx_expenses_status
    ON public.expenses (status);

-- Filter by uploader (per-user views)
CREATE INDEX IF NOT EXISTS idx_expenses_uploaded_by
    ON public.expenses (uploaded_by);

-- Category summaries via Polars group_by
CREATE INDEX IF NOT EXISTS idx_expenses_category
    ON public.expenses (category);
