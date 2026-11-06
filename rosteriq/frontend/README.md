# RosterIQ frontend

The Next.js frontend uses Supabase Auth for Operations Manager registration and login.

## Configure Supabase

1. Copy `.env.example` to `.env.local` and set `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` from the existing Supabase project. Use the anon/publishable key only; never put the service-role key in the frontend.
2. On a fresh Supabase project, run [`../database/manager_profiles.sql`](../database/manager_profiles.sql) in the Supabase SQL Editor. The configured project already has this table, so do not rerun its setup script there.
3. Run [`../database/roster_relationships.sql`](../database/roster_relationships.sql) in the Supabase SQL Editor. It reuses the existing brands, processes, pods, employees, and employee_pods tables; it stops rather than guessing an organization mapping if brands or employees already contain data.
4. If email confirmation is disabled, registration creates the manager profile immediately. If confirmation is enabled, the manager profile is created after the new user confirms their email and logs in.
5. Employee names remain split across `first_name` and `last_name`, employment status remains `status`, and employee-to-pod assignment uses the existing `employee_pods` join table. Create organizations through the authenticated `create_organization` RPC; the creator is automatically associated with the organization. To associate additional managers, insert their memberships through the Supabase SQL Editor; client-side membership writes are intentionally not allowed.
6. Restart the frontend after changing environment variables.

## Getting Started

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Unauthenticated visitors are sent to `/login`; successful registration or login opens the existing Executive Dashboard.
