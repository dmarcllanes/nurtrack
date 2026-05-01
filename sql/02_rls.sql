-- ============================================================
-- 02_rls.sql
-- Row Level Security policies for the expenses table
-- Run after 01_schema.sql
-- ============================================================

-- Enable RLS
ALTER TABLE public.expenses ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to insert their own expenses
CREATE POLICY "Authenticated users can insert expenses"
    ON public.expenses
    FOR INSERT
    TO authenticated
    WITH CHECK (uploaded_by = auth.uid());

-- Allow authenticated users to read all expenses
CREATE POLICY "Authenticated users can read all expenses"
    ON public.expenses
    FOR SELECT
    TO authenticated
    USING (true);

-- Allow authenticated users to update status on any expense
CREATE POLICY "Authenticated users can acknowledge expenses"
    ON public.expenses
    FOR UPDATE
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Allow the anon key to insert (for unauthenticated capture flow)
CREATE POLICY "Anon can insert expenses"
    ON public.expenses
    FOR INSERT
    TO anon
    WITH CHECK (true);

-- Allow the anon key to read all expenses
CREATE POLICY "Anon can read expenses"
    ON public.expenses
    FOR SELECT
    TO anon
    USING (true);

-- Allow the anon key to update status
CREATE POLICY "Anon can update expenses"
    ON public.expenses
    FOR UPDATE
    TO anon
    USING (true)
    WITH CHECK (true);
