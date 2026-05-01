-- ============================================================
-- 05_seed.sql
-- Sample data for local development and UI testing
-- DO NOT run in production
-- ============================================================

INSERT INTO public.expenses (date, category, amount, status) VALUES
    (CURRENT_DATE - 5,  'Medical',    1250.00, 'Acknowledged'),
    (CURRENT_DATE - 3,  'Education',   850.50, 'Acknowledged'),
    (CURRENT_DATE - 2,  'Essentials',  420.75, 'Pending'),
    (CURRENT_DATE - 1,  'Medical',     300.00, 'Pending'),
    (CURRENT_DATE,      'Clothing',    599.00, 'Pending');
