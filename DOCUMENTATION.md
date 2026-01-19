# AutoDJ - Documentation Technique

## Vue d'ensemble

**AutoDJ** est une plateforme SaaS de génération automatique de DJ mixes par intelligence artificielle. L'application permet de créer des mixes professionnels à partir de pistes audio uploadées, en utilisant des algorithmes de mixage harmonique et de traitement audio par stems.

### Fonctionnalités principales

- Upload de 2 à 50 pistes audio (MP3/WAV)
- Analyse automatique (BPM, tonalité, énergie, structure)
- Calcul de l'ordre optimal des pistes via la roue de Camelot
- Génération de transitions professionnelles par séparation de stems
- Suivi en temps réel de la progression via WebSocket
- Téléchargement du mix final

---

## Architecture

### Structure Monorepo (Turborepo)

```
autodj/
├── apps/
│   ├── api/              # Backend NestJS (TypeScript)
│   ├── web/              # Frontend React (TypeScript)
│   └── workers/          # Workers Python (traitement audio)
├── packages/
│   ├── shared-types/     # Types TypeScript partagés
│   ├── database/         # Schéma Prisma & client
│   ├── ui/               # Composants shadcn/ui
│   ├── config-eslint/    # Configuration ESLint
│   └── config-typescript/# Configuration TypeScript
├── docker/               # Configurations Docker
└── docker-compose.yml    # Orchestration complète
```

---

## Stack Technique

### Frontend (`apps/web`)

| Catégorie | Technologies |
|-----------|-------------|
| Framework | React 18, TypeScript, Vite |
| Styling | TailwindCSS, shadcn/ui (Radix UI) |
| State | Zustand |
| Routing | React Router v6 |
| Temps réel | Socket.io-client |
| Formulaires | React Hook Form, Zod |
| HTTP | Axios |
| Upload | React Dropzone |
| Notifications | Sonner |
| Icônes | Lucide React |

### Backend (`apps/api`)

| Catégorie | Technologies |
|-----------|-------------|
| Framework | NestJS 10, TypeScript |
| ORM | Prisma 5 |
| Base de données | PostgreSQL 15 |
| Cache/Queue | Redis 7, BullMQ |
| WebSocket | Socket.io |
| Auth | JWT (passport-jwt), bcrypt |
| Logging | Pino |
| Documentation | Swagger/OpenAPI |

### Workers Python (`apps/workers`)

| Catégorie | Technologies |
|-----------|-------------|
| Analyse audio | librosa, madmom, Essentia |
| Séparation stems | Demucs |
| Traitement | pydub, soundfile, pyrubberband |
| Calcul | NumPy, SciPy |
| Queue | Redis, BullMQ (bindings Python) |
| Validation | Pydantic |
| Logging | structlog |

### Infrastructure

- **Conteneurisation** : Docker, Docker Compose
- **Monorepo** : pnpm 9, Turborepo 2
- **Runtime** : Node.js 20+, Python 3.11+

---

## Base de données

### Modèles principaux

#### Gestion utilisateurs
- `User` - Comptes utilisateurs avec plans (FREE, PRO, ENTERPRISE)

#### Gestion projets
- `Project` - Conteneur de projet de mix
- `Track` - Fichier audio individuel
- `TrackAnalysis` - Résultats d'analyse (BPM, tonalité, énergie, beats, marqueurs intro/outro)
- `Transition` - Transitions calculées entre pistes avec scores de compatibilité
- `MixSegment` - Segments du mix final (SOLO ou TRANSITION)
- `Job` - Jobs de la queue (ANALYZE, ORDER, TRANSITION_AUDIO, MIX)

#### Fonctionnalité Drafts
- `Draft` - Tests de transitions 2 pistes
- Modes supportés : STEMS (mixage complet) ou CROSSFADE (fondu simple)

### Statuts de projet

```
CREATED → UPLOADING → ANALYZING → ORDERING → READY → MIXING → COMPLETED → FAILED
```

### Statuts de draft

```
CREATED → UPLOADING → ANALYZING → READY → GENERATING → COMPLETED
```

---

## API REST

