# Hand Cricket Online

A private-room multiplayer browser game based on traditional hand cricket.

Players create a private room, share a unique room code, and play hand
cricket with friends in real time. Each team can contain one or more players,
with a full match flow: lobby, ready system, toss, innings, scores, wickets,
bowler switching, and a final result screen.

> This project is built for small private friend circles — it is not a public
> matchmaking platform.

## Technology Stack

**Frontend**

- React
- Vite
- JavaScript (JSX)
- Tailwind CSS

**Backend**

- Python 3.12 (3.11 compatible)
- FastAPI
- Uvicorn
- WebSockets
- Pydantic

**Database** (planned, later phases)

- PostgreSQL
- SQLAlchemy

## Folder Structure

```
hand-cricket-online/
├── frontend/          # React + Vite + Tailwind app (UI)
│   ├── src/
│   │   ├── App.jsx    # Landing page (placeholder)
│   │   ├── main.jsx
│   │   └── index.css  # Tailwind entry
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── backend/           # FastAPI app (authoritative game state)
│   ├── main.py        # HTTP + WebSocket API entry point
│   ├── config.py      # Settings from env / .env
│   ├── game/          # Framework-independent game engine (no API deps)
│   │   ├── engine.py
│   │   ├── models.py
│   │   ├── rules.py
│   │   └── state.py
│   ├── rooms/         # Private rooms (codes, hosts, teams, lobby validation)
│   ├── ws/            # WebSocket registry, message builders, handlers
│   ├── tests/         # pytest suite (engine, rooms, WS integration)
│   ├── requirements.txt
│   └── requirements-dev.txt
├── .env.example       # Environment variable template
├── .gitignore
└── README.md
```

## Prerequisites

- Node.js 20+ and npm
- Python 3.11+ (3.12 recommended)

## Installation

### Backend

```bash
cd backend

# Create a virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend

npm install
```

## Running

### Backend

```bash
cd backend
uvicorn main:app --reload
```

The API will be available at http://localhost:8000. The health check is:

```bash
curl http://localhost:8000/health
```

### Frontend

```bash
cd frontend
npm run dev
```

Open the printed URL (default http://localhost:5173) in a browser.

## Backend API

The backend exposes a small HTTP API plus a real-time WebSocket channel. The
server is the authoritative source of truth for all game state.

### HTTP endpoints

| Method | Path                      | Description                          |
| ------ | ------------------------- | ------------------------------------ |
| GET    | `/health`                 | Health check                         |
| POST   | `/rooms`                  | Create a room, returns room + player |
| POST   | `/rooms/{code}/join`      | Join a room by code                  |
| GET    | `/rooms/{code}`           | Fetch a room snapshot                |

`POST /rooms` body: `{"host_name": "Alice", "max_players": 20}`.
`POST /rooms/{code}/join` body: `{"player_name": "Bob"}`. New players join the
room **UNASSIGNED** and pick a team over WebSocket.

Room codes are six random uppercase characters from an unambiguous alphabet
(e.g. `HCR7K2`), so they are hard to guess.

### Lobby and teams

Each game has exactly two teams, Team A and Team B, whose sizes are fully
dynamic and independent (e.g. 1 vs 1, 2 vs 5, 10 vs 10). The host configures
`team_a_size` and `team_b_size`, each within `[MIN_TEAM_SIZE, MAX_TEAM_SIZE]`
(configurable via environment variables, default 1 and 10). Team capacities
are enforced by the server: a player can never join a full team, never belong
to both teams, and a capacity can never be reduced below its current player
count. Players may join a team, leave a team (back to UNASSIGNED), or toggle
their own ready status. The game can start only when both teams hold exactly
their configured number of players and every player is ready.

The room snapshot the frontend renders carries the canonical lobby info:

```json
{
  "room_code": "...",
  "team_a_size": 2,
  "team_b_size": 5,
  "max_team_size": 10,
  "team_a": { "team_id": "team-1", "capacity": 2, "player_count": 2, "players": [...] },
  "team_b": { "team_id": "team-2", "capacity": 5, "player_count": 5, "players": [...] },
  "can_start": true
}
```

### WebSocket

Connect at `/ws/{room_code}/{player_id}` after creating/joining a room.

Client-to-server messages (JSON with a `type` field):

- `set_team_sizes` `{team_a_size, team_b_size}` (host only)
- `join_team` `{team: "A" | "B"}`
- `leave_team`
- `set_ready` / `player_ready` `{ready?: bool}`
- `start_game` (host only, begins the toss)
- `reset_lobby` (host only)
- `submit_toss` `{move: 0..10}`
- `toss_decision` `{decision: "BATTING" | "BOWLING"}`
- `submit_move` `{move: 0..10}`
- `begin_second_innings` (host only)
- `leave_room`
- `ping`

Server-to-client messages:

- `room_state`, `game_state`
- `team_sizes_updated`, `player_team_changed`, `player_ready`
- `player_joined`, `player_left`, `player_connected`, `player_disconnected`,
  `player_reconnected`
- `game_started`, `lobby_reset`, `toss_result`, `move_result`
- `error`, `pong`, `room_closed`

Rooms are fully isolated: a player in room ABC123 never receives events from
room XYZ789.

## Environment Variables

Copy `.env.example` to `.env` (or `frontend/.env`) and fill in values as
needed. No real secrets are committed to the repository.

| Variable             | Purpose                                |
| -------------------- | -------------------------------------- |
| `BACKEND_HOST`       | Backend bind host (uvicorn)            |
| `BACKEND_PORT`       | Backend bind port (uvicorn)            |
| `MIN_TEAM_SIZE`      | Smallest allowed team size (default 1) |
| `MAX_TEAM_SIZE`      | Largest allowed team size (default 10) |
| `VITE_BACKEND_URL`   | Backend API base URL used by frontend  |
| `VITE_WS_URL`        | Backend WebSocket URL used by frontend |
| `DATABASE_URL`       | PostgreSQL connection string (planned) |

## Roadmap

The application is being built incrementally:

- **Phase 1 (done):** Project structure, dev environment, landing page
- **Phase 2 (done):** Backend game engine with rules, state, and tests
- **Phase 3 (done):** Room system, player membership, WebSocket sync, HTTP API
- **Phase 4 (done):** Lobby and team system — dynamic team sizes, team
  assignment, readiness, lobby validation
- **Later phases:** Frontend UI (lobby, toss, gameplay screens), database
  persistence, deployment
