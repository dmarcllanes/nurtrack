-- ============================================================
-- 04_storage.sql
-- Supabase Storage bucket + policies for receipt images
--
-- NOTE: The bucket itself must be created via the Supabase
-- Dashboard (Storage → New bucket) or via the Management API.
-- Name: receipts | Public: enabled
--
-- The SQL below sets the storage access policies.
-- Run after the bucket exists.
-- ============================================================

-- Allow anyone to upload receipt images
CREATE POLICY "Anyone can upload receipts"
    ON storage.objects
    FOR INSERT
    TO public
    WITH CHECK (bucket_id = 'receipts');

-- Allow anyone to read receipt images (public bucket)
CREATE POLICY "Anyone can view receipts"
    ON storage.objects
    FOR SELECT
    TO public
    USING (bucket_id = 'receipts');

-- Allow authenticated users to delete their own uploads
CREATE POLICY "Authenticated users can delete own receipts"
    ON storage.objects
    FOR DELETE
    TO authenticated
    USING (bucket_id = 'receipts' AND owner = auth.uid());
