# Project: Nurture-Track (Co-Parenting Expense Hub)

## Tech Stack
- **Environment/Pkg Manager:** uv
- **Frontend:** FastHTML (Python-based UI)
- **Data Engine:** Polars (for summaries and PDF exports)
- **Backend/DB:** Supabase (Postgres + Storage + Realtime)
- **Style:** Glassmorphism, Mesh Gradients, Teal/Stealth Jade palette

## Core Logic & UI Rules
- **The Woman's View:** Mobile-first, rapid-capture form with direct camera/upload access.
- **The Man's View:** Audit-style feed of expense cards with receipt previews.
- **Design Aesthetic:** - Primary Color: `#00A896` (Stealth Jade)
  - Components: Translucent glass cards (blur: 10px-20px), 1px borders.
  - Vibe: Premium, professional, neutral, and high-contrast.

## Database Schema (Supabase)
- **Table: `expenses`**
  - `id`: uuid (primary key)
  - `created_at`: timestamp (default: now())
  - `date`: date (expense date)
  - `category`: text (Medical, Education, Essentials, etc.)
  - `amount`: numeric
  - `image_url`: text (link to Supabase Storage)
  - `uploaded_by`: uuid (FK to auth.users)
  - `status`: text (Pending, Acknowledged)

## Common Commands (Using uv)
- **Initialize Project:** `uv init`
- **Install Dependencies:** `uv add python-fasthtml polars supabase python-dotenv`
- **Run Dev Server:** `uv run python main.py`
- **Sync Lockfile:** `uv pip compile pyproject.toml -o requirements.txt`

## AI Response Guidelines
- **UI:** Always use FastHTML components. Favor clean, modern CSS-in-Python or Tailwind utility classes.
- **Data:** Use Polars exclusively for data manipulation (no Pandas).
- **Environment:** Always provide commands using the `uv` prefix.
- **Tone:** Technical, concise, and aligned with a data engineer's workflow.