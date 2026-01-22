# AutoDJ

Plateforme SaaS qui génère automatiquement des DJ mixes professionnels à partir de vos tracks audio.

## Fonctionnement

1. **Upload** - Déposez vos tracks MP3/WAV (10-50 fichiers)
2. **Analyse** - L'IA analyse chaque track : BPM, tonalité, énergie, structure
3. **Ordering** - Algorithme de compatibilité harmonique (Camelot wheel) pour ordonner les tracks
4. **Transitions** - Génération automatique de transitions fluides basées sur la séparation de stems (Demucs)
5. **Mix final** - Export du DJ set complet

**Bonus:** Chat IA (Mistral) pour réorganiser les tracks en langage naturel ("mets les tracks énergiques à la fin", "commence par du deep house", etc.)

## Stack

| Service | Tech | Port |
|---------|------|------|
| Frontend | React 18 + Vite + TailwindCSS | 5173 |
| API | NestJS 10 + Socket.io | 3001 |
| Workers | Python 3.10 (Essentia, Madmom, Demucs) | - |
| DB | PostgreSQL 15 | 5433 |
| Queue | Redis 7 + BullMQ | 6379 |

## Prérequis

- Node.js >= 20
- pnpm >= 9
- Docker & Docker Compose

## Lancement (Développement)

### 1. Setup initial (une seule fois)

```bash
pnpm install
cp .env.example .env
```

**Modifier `.env` - variable obligatoire:**
```
MISTRAL_API_KEY=votre-clé-api-mistral
```

### 2. Démarrer l'infrastructure + workers (Terminal 1)

```bash
docker-compose -f docker-compose.dev.yml up --build
```

> **Note:** `--build` reconstruit l'image des workers. À utiliser au premier lancement ou après modification des dépendances Python.

### 3. Initialiser la base de données (une seule fois)

```bash
pnpm db:generate
pnpm db:push
```

### 4. Démarrer les apps (Terminal 2)

```bash
pnpm dev
```

## URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| API | http://localhost:3001/api/v1 |
| Swagger | http://localhost:3001/api/docs |

## Résumé des commandes

**Premier lancement:**
```bash
pnpm install
cp .env.example .env
# Ajouter MISTRAL_API_KEY dans .env
docker-compose -f docker-compose.dev.yml up --build  # Terminal 1
pnpm db:generate && pnpm db:push                     # Terminal 2
pnpm dev                                              # Terminal 2
```

**Lancements suivants:**
```bash
docker-compose -f docker-compose.dev.yml up   # Terminal 1
pnpm dev                                       # Terminal 2
```

## Commandes Utiles

```bash
pnpm dev              # Démarre frontend + API
pnpm db:studio        # Interface graphique DB (Prisma)
pnpm build            # Build tous les packages
pnpm lint             # ESLint
```

## Production

```bash
docker-compose up -d --build
```

## Structure

```
apps/
├── api/          # Backend NestJS
├── web/          # Frontend React
└── workers/      # Workers Python (analyse audio, mixing, LLM)
packages/
├── database/     # Prisma schema
├── shared-types/ # Types partagés
└── ui/           # Composants React
```

## Troubleshooting

| Problème | Solution |
|----------|----------|
| `mistralai` module not found | `docker-compose -f docker-compose.dev.yml up --build` |
| Prisma "Cannot find module" | `pnpm db:generate` |
| Redis connection refused | Vérifier que Docker tourne |
| Workers crash en boucle | Vérifier `MISTRAL_API_KEY` dans `.env` |