### Authentification

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/auth/register` | Créer un compte |
| POST | `/auth/login` | Obtenir un token JWT |
| GET | `/auth/me` | Profil utilisateur |

### Projets

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/projects` | Liste des projets |
| POST | `/projects` | Créer un projet |
| GET | `/projects/:id` | Détails du projet |
| PATCH | `/projects/:id` | Modifier un projet |
| DELETE | `/projects/:id` | Supprimer un projet |
| POST | `/projects/:id/mix/order` | Calculer l'ordre optimal |
| POST | `/projects/:id/transitions/generate` | Générer les transitions |
| POST | `/projects/:id/generate` | Lancer la génération du mix |
| GET | `/projects/:id/download` | Télécharger le mix (MP3/WAV) |
| GET | `/projects/:id/mix/segments` | Segments pour lecture |
| GET | `/projects/:id/mix/segments/:segmentId/audio` | Stream d'un segment |

### Pistes

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/projects/:projectId/tracks` | Liste des pistes |
| POST | `/projects/:projectId/tracks` | Upload (multipart, max 100MB) |
| GET | `/projects/:projectId/tracks/:trackId` | Détails d'une piste |
| GET | `/projects/:projectId/tracks/:trackId/analysis` | Résultats d'analyse |
| GET | `/projects/:projectId/tracks/:trackId/audio` | Stream audio |
| DELETE | `/projects/:projectId/tracks/:trackId` | Supprimer une piste |

### Drafts

Structure similaire pour les tests de transitions 2 pistes.

### Documentation Swagger

Accessible sur `http://localhost:3001/api/docs`

---

## Frontend

### Pages

| Page | Description |
|------|-------------|
| `HomePage` | Page d'accueil |
| `LoginPage` | Connexion |
| `RegisterPage` | Inscription |
| `DashboardPage` | Tableau de bord utilisateur |
| `ProjectPage` | Gestion complète d'un projet |
| `NewProjectPage` | Création de projet |
| `DraftsListPage` | Liste des drafts |
| `NewDraftPage` | Création de draft |
| `DraftPage` | Éditeur de transition 2 pistes |

### Composants principaux

| Composant | Description |
|-----------|-------------|
| `TrackUploader` | Upload drag-and-drop |
| `TrackList` | Affichage des pistes avec analyse |
| `TrackAnalysisCard` | BPM, tonalité, énergie, confiance |
| `ProjectProgress` | Barre de progression temps réel |
| `MixScoreCard` | Score moyen du mix |
| `MixPlayer` | Lecteur du mix final |
| `CompatibilityCard` | Scores harmonique/BPM/énergie |
| `DraftPlayer` | Lecteur de transition 2 pistes |
| `TransitionIndicator` | Indicateur visuel de qualité |

### Stores Zustand

| Store | Responsabilité |
|-------|----------------|
| `authStore` | Token, utilisateur, login/logout |
| `projectStore` | CRUD projets |
| `draftStore` | CRUD drafts |

### Hooks personnalisés

| Hook | Description |
|------|-------------|
| `useJobProgress()` | Connexion WebSocket pour progression projet |
| `useDraftProgress()` | Connexion WebSocket pour progression draft |

---

## Workers & Job Queue

### Queues BullMQ

| Queue | Description |
|-------|-------------|
| `analyze-queue` | Jobs d'analyse de pistes |
| `mix-queue` | Jobs de génération de mix |
| `draft-transition-queue` | Génération de transitions 2 pistes |
| `transitions-queue` | Génération d'audio de transition |

### Modules Python

#### Analyse (`src/analysis/`)
- `analyzer.py` - Point d'entrée principal (Essentia)
- `bpm.py` - Détection BPM et beats (librosa + madmom)
- `key.py` - Détection tonalité → roue de Camelot
- `energy.py` - Analyse énergie/danceability/loudness
- `camelot.py` - Conversion tonalité → Camelot
- `structure.py` - Détection intro/outro
- `stems.py` - Extraction features pour stems

#### Mixage (`src/mixing/`)
- `mixer.py` - Orchestrateur principal
- `beatmatch.py` - Synchronisation BPM (time-stretching)
- `stems.py` - Séparation stems via Demucs
- `transitions.py` - Création crossfades
- `transition_generator.py` - Pipeline complet de transition
- `draft_transition_generator.py` - Transitions 2 pistes
- `mix_generator.py` - Génération mix complet

