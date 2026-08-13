# Hand Cricket Online - Frontend

React + Vite + Tailwind CSS client for Hand Cricket Online.

## Commands

```bash
npm install       # install dependencies
npm run dev       # start the dev server (default http://localhost:5173)
npm run build     # production build
npm run lint      # run oxlint
npm run preview   # preview the production build
```

## Environment

The frontend reads these variables from `frontend/.env` (see `.env.example`
at the repo root):

- `VITE_BACKEND_URL` — backend API base URL (default `http://localhost:8000`)
- `VITE_WS_URL` — backend WebSocket URL (default `ws://localhost:8000/ws`)
