# AutoDJ - Refonte UX "Mix Studio"

## STATUT : ✅ TERMINÉ

---

## CE QUI A ÉTÉ FAIT ✅

### 1. Architecture du Studio
- **StudioPage** (`src/pages/StudioPage.tsx`) - Layout principal avec 4 zones
- **StudioStore** (`src/stores/studioStore.ts`) - Gestion état du studio (sélection, timeline, lecture)

### 2. Composants créés (`src/components/studio/`)
| Composant | Description | Statut |
|-----------|-------------|--------|
| `StudioHeader.tsx` | Header avec nom éditable, status, actions (Auto-arrange, Generate, Export) | ✅ |
| `MixList.tsx` | Sidebar liste des mixes + création | ✅ |
| `TrackPool.tsx` | Zone drop upload + grille horizontale mini-cartes | ✅ |
| `TrackMiniCard.tsx` | Mini carte draggable (BPM, Key, Energy) | ✅ |
| `Timeline.tsx` | Arrangement visuel horizontal | ✅ |
| `TimelineTrack.tsx` | Track dans timeline, réordonnable | ✅ |
| `TransitionIndicator.tsx` | Score compatibilité entre tracks | ✅ |
| `Inspector.tsx` | Panel détails track/transition | ✅ |
| `PlayerBar.tsx` | Barre lecture fixe en bas | ✅ |

### 3. Routing mis à jour (`src/App.tsx`)
```
/               → HomePage (landing)
/studio         → StudioPage (nouveau)
/studio/:id     → StudioPage avec mix sélectionné
/login          → LoginPage
/register       → RegisterPage
```

### 4. Fichiers supprimés
- `src/pages/DashboardPage.tsx`
- `src/pages/NewProjectPage.tsx`
- `src/pages/ProjectPage.tsx`
- `src/pages/DraftsListPage.tsx`
- `src/pages/NewDraftPage.tsx`
- `src/pages/DraftPage.tsx`
- `src/components/project/*`
- `src/components/draft/*`
- `src/components/layout/Sidebar.tsx`

### 5. Dépendances ajoutées
- `react-dnd` + `react-dnd-html5-backend` (drag & drop)

### 6. Corrections CSS
- `html`, `body`, `#root` → `height: 100%` pour layout pleine hauteur
- Composants avec `h-full` et `flex` pour remplir l'espace

### 7. Corrections bugs
- Boucle infinie API → séparation `isLoading` / `isLoadingList` dans projectStore
- `project.tracks.length` undefined → optional chaining
- Layout Sidebar supprimée du Layout principal

---

## CE QUI RESTE À FAIRE 🔧

### Priorité Haute

1. **Drag & Drop complet** ✅ TERMINÉ
   - [x] Drag depuis TrackPool vers Timeline
   - [x] Réorganisation tracks dans Timeline
   - [x] Feedback visuel pendant le drag

2. **Intégration API** ✅ TERMINÉ
   - [x] Sauvegarder l'ordre des tracks (`orderedTracks`) quand modifié
     - Backend: `UpdateProjectDto` accepte maintenant `orderedTracks`
     - Backend: Validation des track IDs (appartenance au projet, pas de doublons)
     - Frontend: `projectsService.saveTrackOrder()` ajouté
     - Frontend: Auto-save avec debounce 800ms dans StudioPage
   - [x] Bouton Auto-arrange appelle `calculateOrder`
   - [x] Bouton Generate Mix démarre la génération

3. **Player fonctionnel** ✅ TERMINÉ
   - [x] Lecture du mix complet (PlayerBar avec segments)
   - [x] Lecture d'une transition spécifique (navigation par segments)
   - [ ] Waveform visualisation (optionnel - non implémenté)

### Priorité Moyenne

4. **Métadonnées audio (covers, artiste, titre)** ✅ TERMINÉ
   - [x] **Backend** : Extraire metadata avec `music-metadata`
     - MetadataService créé dans `apps/api/src/tracks/metadata.service.ts`
     - Extraction automatique lors de l'upload (title, artist, album, genre, year, cover)
   - [x] **Backend** : Stocker cover art (fichier)
     - Covers stockées dans `storage/projects/{id}/covers/`
     - Endpoint GET `/projects/:id/tracks/:trackId/cover` pour servir les covers
   - [x] **Frontend** : Afficher cover dans TrackMiniCard
     - Design avec cover art carré en haut, infos en dessous
     - Placeholder avec icône Music si pas de cover
   - [x] **Frontend** : Afficher artiste/titre au lieu du filename
     - Si métadonnées présentes, affiche titre + artiste
     - Sinon fallback sur filename
   - [x] **Frontend** : Détails complets dans Inspector
     - Album, genre, year avec icônes et tooltips
     - File size affiché
     - Play overlay sur la cover
   - **DB** : `pnpm prisma db push` pour sync le schéma

5. **WebSocket real-time** ✅ TERMINÉ
   - [x] Progress pendant analyse (ProgressBar component)
   - [x] Progress pendant génération mix (ProgressBar component)
   - [x] Mise à jour auto des transitions

