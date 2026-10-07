# Database Migrations

Migrations are plain SQL files applied in numeric order.

## How to apply

### Option A — Supabase SQL Editor (recommended for Supabase Cloud)

1. Open your Supabase project → **SQL Editor**
2. Paste the contents of each migration file in order
3. Click **Run**

### Option B — psql

```bash
psql "$DATABASE_URL" -f migrations/001_initial_schema.sql
```

## Files

| File | Description |
|------|-------------|
| `001_initial_schema.sql` | Creates `files`, `features`, `measurements` tables and indexes. Safe to re-run (idempotent). |

## Notes

- All migrations use `IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS` — safe to re-run against an existing database.
- The final `NOTIFY pgrst, 'reload schema'` refreshes the PostgREST schema cache so new columns are immediately visible without restarting the Supabase project.
