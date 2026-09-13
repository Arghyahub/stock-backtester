# Seasonal Research frontend

Next.js interface for the Anomaly Trading V2 backend.

## Requirements

- Node.js 20+
- npm
- Running backend API

## Run locally

```bash
cp .env.example .env.local
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_BASE_URL` in `.env.local`. The default local value is:

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Open [http://localhost:3000](http://localhost:3000).

## Pages

- `/` — public approved windows beginning in the next 30 days.
- `/plans/:id` — evidence, mapped stock/ETF, alpha/beta, and headlines.
- `/admin` — track sectors, manage mappings, refresh data, and compute V2.

The public dashboard remains empty until an admin completes a successful
compute run that has a qualifying window in the next 30 days.

## Checks

```bash
npm run lint
npm run build
```
