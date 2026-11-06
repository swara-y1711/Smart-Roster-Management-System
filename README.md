# RosterIQ — Smart Workforce & Roster Management System

RosterIQ is a workforce operations platform that helps managers plan monthly employee schedules, monitor staffing coverage, identify scheduling conflicts, and analyze workforce capacity.

It combines automated roster generation, scheduling intelligence, and workforce analytics in a centralized application designed for multi-brand operations.

## Key Features

- **Workforce Management:** Centralized management of employees, brands, processes, pods, shifts, and assignments.
- **Smart Roster Planning:** Generate and validate monthly workforce schedules.
- **Coverage Analysis:** Track required versus assigned positions and identify staffing gaps.
- **Conflict Detection:** Identify scheduling conflicts and insufficient staffing.
- **Workforce Intelligence:** Analyze workforce capacity, resilience, and operational impact.
- **Secure Authentication:** Supabase Auth with JWT-protected FastAPI endpoints.
- **Database Security:** PostgreSQL Row Level Security (RLS) for authenticated access.
- **Demo-ready Data:** Pre-seeded synthetic workforce data generated using Python Faker.

## Technology Stack

| Layer           | Technologies                             |
| --------------- | ---------------------------------------- |
| Frontend        | Next.js, React, TypeScript, Tailwind CSS |
| Backend         | FastAPI, Python, Pydantic                |
| Database        | Supabase PostgreSQL                      |
| Authentication  | Supabase Auth, JWT                       |
| Database Access | PostgREST, psycopg                       |
| Synthetic Data  | Python Faker                             |

## System Architecture

**Frontend → FastAPI Backend → Supabase Authentication → PostgreSQL**

The frontend communicates with the FastAPI backend through API endpoints. Requests are authenticated using Supabase-issued JWTs, while PostgreSQL RLS policies enforce database-level access controls.

## Demo Data

RosterIQ comes pre-seeded with a synthetic workforce dataset generated using Python [Faker](https://faker.readthedocs.io/). This eliminates the need for reviewers to manually import the nine required CSV files and allows immediate access after database setup.

The shared demonstration dataset is available to every authenticated user.

**November 2026 Dataset**

| Data Entity        | Records |
| ------------------ | ------: |
| Employees          |      50 |
| Brands             |      10 |
| Processes          |      20 |
| Pods               |      40 |
| Required Positions |   1,200 |

## Getting Started

### Prerequisites

- Node.js 20 or newer
- Python 3.11 or newer
- A Supabase project

### 1. Configure Environment Variables

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<supabase-anon-key>
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Create `backend/.env`:

```env
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<supabase-anon-key>
DATABASE_URL=<postgresql-connection-string>
```

Never commit environment files, database passwords, service-role keys, or other secrets.

### 2. Database Setup

Apply the project SQL schema and migrations from the `database/` directory using the Supabase SQL Editor.

Apply them in the documented order, ensuring the shared authentication migration is applied before running the application.

### 3. Start the Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Backend: http://localhost:8000

API documentation: http://localhost:8000/docs

### 4. Start the Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:3000

## Demo data

The application normally needs 9 CSV files (employees, brands, processes, pods, etc.) to be imported before it can be used. To spare reviewers from re-importing them, the database is pre-seeded with synthetic data generated using Python Faker. This data is available to every login, so the app can be tested right away.

## Validation Snapshot

The following metrics were verified across the Dashboard, Roster Planner and Coverage pages for the generated roster proposal.

| Metric             | Result |
| ------------------ | -----: |
| Total Employees    |     50 |
| Active Employees   |     50 |
| Inactive Employees |      0 |
| Required Positions |  1,200 |
| Assigned Positions |  1,044 |
| Unfilled Positions |    156 |
| Staffing Coverage  |    87% |

**Coverage Calculation:** (1,044 / 1,200) × 100 = 87%.

The Dashboard and Coverage pages may display different results because the Dashboard represents the last saved roster, while Coverage represents the newly generated proposal.

## Testing

**Backend Tests**

```powershell
python -m pytest backend/tests
```

**Frontend Linting and Type Checking**

```powershell
cd frontend
npm run lint
npx tsc --noEmit
```

Integration tests involving Supabase Auth require connectivity to the configured Supabase project.

## Current Development Considerations

The following areas have been identified for further refinement:

- **Staffing Capacity:** Current workforce capacity may limit the ability to fill every required position.
- **Conflict Explanations:** Improve error messages to identify the actual cause of insufficient staffing.
- **Assignment Ledger:** Refine grouping dimensions to distinguish assignments by pod and shift.
- **Proposal Status:** Differentiate valid, invalid and review-required assignments.
- **Preference Validation:** Further verify employee preference evaluation and warning generation.
- **Roster State Visibility:** Clearly distinguish the last saved roster from a newly generated proposal.

## Security & Access Control

- Supabase JWT verification protects API endpoints.
- Unauthenticated API requests are rejected.
- PostgreSQL RLS is enabled for authenticated database access.
- The `anon` role is not granted access to shared workforce data.
- All authenticated users are members of the shared demonstration workspace by design.
- Authenticated users can access and modify shared data according to the existing database policies.

**Note:** The shared workspace is designed for demonstration and assessment purposes, not isolated multi-tenant production deployments.

## Project Purpose

RosterIQ demonstrates the application of full-stack development, database design, authentication, workforce scheduling, and operational analytics to a practical business problem.