#### Ordonnancement (`src/ordering/`)
- Solveur TSP pour séquençage optimal

---

## Algorithmes

### Ordonnancement des pistes

**Algorithme Nearest Neighbor avec scoring pondéré :**
1. Sélection de la piste de départ (énergie la plus basse)
2. Sélection itérative de la meilleure piste suivante
3. Pondération : Harmonique (50%) + BPM (30%) + Énergie (20%)

### Compatibilité harmonique (Roue de Camelot)

| Type | Score | Description |
|------|-------|-------------|
| Perfect Match | 100 | Même tonalité |
| Adjacent | 90 | ±1, même mode |
| Relative | 85 | Même numéro, mode opposé |
| Diagonal Adjacent | 75 | ±1, changement de mode |
| Energy Boost | 65 | +7 positions |
| Compatible | 60 | ±2 |
| Risky | 20 | Autres |

### Score BPM

| Différence | Score |
|------------|-------|
| ≤2% | 100 |
| ≤4% | 85 |
| ≤6% | 70 |
| ≤8% | 55 |
| >8% | 25 |

### Score Énergie

| Variation | Score | Description |
|-----------|-------|-------------|
| +0.05 à +0.15 | 100 | Montée douce |
| -0.05 à +0.05 | 85 | Stable |
| +0.15 à +0.25 | 70 | Montée forte |
| -0.15 à -0.05 | 65 | Descente douce |
| -0.25 à -0.15 | 45 | Descente forte |
| Autres | 25 | Extrême |

### Génération de transitions

1. **Mixage par stems** : Extraction des stems (drums, bass, vocals, other) via Demucs
2. **Beat matching** : Time-stretch pour aligner les BPM (pyrubberband)
3. **Transition 4 phases** : Introduction progressive de la nouvelle piste
4. **Fallback crossfade** : Si différence BPM >8%, crossfade simple

---

## Temps réel (WebSocket)

### Événements

| Événement | Description |
|-----------|-------------|
| `progress` | Progression du job (étape, %) |
| `mixOrdered` | Ordonnancement terminé |
| `mixGenerated` | Génération du mix terminée |
| `draftTransitionComplete` | Transition draft terminée |

---

## Configuration

### Variables d'environnement principales

```env
# Base de données
DATABASE_URL=postgresql://...

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Authentification
JWT_SECRET=min_32_caracteres

# Stockage
STORAGE_PATH=/path/to/storage
STORAGE_TYPE=local

# API
API_PORT=3001
API_HOST=0.0.0.0
CORS_ORIGINS=http://localhost:5173

# Frontend
VITE_API_URL=http://localhost:3001
VITE_WS_URL=http://localhost:3001

# Workers
DEMUCS_MODEL=htdemucs_ft
MAX_TRACK_DURATION=900  # 15 minutes
MAX_TRACKS_PER_PROJECT=50
```

### Concurrence des queues

| Queue | Concurrence |
|-------|-------------|
| ANALYZE | 2 jobs simultanés |
| MIX | 1 job (ressources intensives) |

---

## Déploiement Docker

### Services

| Service | Description | Port |
|---------|-------------|------|
| postgres | Base de données | 5432 |
| redis | Cache/Queue | 6379 |
| api | Backend NestJS | 3001 |
| web | Frontend React (Nginx) | 80 |
| workers | Workers Python | - |

### Ressources Workers

- 2-4 workers
- Limite : 2 CPU / 4GB RAM par worker

---

## Commandes de développement

```bash
# Installation
pnpm install

# Développement
pnpm dev

# Build
pnpm build

# Linting
pnpm lint

# Type checking
pnpm typecheck

# Tests
pnpm test

# Base de données
pnpm db:generate    # Génération client Prisma
pnpm db:push        # Push schéma vers DB
pnpm db:migrate     # Migrations
pnpm db:studio      # Interface Prisma Studio
```

---

## Statistiques du projet

| Catégorie | Quantité |
|-----------|----------|
| Composants React | 16+ |
| Modules NestJS | 11 |
| Modules Python | 7 |
| Modèles Prisma | 10+ |
| Endpoints API | 20+ |