6. **UX améliorations** ✅ TERMINÉ
   - [x] Sidebar MixList collapsible (avec animation Framer Motion)
   - [x] Raccourcis clavier (Space, flèches, B, I, Escape)
   - [x] Confirmation avant suppression (inline confirmation)

### Priorité Basse

7. **Polish** ✅ TERMINÉ
   - [x] Animations Framer Motion sur transitions (sidebar, progress bar)
   - [x] Skeleton loading states (StudioSkeleton, TrackPoolSkeleton, etc.)
   - [x] Empty states plus visuels (déjà présents)
   - [x] Tooltips sur les actions (TooltipProvider partout)

---

## STRUCTURE ACTUELLE DES FICHIERS

```
src/
├── App.tsx                     # Routing principal
├── main.tsx
├── index.css                   # Midnight Studio theme
├── components/
│   ├── layout/
│   │   ├── Header.tsx          # Header global (landing)
│   │   └── Layout.tsx          # Layout pour landing
│   ├── studio/                 # 🆕 NOUVEAU
│   │   ├── index.ts
│   │   ├── StudioHeader.tsx    # Header avec tooltips et raccourcis
│   │   ├── MixList.tsx         # Sidebar collapsible
│   │   ├── TrackPool.tsx
│   │   ├── TrackMiniCard.tsx
│   │   ├── Timeline.tsx
│   │   ├── TimelineTrack.tsx
│   │   ├── TransitionIndicator.tsx
│   │   ├── Inspector.tsx       # Détails track/transition avec tooltips
│   │   ├── PlayerBar.tsx       # Lecture par segments
│   │   ├── ProgressBar.tsx     # 🆕 Progress WebSocket
│   │   └── Skeleton.tsx        # 🆕 Loading skeletons
│   ├── tracks/
│   │   ├── TrackUploader.tsx   # Réutilisable
│   │   ├── TrackAnalysisCard.tsx
│   │   └── TrackList.tsx
│   └── player/
│       └── MixPlayer.tsx       # À adapter pour PlayerBar
├── pages/
│   ├── HomePage.tsx            # Landing page
│   ├── StudioPage.tsx          # 🆕 NOUVEAU - Page principale
│   ├── LoginPage.tsx
│   ├── RegisterPage.tsx
│   └── NotFoundPage.tsx
├── stores/
│   ├── authStore.ts
│   ├── projectStore.ts         # Modifié (isLoadingList)
│   └── studioStore.ts          # 🆕 NOUVEAU (+ isSidebarCollapsed)
├── services/
│   ├── api.ts
│   ├── projects.service.ts
│   └── socket.service.ts
└── hooks/
    ├── useJobProgress.ts
    ├── useDraftProgress.ts
    └── useKeyboardShortcuts.ts # 🆕 NOUVEAU - Raccourcis clavier
```

---

## MODÈLES DE DONNÉES

### Track (existant)
```typescript
Track {
  id: string
  filename: string
  originalName: string
  duration: number | null
  fileSize: number
  analysis?: TrackAnalysis | null
}
```

### Track (à ajouter pour metadata)
```typescript
Track {
  // ... existant
  metadata?: {
    title?: string
    artist?: string
    album?: string
    genre?: string
    year?: number
    coverUrl?: string  // URL ou base64
  }
}
```

### TrackAnalysis (existant)
```typescript
TrackAnalysis {
  bpm: number
  key: string
  camelot: string
  energy: number
  danceability: number
  loudness: number
  vocalIntensity?: 'NONE' | 'LOW' | 'MEDIUM' | 'HIGH'
  mixFriendly?: boolean
  mixabilityWarnings?: string[]
}
```

---

## DESIGN SYSTEM "MIDNIGHT STUDIO"

Déjà implémenté dans `src/index.css`:

```css
/* Couleurs principales */
--background: 220 20% 6%;      /* Noir studio */
--foreground: 210 20% 92%;     /* Blanc cassé */
--primary: 38 95% 55%;         /* Amber/gold (VU meters) */
--accent: 185 70% 45%;         /* Cyan (LEDs) */
--success: 142 70% 45%;        /* Vert */
--destructive: 0 72% 51%;      /* Rouge */

/* Classes utilitaires */
.studio-panel    /* Glass panel effect */
.btn-glow        /* Bouton lumineux */
.text-glow       /* Texte avec glow */
.vu-meter        /* Barre VU meter gradient */
.led-on          /* LED allumée avec glow */
.scrollbar-studio /* Scrollbar custom */
```

---

## NOTES TECHNIQUES

- **Backend inchangé** - on utilise les mêmes API
- **Socket.io** pour real-time (progress, mix:ordered)
- **Formats audio** : MP3, WAV, M4A, FLAC, OGG (max 100MB)
- **Minimum 2 tracks** pour générer un mix
- **react-dnd** pour drag & drop

---

## POUR CONTINUER

1. Relire ce document
2. Lancer `pnpm dev` dans `apps/web`
3. Tester le flow : créer mix → upload tracks → voir analyse → arranger → générer
4. Implémenter les items "À FAIRE" par priorité
