# RosterIQ frontend

The Next.js frontend uses Supabase Auth for Operations Manager registration and login.

## Configure Supabase

1. Copy `.env.example` to `.env.local` and set `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` from the existing Supabase project. Use the anon/publishable key only; never put the service-role key in the frontend.
2. Run [`../database/manager_profiles.sql`](../database/manager_profiles.sql) in the Supabase SQL Editor.
3. If email confirmation is disabled, registration creates the manager profile immediately. If confirmation is enabled, the manager profile is created after the new user confirms their email and logs in.
4. Restart the frontend after changing environment variables.

## Getting Started

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Unauthenticated visitors are sent to `/login`; successful registration or login opens the existing Executive Dashboard.
