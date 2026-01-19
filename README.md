# AutoDJ - AI-Powered DJ Mix Generation

AutoDJ is a SaaS platform that automatically generates professional DJ mixes from your uploaded tracks using AI-powered audio analysis and harmonic mixing algorithms.

## Features

- Upload 10-50 audio tracks (MP3/WAV)
- Automatic BPM, key, and energy analysis
- Optimal track ordering using Camelot wheel compatibility
- Professional crossfade and stem-based transitions
- Real-time progress tracking via WebSocket
- Download complete mixed DJ set

## Tech Stack

### Frontend
- React 18 + TypeScript + Vite
- TailwindCSS + shadcn/ui
- Zustand for state management
- React Router v6
- Socket.io-client for real-time updates

### Backend
- NestJS 10 + TypeScript
- Prisma ORM + PostgreSQL
- BullMQ + Redis for job queues
- Socket.io for WebSocket
- JWT authentication

### Workers (Python)
- Essentia for audio analysis
- Demucs for stem separation
- librosa + madmom for beat tracking
- pyrubberband for time-stretching

### Infrastructure
- Turborepo monorepo
- Docker + Docker Compose
- pnpm workspaces

## Project Structure

```
autodj/
├── apps/
│   ├── api/              # NestJS backend
│   ├── web/              # React frontend
│   └── workers/          # Python audio processing
├── packages/
│   ├── shared-types/     # TypeScript types
│   ├── ui/               # React components
│   ├── database/         # Prisma schema
│   ├── config-eslint/    # ESLint config
│   └── config-typescript/# TypeScript config
└── docker/               # Docker configs
```

## Getting Started

### Prerequisites

- Node.js >= 20
- pnpm >= 9
- Python >= 3.11
- Docker & Docker Compose
- PostgreSQL 15+ (or use Docker)
- Redis 7+ (or use Docker)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd autodj
   ```

2. **Install dependencies**
   ```bash
   pnpm install
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start infrastructure (PostgreSQL & Redis)**
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```

5. **Generate Prisma client and push schema**
   ```bash
   pnpm db:generate
   pnpm db:push
   ```

6. **Start development servers**
   ```bash
   pnpm dev
   ```

   This starts:
   - Frontend: http://localhost:5173
   - API: http://localhost:3001
   - Swagger docs: http://localhost:3001/api/docs

7. **Start Python workers (separate terminal)**
   ```bash
   cd apps/workers
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   python -m src.main
   ```

## Development Commands

```bash
# Install dependencies
pnpm install

# Start all apps in dev mode
pnpm dev

# Build all packages
pnpm build

# Run linting
pnpm lint

# Type check
pnpm typecheck

# Format code
pnpm format

# Database commands
pnpm db:generate   # Generate Prisma client
pnpm db:push       # Push schema to database
pnpm db:migrate    # Run migrations
pnpm db:studio     # Open Prisma Studio
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /auth/register | Register new user |
| POST | /auth/login | Login |
| GET | /auth/me | Get current user |
| GET | /projects | List projects |
| POST | /projects | Create project |
| GET | /projects/:id | Get project |
| DELETE | /projects/:id | Delete project |
| POST | /projects/:id/tracks | Upload tracks |
| POST | /projects/:id/generate | Start mix generation |
| GET | /projects/:id/download | Download mix |
| GET | /health | Health check |

## Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_HOST` / `REDIS_PORT` - Redis connection
- `JWT_SECRET` - Secret for JWT tokens (min 32 chars)
- `STORAGE_PATH` - Path for file storage

## Production Deployment

```bash
# Build and start all services
docker-compose up -d --build

# Or build images separately
docker-compose build api
docker-compose build web
docker-compose build workers
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT
