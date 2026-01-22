# PROMPT - Système de Transitions DJ Professionnel COMPLET

## MISSION

Transformer le système de transitions de mon application AutoDJ pour qu'il produise des mixes de qualité professionnelle, indiscernables de ceux créés par des DJs experts. Le système doit implémenter TOUTES les techniques documentées dans les meilleures pratiques de l'industrie DJ.

---

## CONTEXTE TECHNIQUE

### Stack existante
```
apps/workers/
├── src/
│   ├── analysis/        # Analyse audio (à enrichir)
│   ├── mixing/          # Génération transitions (à réécrire)
│   └── llm/             # Intégration Mistral (à enrichir)
├── prompts/             # Prompts système
└── requirements.txt
```

### Technologies disponibles
- **Python 3.11+**
- **Analyse** : librosa, essentia, madmom
- **Stems** : Demucs (htdemucs_ft) - sépare en drums, bass, vocals, other
- **Traitement** : pydub, soundfile, pyrubberband, scipy
- **LLM** : Mistral API

---

## PARTIE 1 : ANALYSE AUDIO ENRICHIE

### 1.1 Structure des morceaux à détecter

Créer `apps/workers/src/analysis/structure_detector.py` qui détecte :

```python
STRUCTURE_SECTIONS = {
    "INTRO": {
        "bars": 16,
        "characteristics": "Éléments minimaux, conçu pour le mix",
        "energy": "low",
        "has_full_drums": False,
        "has_bass": False  # Souvent sans basse ou basse minimale
    },
    "VERSE": {
        "bars": 16,
        "characteristics": "Construction progressive de l'énergie",
        "energy": "medium-low",
        "has_full_drums": True,
        "has_bass": True
    },
    "BUILDUP": {
        "bars": [8, 16],  # Variable
        "characteristics": "Tension croissante, anticipation du drop",
        "energy": "rising",
        "has_full_drums": "building",
        "has_bass": "filtered/rising"
    },
    "DROP": {
        "bars": 16,
        "characteristics": "Point culminant énergétique, tous éléments présents",
        "energy": "maximum",
        "has_full_drums": True,
        "has_bass": True  # Basse pleine puissance
    },
    "BREAKDOWN": {
        "bars": [8, 16],
        "characteristics": "Respiration, éléments réduits, moment émotionnel",
        "energy": "low",
        "has_full_drums": False,
        "has_bass": False  # Basse retirée
    },
    "OUTRO": {
        "bars": 16,
        "characteristics": "Éléments retirés progressivement, conçu pour le mix",
        "energy": "decreasing",
        "has_full_drums": "decreasing",
        "has_bass": "decreasing"
    }
}
```

**Algorithme de détection :**
1. Séparer les stems avec Demucs
2. Calculer l'énergie RMS de chaque stem par segment de 8 bars
3. Détecter les drops = pics d'énergie où tous les stems sont présents
4. Détecter les breakdowns = creux d'énergie où bass et drums sont absents
5. Détecter les buildups = énergie croissante avant un drop
6. Intro = début jusqu'au premier élément majeur
7. Outro = après le dernier drop/breakdown

### 1.2 Détection des phrases

Créer `apps/workers/src/analysis/phrase_detector.py` :

```python
"""
Une phrase musicale = section cohérente de 8, 16, ou 32 mesures (bars)
En électronique : généralement 8 ou 16 bars
1 bar = 4 beats
Donc : 8 bars = 32 beats, 16 bars = 64 beats

La musique électronique est construite en puissances de 2.
Les changements majeurs arrivent TOUJOURS sur le premier beat d'une nouvelle phrase.
"""

def detect_phrases(audio_path: str, bpm: float, beats: list) -> list:
    """
    Retourne une liste de phrases avec:
    - start_time (seconds)
    - end_time (seconds)
    - bar_count (8, 16, ou 32)
    - beat_start_index
    - is_phrase_boundary (pour le mix)
    """
    # Calculer durée d'un bar
    beat_duration = 60.0 / bpm
    bar_duration = beat_duration * 4
    
    # Détecter les downbeats (beat 1 de chaque mesure)
    downbeats = detect_downbeats(beats, bpm)
    
    # Analyser les changements spectraux/énergétiques pour trouver
    # les vraies frontières de phrases (pas juste tous les 8 bars)
    
    # Les frontières de phrases sont marquées par:
    # - Changement d'instrumentation
    # - Changement d'énergie
    # - Entrée/sortie d'éléments (basse, vocals, etc.)
    
    return phrases
```

### 1.3 Détection vocale

Créer `apps/workers/src/analysis/vocal_detector.py` :

```python
"""
Deux vocals simultanés = CATASTROPHE
Le système DOIT savoir où sont les vocals pour éviter les clashes.
"""

def detect_vocals(audio_path: str) -> dict:
    """
    Utilise le stem vocal de Demucs pour détecter:
    - has_vocals: bool
    - vocal_sections: list of {start, end, intensity}
    - intensity: "FULL" (lead vocal), "SPARSE" (ad-libs), "BACKGROUND" (choeurs)
    """
    # 1. Séparer avec Demucs
    # 2. Analyser l'énergie RMS du stem vocal
    # 3. Seuil pour détecter présence
    # 4. Classifier l'intensité
    
    return {
        "has_vocals": True,
        "vocal_sections": [
            {"start": 32.0, "end": 64.0, "intensity": "FULL"},
            {"start": 96.0, "end": 112.0, "intensity": "SPARSE"}
        ]
    }
```

### 1.4 Points de mix recommandés

Créer `apps/workers/src/analysis/mix_points.py` :

```python
"""
Identifier les meilleurs points pour:
- MIX IN : où commencer à introduire ce track
- MIX OUT : où commencer à sortir de ce track
- CUE POINTS : points d'intérêt pour le mix
"""

def analyze_mix_points(structure: list, phrases: list, vocals: dict) -> dict:
    """
    Retourne:
    - best_mix_in_points: list (généralement intro, ou début d'une phrase sans vocal)
    - best_mix_out_points: list (outro, fin de drop, breakdown)
    - cue_points: list (drop, breakdown, vocal entry, etc.)
    """
    
    # Règles:
    # - Mix in sur une phrase boundary
    # - Mix out après un drop ou sur outro
    # - Éviter de mixer pendant les vocals intenses
    # - Le breakdown est une excellente zone de transition
    
    return mix_points
```

---

## PARTIE 2 : THÉORIE MUSICALE COMPLÈTE

### 2.1 Système Camelot Wheel Complet

Créer `apps/workers/src/theory/camelot.py` :

```python
"""
Le Camelot Wheel - Système de Mark Davis (Mixed In Key)
24 tonalités organisées en cercle pour faciliter le mixage harmonique.

Cercle extérieur (B) = Tonalités MAJEURES (son lumineux, énergique)
Cercle intérieur (A) = Tonalités MINEURES (son sombre, mélancolique)
"""

CAMELOT_WHEEL = {
    # Mineures (A) - cercle intérieur
    "1A": {"musical_key": "A♭m", "enharmonic": "G#m", "relative_major": "1B"},
    "2A": {"musical_key": "E♭m", "enharmonic": "D#m", "relative_major": "2B"},
    "3A": {"musical_key": "B♭m", "enharmonic": "A#m", "relative_major": "3B"},
    "4A": {"musical_key": "Fm", "enharmonic": None, "relative_major": "4B"},
    "5A": {"musical_key": "Cm", "enharmonic": None, "relative_major": "5B"},
    "6A": {"musical_key": "Gm", "enharmonic": None, "relative_major": "6B"},
    "7A": {"musical_key": "Dm", "enharmonic": None, "relative_major": "7B"},
    "8A": {"musical_key": "Am", "enharmonic": None, "relative_major": "8B"},
    "9A": {"musical_key": "Em", "enharmonic": None, "relative_major": "9B"},
    "10A": {"musical_key": "Bm", "enharmonic": None, "relative_major": "10B"},
    "11A": {"musical_key": "F#m", "enharmonic": "G♭m", "relative_major": "11B"},
    "12A": {"musical_key": "C#m", "enharmonic": "D♭m", "relative_major": "12B"},
    
    # Majeures (B) - cercle extérieur
    "1B": {"musical_key": "B", "enharmonic": "C♭", "relative_minor": "1A"},
    "2B": {"musical_key": "F#", "enharmonic": "G♭", "relative_minor": "2A"},
    "3B": {"musical_key": "D♭", "enharmonic": "C#", "relative_minor": "3A"},
    "4B": {"musical_key": "A♭", "enharmonic": "G#", "relative_minor": "4A"},
    "5B": {"musical_key": "E♭", "enharmonic": "D#", "relative_minor": "5A"},
    "6B": {"musical_key": "B♭", "enharmonic": "A#", "relative_minor": "6A"},
    "7B": {"musical_key": "F", "enharmonic": None, "relative_minor": "7A"},
    "8B": {"musical_key": "C", "enharmonic": None, "relative_minor": "8A"},
    "9B": {"musical_key": "G", "enharmonic": None, "relative_minor": "9A"},
    "10B": {"musical_key": "D", "enharmonic": None, "relative_minor": "10A"},
    "11B": {"musical_key": "A", "enharmonic": None, "relative_minor": "11A"},
    "12B": {"musical_key": "E", "enharmonic": None, "relative_minor": "12A"},
}

def calculate_harmonic_compatibility(key_a: str, key_b: str) -> dict:
    """
    Calcule la compatibilité harmonique entre deux tonalités Camelot.
    
    RÈGLES DE COMPATIBILITÉ:
    
    | Mouvement           | Score | Description                              | Exemple      |
    |---------------------|-------|------------------------------------------|--------------|
    | Même tonalité       | 100   | Parfait, aucune tension                  | 8A → 8A      |
    | +1 ou -1            | 95    | Adjacent, très harmonieux                | 8A → 9A, 7A  |
    | Majeur ↔ Mineur     | 90    | Relatif, changement d'humeur subtil      | 8A → 8B      |
    | +1/-1 + mode change | 80    | Diagonal adjacent                        | 8A → 9B, 7B  |
    | +2 ou -2            | 70    | Energy boost/drop, à utiliser avec soin  | 8A → 10A     |
    | +7 (dominant)       | 75    | Mouvement de résolution classique        | 8A → 3A      |
    | +5 (sous-dominant)  | 70    | Mouvement inverse du dominant            | 8A → 1A      |
    | Autre               | <50   | INCOMPATIBLE - éviter les blends longs   |              |
    """
    
    num_a = int(key_a[:-1])
    mode_a = key_a[-1]  # A ou B
    num_b = int(key_b[:-1])
    mode_b = key_b[-1]
    
    # Calculer la distance sur le cercle (0-6, car c'est circulaire)
    distance = min(abs(num_a - num_b), 12 - abs(num_a - num_b))
    same_mode = mode_a == mode_b
    
    # Même tonalité
    if key_a == key_b:
        return {"score": 100, "type": "PERFECT", "description": "Même tonalité"}
    
    # Adjacent ±1, même mode
    if distance == 1 and same_mode:
        return {"score": 95, "type": "ADJACENT", "description": "Adjacent harmonieux"}
    
    # Relatif majeur/mineur (même numéro, mode différent)
    if num_a == num_b and not same_mode:
        return {"score": 90, "type": "RELATIVE", "description": "Relatif maj/min"}
    
    # Diagonal adjacent (±1 + changement de mode)
    if distance == 1 and not same_mode:
        return {"score": 80, "type": "DIAGONAL", "description": "Diagonal adjacent"}
    
    # ±2, même mode
    if distance == 2 and same_mode:
        return {"score": 70, "type": "ENERGY_SHIFT", "description": "Energy boost/drop"}
    
    # +7 (dominant) - distance de 7 sur le cercle, même mode
    if distance == 7 and same_mode:
        return {"score": 75, "type": "DOMINANT", "description": "Résolution dominante"}
    
    # +5 (sous-dominant)
    if distance == 5 and same_mode:
        return {"score": 70, "type": "SUBDOMINANT", "description": "Sous-dominante"}
    
    # Tout le reste = incompatible
    return {"score": 30, "type": "INCOMPATIBLE", "description": "Clash harmonique probable"}
```

### 2.2 Référentiel BPM par Genre

```python
"""
Les plages de BPM typiques par genre.
Utile pour:
- Adapter la durée des transitions
- Comprendre le contexte énergétique
- Détecter le genre automatiquement
"""

BPM_REFERENCE = {
    # House
    "deep_house": {"min": 120, "max": 125, "energy": "low", "transition_style": "long_blend"},
    "chicago_house": {"min": 120, "max": 128, "energy": "medium", "transition_style": "blend"},
    "tech_house": {"min": 125, "max": 130, "energy": "medium", "transition_style": "blend"},
    "progressive_house": {"min": 125, "max": 130, "energy": "building", "transition_style": "long_blend"},
    "electro_house": {"min": 128, "max": 132, "energy": "high", "transition_style": "blend_or_cut"},
    "bass_house": {"min": 125, "max": 130, "energy": "high", "transition_style": "blend"},
    "hard_house": {"min": 145, "max": 150, "energy": "very_high", "transition_style": "cut"},
    
    # Techno
    "minimal_techno": {"min": 125, "max": 135, "energy": "medium", "transition_style": "long_blend"},
    "detroit_techno": {"min": 125, "max": 135, "energy": "medium", "transition_style": "blend"},
    "berlin_techno": {"min": 130, "max": 140, "energy": "high", "transition_style": "blend"},
    "acid_techno": {"min": 130, "max": 145, "energy": "high", "transition_style": "blend"},
    "hard_techno": {"min": 145, "max": 160, "energy": "very_high", "transition_style": "cut"},
    "industrial_techno": {"min": 130, "max": 145, "energy": "high", "transition_style": "blend"},
    
    # Autres électroniques
    "trance": {"min": 130, "max": 145, "energy": "building", "transition_style": "long_blend"},
    "psytrance": {"min": 140, "max": 150, "energy": "very_high", "transition_style": "blend"},
    "dubstep": {"min": 140, "max": 140, "energy": "high", "transition_style": "cut", "note": "half-time feel"},
    "drum_and_bass": {"min": 170, "max": 180, "energy": "very_high", "transition_style": "cut"},
    "jungle": {"min": 160, "max": 180, "energy": "very_high", "transition_style": "cut"},
    "breakbeat": {"min": 120, "max": 140, "energy": "medium", "transition_style": "cut"},
    "hardcore": {"min": 160, "max": 200, "energy": "extreme", "transition_style": "cut"},
    "hardstyle": {"min": 150, "max": 160, "energy": "very_high", "transition_style": "cut"},
    
    # Non-électroniques
    "hip_hop": {"min": 85, "max": 115, "energy": "variable", "transition_style": "cut"},
    "rnb": {"min": 60, "max": 90, "energy": "low", "transition_style": "fade"},
    "reggae": {"min": 60, "max": 90, "energy": "low", "transition_style": "fade"},
    "disco": {"min": 110, "max": 130, "energy": "medium", "transition_style": "blend"},
}

def detect_genre_from_bpm(bpm: float) -> list:
    """Retourne les genres possibles pour un BPM donné."""
    matches = []
    for genre, data in BPM_REFERENCE.items():
        if data["min"] <= bpm <= data["max"]:
            matches.append({"genre": genre, **data})
    return matches
```

---

## PARTIE 3 : TECHNIQUES DE TRANSITION

### 3.1 Types de transitions à implémenter

Créer `apps/workers/src/mixing/transitions/` avec un fichier par technique :

#### 3.1.1 Blend / Crossfade (`blend.py`)

```python
"""
LE BLEND - Technique standard House/Techno

Superposition progressive sur 16 à 64 mesures.
Le public ne doit pas percevoir où un morceau finit et l'autre commence.

DURÉES RECOMMANDÉES:
- Warmup: 32-64 bars (long, smooth)
- Build: 16-32 bars
- Peak: 8-16 bars (plus court, plus punchy)
- Cooldown: 32-64 bars

RÈGLE CRITIQUE: 
Jamais deux basses simultanées > 2 beats → utiliser bass swap
"""

def create_blend_transition(
    track_a_audio,
    track_b_audio,
    stems_a: dict,  # {drums, bass, vocals, other}
    stems_b: dict,
    transition_duration_bars: int,
    bpm: float,
    bass_swap_bar: int,  # Sur quel bar faire le swap de basse
    use_stems: bool = True
) -> np.ndarray:
    """
    Crée une transition blend professionnelle.
    
    Si use_stems=True:
        - Introduit les éléments de B progressivement
        - Bass swap NET au bar spécifié
        - Retire les éléments de A progressivement
    
    Si use_stems=False:
        - Simple crossfade volume avec EQ management
    """
    pass
```

#### 3.1.2 Bass Swap (`bass_swap.py`)

```python
"""
LE BASS SWAP - Technique FONDAMENTALE

Deux lignes de basse simultanées = son CONFUS et BOUEUX.
Le bass swap résout ce problème.

MÉTHODE:
1. Track B entre SANS basse (bass à 0, ou filtre HP sur les lows)
2. Blend les médiums et aigus de B
3. AU MOMENT DU SWAP (sur le 1er temps d'une phrase):
   - Couper INSTANTANÉMENT la basse de A
   - Monter INSTANTANÉMENT la basse de B
4. Continuer le blend des autres éléments
5. Faire sortir A complètement

LE SWAP DOIT ÊTRE NET:
- Instantané (idéal)
- Ou crossfade de 1 bar MAXIMUM
- JAMAIS de crossfade long sur les basses
"""

def execute_bass_swap(
    stems_a: dict,
    stems_b: dict,
    swap_time: float,  # En secondes
    swap_duration: str = "instant",  # "instant" ou "1_bar"
    sr: int = 44100
) -> tuple:
    """
    Exécute un bass swap propre.
    
    Retourne les stems modifiés avec le swap appliqué.
    """
    
    swap_sample = int(swap_time * sr)
    
    if swap_duration == "instant":
        # Swap instantané
        stems_a["bass"][swap_sample:] = 0
        stems_b["bass"][:swap_sample] = 0
    else:
        # Crossfade 1 bar
        bar_samples = int((60 / bpm) * 4 * sr)
        fade_out = np.linspace(1, 0, bar_samples)
        fade_in = np.linspace(0, 1, bar_samples)
        
        stems_a["bass"][swap_sample:swap_sample+bar_samples] *= fade_out
        stems_b["bass"][swap_sample:swap_sample+bar_samples] *= fade_in
        stems_a["bass"][swap_sample+bar_samples:] = 0
        stems_b["bass"][:swap_sample] = 0
    
    return stems_a, stems_b
```

#### 3.1.3 Hard Cut (`cut.py`)

```python
"""
LE CUT - Transition instantanée

Passage direct d'un morceau à l'autre sur le premier temps d'une phrase.
Populaire en hip-hop, drum & bass, et pour les moments de surprise.

EXÉCUTION:
1. Identifier le point de cut sur A (fin de phrase)
2. Identifier le point d'entrée sur B (début de phrase forte, souvent le drop)
3. Couper A exactement sur le premier temps
4. Lancer B simultanément

OPTIONS:
- Sec: cut direct sans effet
- Avec reverb tail: activer reverb sur A avant le cut, laisser s'éteindre
- Avec delay tail: même principe avec delay
- Avec buildup: crescendo/riser avant le cut pour maximiser l'impact
"""

def create_cut_transition(
    track_a_audio,
    track_b_audio,
    cut_point_a: float,  # Secondes
    entry_point_b: float,
    effect: str = "none",  # "none", "reverb_tail", "delay_tail"
    effect_params: dict = None,
    sr: int = 44100
) -> np.ndarray:
    """
    Crée une transition cut.
    """
    pass
```

#### 3.1.4 Filter Transition (`filter_transition.py`)

```python
"""
TRANSITION PAR FILTRE

Les filtres sculptent le son de manière musicale:
- HPF (High Pass Filter): retire les basses → son aérien, ténu
- LPF (Low Pass Filter): retire les aigus → son étouffé, lointain

TECHNIQUES:

1. Filter sweep OUT sur A:
   - HPF de 20Hz → 2000Hz+ sur A
   - Le son "s'éloigne", devient aérien
   - Parfait pour faire sortir un morceau

2. Filter sweep IN sur B:
   - LPF de 200Hz → 20000Hz sur B
   - Le son "arrive de loin", se révèle progressivement
   - Parfait pour introduire un morceau avec tension

3. Combiné:
   - HPF sweep up sur A + LPF sweep up sur B
   - Transition créative et dynamique
"""

def create_filter_transition(
    track_a_audio,
    track_b_audio,
    transition_duration: float,
    filter_a: dict,  # {"type": "hpf", "start": 20, "end": 2000}
    filter_b: dict,  # {"type": "lpf", "start": 200, "end": 20000}
    crossfade: bool = True,
    sr: int = 44100
) -> np.ndarray:
    """
    Crée une transition par filter sweep.
    """
    
    # Implémenter avec scipy.signal pour les filtres
    # Automatiser le sweep avec des enveloppes
    pass
```

#### 3.1.5 Echo Out (`echo_out.py`)

```python
"""
ECHO OUT - Sortie avec delay/reverb

Technique élégante pour terminer un morceau:
1. Activer l'effet (delay ou reverb) sur A
2. Couper le signal DRY progressivement
3. Laisser le signal WET (effet) s'éteindre naturellement
4. Pendant ce temps, B peut entrer

PARAMÈTRES DELAY:
- Time: synchronisé au BPM (1/4, 1/2, 1 beat)
- Feedback: 30-50% pour un decay naturel
- Mix: monter progressivement de 0% à 100% wet

PARAMÈTRES REVERB:
- Size: large pour un effet dramatique
- Decay: 2-4 secondes
- Mix: monter progressivement
"""

def create_echo_out_transition(
    track_a_audio,
    track_b_audio,
    echo_start: float,  # Quand commencer l'effet
    echo_duration: float,  # Durée du tail
    effect_type: str = "delay",  # "delay" ou "reverb"
    effect_params: dict = None,
    track_b_entry: float = None,  # Quand B entre (pendant le tail)
    sr: int = 44100
) -> np.ndarray:
    pass
```

#### 3.1.6 Loop Mixing (`loop_mixing.py`)

```python
"""
LOOP MIXING - Étendre ou créer des sections

Le looping permet de:
- Étendre une intro trop courte pour un blend plus long
- Maintenir un breakdown pour construire plus de tension
- Créer des patterns personnalisés

TAILLES DE LOOP STANDARD:
- 1 bar: pour effets rythmiques
- 2 bars: loop court, maintien du groove
- 4 bars: standard, naturel
- 8 bars: section complète
- 16 bars: phrase entière
"""

def create_loop(
    audio: np.ndarray,
    loop_start: float,
    loop_length_bars: int,
    bpm: float,
    repetitions: int,
    sr: int = 44100
) -> np.ndarray:
    """
    Crée un loop parfait calé sur le tempo.
    """
    bar_duration = (60 / bpm) * 4
    loop_samples = int(loop_length_bars * bar_duration * sr)
    start_sample = int(loop_start * sr)
    
    loop_audio = audio[start_sample:start_sample + loop_samples]
    
    # Crossfade les bords pour éviter les clics
    fade_samples = int(0.01 * sr)  # 10ms
    # ... appliquer crossfade
    
    # Répéter le loop
    extended = np.tile(loop_audio, repetitions)
    
    return extended

def extend_section(
    audio: np.ndarray,
    section_start: float,
    section_end: float,
    target_duration_bars: int,
    bpm: float,
    sr: int = 44100
) -> np.ndarray:
    """
    Étend une section (intro, outro, breakdown) à la durée souhaitée.
    """
    pass
```

#### 3.1.7 Double Drop (`double_drop.py`)

```python
"""
DOUBLE DROP - Technique avancée risquée

Faire tomber les drops de deux morceaux SIMULTANÉMENT.
Crée un moment d'intensité maximale.

PRÉREQUIS ABSOLUS:
- Tonalités PARFAITEMENT compatibles (même key ou ±1)
- BPM identiques (ou très proches, <1% de différence)
- Structures compatibles (drops de même longueur)
- Éléments complémentaires (pas deux leads identiques)

EXÉCUTION:
1. Identifier les drops des deux morceaux
2. Aligner parfaitement sur le premier temps
3. Mixer les stems intelligemment:
   - Drums: peuvent se superposer (ajoute de la puissance)
   - Bass: ATTENTION - choisir une seule basse ou alterner
   - Leads/Melody: doivent être complémentaires, pas conflictuels
4. Durée typique: 8-16 bars puis transition vers un seul track
"""

def create_double_drop(
    stems_a: dict,
    stems_b: dict,
    drop_start_a: float,
    drop_start_b: float,
    drop_duration_bars: int,
    bpm: float,
    stem_mix: dict,  # {"drums": [0.6, 0.6], "bass": [1.0, 0.0], ...}
    sr: int = 44100
) -> np.ndarray:
    """
    UTILISER AVEC PRÉCAUTION.
    Seulement si les conditions sont parfaites.
    """
    pass
```

#### 3.1.8 Acapella Mixing (`acapella.py`)

```python
"""
ACAPELLA MIXING - Mashup live

Superposer le vocal d'un morceau sur l'instrumental d'un autre.

PRÉREQUIS:
- Tonalités compatibles (le vocal doit "sonner juste" sur l'instrumental)
- BPM compatibles (le vocal doit pouvoir être time-stretchée)
- Styles compatibles (un vocal R&B sur du hard techno = bizarre)

TECHNIQUE:
1. Extraire le stem vocal du morceau A avec Demucs
2. Time-stretch pour matcher le BPM de B si nécessaire
3. Pitch-shift si nécessaire pour la compatibilité harmonique
4. Superposer sur l'instrumental de B
5. Mixer les niveaux pour que le vocal soit audible mais intégré
"""

def create_acapella_mix(
    vocal_stem: np.ndarray,
    instrumental_audio: np.ndarray,  # Ou stems sans vocals
    vocal_bpm: float,
    instrumental_bpm: float,
    vocal_key: str,
    instrumental_key: str,
    vocal_level: float = 0.8,  # Niveau relatif du vocal
    sr: int = 44100
) -> np.ndarray:
    pass
```

---

## PARTIE 4 : EFFETS AUDIO

Créer `apps/workers/src/mixing/effects/` :

### 4.1 Effets essentiels

```python
# effects/delay.py
"""
DELAY / ECHO

Répète le son à intervalles réguliers.

PARAMÈTRES:
- time: durée entre les répétitions (en beats ou ms)
  - 1/4 beat: delay rapide, rythmique
  - 1/2 beat: delay medium
  - 1 beat: delay standard
  - 3/4 beat: delay syncopé (groovy)
- feedback: quantité de signal réinjecté (0-1)
  - 0.3: quelques répétitions
  - 0.5: decay medium
  - 0.7+: long decay (attention au buildup)
- mix: wet/dry ratio (0-1)
  - 0.3: subtil
  - 0.5: équilibré
  - 1.0: 100% wet (pour echo out)

SYNC AU TEMPO: time_ms = (60000 / bpm) * beat_fraction
"""

def apply_delay(
    audio: np.ndarray,
    bpm: float,
    beat_fraction: float = 0.5,  # 1/4, 1/2, 1, etc.
    feedback: float = 0.4,
    mix: float = 0.3,
    sr: int = 44100
) -> np.ndarray:
    delay_samples = int((60 / bpm) * beat_fraction * sr)
    
    output = audio.copy()
    delayed = np.zeros_like(audio)
    
    for i in range(1, 10):  # 10 répétitions max
        level = feedback ** i
        if level < 0.01:
            break
        shift = delay_samples * i
        if shift < len(audio):
            delayed[shift:] += audio[:-shift] * level
    
    return output * (1 - mix) + delayed * mix


# effects/reverb.py
"""
REVERB

Simule la réverbération d'un espace acoustique.

TYPES:
- Room: petit espace, decay court
- Hall: grand espace, decay medium
- Cathedral: immense, decay long
- Plate: artificiel mais musical

PARAMÈTRES:
- size/room_size: taille de l'espace (0-1)
- decay/rt60: temps de réverbération
- mix: wet/dry
- pre_delay: délai avant la reverb (crée de l'espace)
- damping: atténuation des hautes fréquences
"""

def apply_reverb(
    audio: np.ndarray,
    room_size: float = 0.7,
    decay: float = 2.0,
    mix: float = 0.3,
    damping: float = 0.5,
    sr: int = 44100
) -> np.ndarray:
    # Utiliser une convolution avec une IR
    # Ou algorithme de Freeverb/Schroeder
    pass


# effects/filters.py
"""
FILTRES HPF / LPF

HPF (High Pass Filter):
- Laisse passer les hautes fréquences
- Coupe les basses
- Son: aérien, ténu, "lointain"
- Fréquences typiques: 20Hz (off) → 200Hz (léger) → 1000Hz+ (extrême)

LPF (Low Pass Filter):
- Laisse passer les basses fréquences
- Coupe les aigus
- Son: étouffé, "sous l'eau", lointain
- Fréquences typiques: 20000Hz (off) → 5000Hz (léger) → 500Hz (extrême)

SWEEPS:
- Filter sweep up: augmenter la fréquence progressivement
- Filter sweep down: diminuer la fréquence
- Automation: créer une courbe de fréquence dans le temps
"""

def apply_filter(
    audio: np.ndarray,
    filter_type: str,  # "hpf" ou "lpf"
    cutoff_freq: float,
    resonance: float = 0.7,  # Q factor
    sr: int = 44100
) -> np.ndarray:
    from scipy.signal import butter, sosfilt
    
    nyquist = sr / 2
    normalized_cutoff = cutoff_freq / nyquist
    
    if filter_type == "hpf":
        sos = butter(4, normalized_cutoff, btype='high', output='sos')
    else:  # lpf
        sos = butter(4, normalized_cutoff, btype='low', output='sos')
    
    return sosfilt(sos, audio)

def create_filter_sweep(
    audio: np.ndarray,
    filter_type: str,
    start_freq: float,
    end_freq: float,
    duration: float,  # En secondes
    curve: str = "exponential",  # "linear" ou "exponential"
    sr: int = 44100
) -> np.ndarray:
    """
    Applique un sweep de filtre progressif.
    """
    num_samples = int(duration * sr)
    
    if curve == "exponential":
        freqs = np.geomspace(start_freq, end_freq, num_samples)
    else:
        freqs = np.linspace(start_freq, end_freq, num_samples)
    
    # Appliquer le filtre frame par frame avec la fréquence qui change
    # (Utiliser un filtre IIR avec coefficients variables ou traitement par blocs)
    pass
```

### 4.2 Effets avancés

```python
# effects/advanced.py
"""
EFFETS AVANCÉS
"""

def apply_flanger(audio, rate=0.5, depth=0.7, mix=0.5, sr=44100):
    """
    Flanger: modulation créant un son 'jet'
    - rate: vitesse de modulation (Hz)
    - depth: profondeur de l'effet
    """
    pass

def apply_phaser(audio, rate=0.3, stages=4, mix=0.5, sr=44100):
    """
    Phaser: similaire au flanger mais plus subtil
    Son psychédélique, texture mouvante
    """
    pass

def apply_beat_repeat(audio, bpm, repeat_length_beats=0.25, repeats=4, sr=44100):
    """
    Beat Repeat: répète des segments rythmiques
    Excellent pour buildups et moments d'impact
    """
    beat_samples = int((60 / bpm) * repeat_length_beats * sr)
    # Extraire le segment, le répéter, créer un effet de stutter
    pass

def apply_gater(audio, bpm, pattern=[1,0,1,0,1,1,0,1], sr=44100):
    """
    Gater: découpe le son rythmiquement
    Crée des patterns staccato
    """
    pass

def apply_bitcrusher(audio, bit_depth=8, sample_rate_reduction=4):
    """
    Bitcrusher: dégrade le son numériquement
    Son lo-fi, industriel
    """
    # Réduire la résolution et le sample rate
    pass

def apply_spiral(audio, pitch_shift_rate=0.1, reverb_size=0.95, sr=44100):
    """
    Spiral: reverb infinie avec pitch shift
    Parfait pour sorties atmosphériques
    Le son monte ou descend en spirale infinie
    """
    pass
```

---

## PARTIE 5 : GESTION DE L'ÉNERGIE

### 5.1 Architecture du set

```python
# energy/set_manager.py
"""
GESTION DE L'ÉNERGIE D'UN SET

Un set réussi n'est PAS une montée constante.
C'est un VOYAGE avec des pics et des vallées intentionnels.

STRUCTURE TYPE (2 heures):

| Phase    | Durée     | Énergie | BPM      | Style transitions    |
|----------|-----------|---------|----------|----------------------|
| Warmup   | 0-30 min  | 3-5/10  | Modéré   | Longs blends (32-64) |
| Build    | 30-60 min | 5-7/10  | Croissant| Medium blends (16-32)|
| Peak     | 60-90 min | 8-10/10 | Maximum  | Variés (8-16)        |
| Cooldown | 90-120min | 6-4/10  | Décroiss.| Longs blends (32-64) |
"""

def determine_set_phase(
    track_index: int,
    total_tracks: int,
    elapsed_time: float,
    total_duration: float
) -> dict:
    """
    Détermine la phase actuelle du set.
    """
    progress = elapsed_time / total_duration
    
    if progress < 0.25:
        return {
            "phase": "WARMUP",
            "target_energy": (3, 5),
            "transition_style": "long_blend",
            "transition_bars": (32, 64),
            "bpm_change": "stable"
        }
    elif progress < 0.50:
        return {
            "phase": "BUILD",
            "target_energy": (5, 7),
            "transition_style": "medium_blend",
            "transition_bars": (16, 32),
            "bpm_change": "slightly_increasing"
        }
    elif progress < 0.75:
        return {
            "phase": "PEAK",
            "target_energy": (8, 10),
            "transition_style": "varied",
            "transition_bars": (8, 16),
            "bpm_change": "stable_high"
        }
    else:
        return {
            "phase": "COOLDOWN",
            "target_energy": (4, 6),
            "transition_style": "long_blend",
            "transition_bars": (32, 64),
            "bpm_change": "decreasing"
        }
```

### 5.2 Serpentine Flow

```python
"""
SERPENTINE FLOW

Alterner entre haute et basse énergie dans un ratio 5:1.
Évite la fatigue de l'auditeur.
Maintient l'intérêt tout en gardant une trajectoire globale.

Exemple:
HIGH → HIGH → HIGH → HIGH → HIGH → MEDIUM → HIGH → HIGH → ...

La respiration (le MEDIUM) amplifie l'impact du HIGH suivant.
"""

def apply_serpentine_flow(
    tracks: list,  # Liste de tracks avec leur énergie
    ratio: int = 5  # 5 high pour 1 medium
) -> list:
    """
    Réordonne ou suggère des modifications pour suivre le serpentine flow.
    """
    reordered = []
    high_count = 0
    
    for track in sorted(tracks, key=lambda t: t["energy"], reverse=True):
        if high_count < ratio:
            if track["energy"] >= 7:
                reordered.append(track)
                high_count += 1
        else:
            if track["energy"] < 7:
                reordered.append(track)
                high_count = 0
    
    return reordered
```

### 5.3 Teasing

```python
"""
TEASING

Hinter des moments haute énergie sans les livrer immédiatement.
Crée de l'anticipation.

TECHNIQUES:
- Jouer un buildup mais couper avant le drop
- Introduire un élément reconnaissable puis le retirer
- Filter sweep qui monte mais ne "relâche" pas
- Faux drops (drop atténué avant le vrai)
"""

def create_tease(
    audio: np.ndarray,
    buildup_start: float,
    buildup_end: float,  # Juste avant le drop
    drop_start: float,
    tease_type: str = "cut_before_drop",  # ou "filtered_drop", "half_drop"
    sr: int = 44100
) -> np.ndarray:
    """
    Crée un moment de tease.
    """
    pass
```

---

## PARTIE 6 : PROMPT SYSTÈME LLM

### 6.1 Le prompt enrichi pour le planner

Remplacer `apps/workers/prompts/AUTODJ_BRAIN_PROMPT.md` par cette version complète :

```markdown
# AutoDJ Brain - Système Expert DJ Professionnel v2.0

Tu es le cerveau d'un système de mixage DJ automatique professionnel. Tu dois prendre des décisions de transition comme un DJ expert de classe mondiale.

## DONNÉES D'ENTRÉE

Tu reçois un JSON avec:
- Analyse complète des deux tracks (BPM, key, energy, structure, phrases, vocals)
- Scores de compatibilité (harmonique, BPM, énergie)
- Contexte du set (phase, position, historique)

## TON RÔLE

Générer un plan de transition COMPLET et PRÉCIS en JSON qui sera exécuté à la lettre par le système audio.

---

## RÈGLES ABSOLUES (JAMAIS VIOLER)

### 1. BASS SWAP
**JAMAIS deux basses simultanées pendant plus de 2 beats.**
- Le bass swap doit être NET (instantané ou 1 bar max)
- Couper bass A EXACTEMENT quand bass B entre
- C'est LA règle la plus importante

### 2. PHRASE ALIGNMENT
**Les transitions DOIVENT commencer/finir sur des frontières de phrases.**
- Une phrase = 8, 16, ou 32 bars
- Les changements majeurs arrivent sur le beat 1 de la phrase
- Jamais couper au milieu d'une phrase

### 3. HARMONIC COMPATIBILITY
**Respecter le Camelot Wheel:**
- Score ≥ 90: Blend long OK (16-64 bars)
- Score 70-89: Blend medium (8-16 bars)
- Score 50-69: Blend court ou filter (4-8 bars)
- Score < 50: HARD CUT OBLIGATOIRE (pas de blend)

### 4. VOCAL CLASH
**Jamais deux vocals simultanés.**
- Si track A a des vocals pendant la transition, baisser/couper vocals A avant d'introduire B
- Si track B a des vocals dès le début, attendre que vocals A soient finis
- Ou utiliser hard cut entre les sections vocales

---

## TYPES DE TRANSITION

### STEM_BLEND (Compatibilité haute)
Conditions: harmonic ≥ 85, BPM delta ≤ 3%
Durée: 16-64 bars selon le contexte

Phases d'introduction de B:
1. Bars 1-4: Drums B à 30%, reste à 0%
2. Bars 5-8: Drums B à 50%, Other B à 30%
3. Bars 9-12: Drums B à 70%, Other B à 50%, BASS SWAP (A→0, B→100%)
4. Bars 13-16: Tout B monte à 100%, tout A descend à 0%

### CROSSFADE (Compatibilité moyenne)
Conditions: harmonic 60-84, BPM delta ≤ 5%
Durée: 8-16 bars
Méthode: Volume crossfade + bass swap au milieu

### HARD_CUT (Compatibilité basse ou effet dramatique)
Conditions: harmonic < 60 OU BPM delta > 6% OU choix artistique
Durée: 0 bars (instantané)
Options: sec, reverb_tail, delay_tail

### FILTER_SWEEP (Créatif)
Conditions: Compatibilité moyenne, veut un effet créatif
Durée: 8-16 bars
Méthode: HPF sweep up sur A + LPF sweep down→up sur B

### ECHO_OUT (Dramatique)
Conditions: Changement d'ambiance, fin de section
Durée: 4-8 bars + tail
Méthode: Delay ou reverb sur A, couper dry, laisser wet s'éteindre

### LOOP_EXTEND (Technique)
Conditions: Section trop courte pour le blend souhaité
Usage: Étendre intro/outro/breakdown pour plus de temps de mix

### DOUBLE_DROP (Avancé - RARE)
Conditions: Tonalités IDENTIQUES, BPM identiques, structures compatibles
Risque: ÉLEVÉ - utiliser seulement si parfait
Durée: 8-16 bars puis sortie vers un seul track

---

## DURÉES PAR CONTEXTE

| Phase Set | Durée Transition | Style Préféré |
|-----------|------------------|---------------|
| WARMUP    | 32-64 bars       | STEM_BLEND long, smooth |
| BUILD     | 16-32 bars       | STEM_BLEND, CROSSFADE |
| PEAK      | 8-16 bars        | Varié, HARD_CUT OK |
| COOLDOWN  | 32-64 bars       | STEM_BLEND long, smooth |

---

## POINTS DE CUT

### Où sortir de track A:
- **Standard**: Sur l'outro (après le dernier drop)
- **Peak time**: Après le premier drop (avant le breakdown 2)
- **Jamais**: Au milieu d'une phrase ou d'une section vocale

### Où entrer dans track B:
- **Standard**: Début de l'intro
- **Énergie immédiate**: Skip intro, entrer sur le verse ou buildup
- **Peak time**: Parfois direct sur le buildup ou drop

### Durée jouée par track:
| Phase     | Durée track A    |
|-----------|------------------|
| WARMUP    | 70-90%           |
| BUILD     | 60-80%           |
| PEAK      | 40-70%           |
| COOLDOWN  | 70-90%           |

---

## EFFETS

### Reverb (sortie dramatique)
- Utiliser avant HARD_CUT pour adoucir
- Params: size=large, decay=2-3s, mix=0.5→1.0

### Delay (sortie rythmique)
- Timing sync au BPM (1/4, 1/2, 1 beat)
- Params: feedback=0.4, mix=0.3→0.8

### Filter HPF (sortie aérienne)
- Sweep de 20Hz → 2000Hz+
- Le son "s'éloigne"

### Filter LPF (entrée progressive)
- Sweep de 500Hz → 20000Hz
- Le son "se révèle"

---

## FORMAT DE SORTIE

```json
{
  "summary": "Description courte de la stratégie",
  "confidence": 0.95,
  
  "track_a": {
    "play_from_seconds": 0.0,
    "play_until_seconds": 210.0,
    "play_until_section": "OUTRO",
    "effective_duration_percent": 75,
    "cut_reason": "Sortie après le drop 1, avant breakdown 2"
  },
  
  "track_b": {
    "start_from_seconds": 0.0,
    "start_from_section": "INTRO",
    "entry_reason": "Entrée standard sur intro"
  },
  
  "transition": {
    "type": "STEM_BLEND",
    "start_time_in_a": 195.0,
    "duration_bars": 16,
    "duration_seconds": 30.0,
    
    "stems": {
      "enabled": true,
      "bass_swap_bar": 9,
      "bass_swap_style": "instant",
      "phases": [
        {
          "bars": [1, 4],
          "a": {"drums": 1.0, "bass": 1.0, "other": 1.0, "vocals": 1.0},
          "b": {"drums": 0.3, "bass": 0.0, "other": 0.0, "vocals": 0.0}
        },
        {
          "bars": [5, 8],
          "a": {"drums": 1.0, "bass": 1.0, "other": 0.7, "vocals": 0.7},
          "b": {"drums": 0.5, "bass": 0.0, "other": 0.3, "vocals": 0.0}
        },
        {
          "bars": [9, 12],
          "a": {"drums": 0.6, "bass": 0.0, "other": 0.4, "vocals": 0.3},
          "b": {"drums": 0.7, "bass": 1.0, "other": 0.6, "vocals": 0.3}
        },
        {
          "bars": [13, 16],
          "a": {"drums": 0.2, "bass": 0.0, "other": 0.0, "vocals": 0.0},
          "b": {"drums": 1.0, "bass": 1.0, "other": 1.0, "vocals": 1.0}
        }
      ]
    },
    
    "effects": {
      "track_a": {
        "type": "none",
        "params": {}
      },
      "track_b": {
        "type": "none",
        "params": {}
      }
    },
    
    "volume_automation": {
      "track_a": [
        {"bar": 1, "level": 1.0},
        {"bar": 8, "level": 0.85},
        {"bar": 12, "level": 0.4},
        {"bar": 16, "level": 0.0}
      ],
      "track_b": [
        {"bar": 1, "level": 0.3},
        {"bar": 8, "level": 0.5},
        {"bar": 12, "level": 0.85},
        {"bar": 16, "level": 1.0}
      ]
    }
  },
  
  "warnings": [
    {"type": "INFO", "message": "Transition optimale, aucun problème détecté"}
  ],
  
  "alternative": {
    "type": "CROSSFADE",
    "reason": "Si stem separation échoue",
    "duration_bars": 8
  }
}
```

---

## EXEMPLES

### Exemple 1: Tech House parfait
Input: 126 BPM 8A → 125 BPM 8A, harmonic=100, energy=72%→75%
Output: STEM_BLEND 16 bars, bass swap bar 9, smooth

### Exemple 2: Clash harmonique
Input: 128 BPM 8A → 127 BPM 2B, harmonic=35
Output: HARD_CUT avec reverb_tail, couper sur la fin de phrase A

### Exemple 3: Grand écart BPM
Input: 126 BPM → 140 BPM, harmonic=90
Output: HARD_CUT (malgré bonne harmonie, BPM trop différent)

### Exemple 4: Peak time
Input: Phase=PEAK, energy=85%→88%
Output: STEM_BLEND 8 bars (court et punchy), ou HARD_CUT pour impact

### Exemple 5: Vocals des deux côtés
Input: Track A vocals 0:30-1:00, Track B vocals dès 0:00
Output: Retarder l'entrée de B jusqu'à 1:00, ou HARD_CUT après 1:00

---

## RAPPELS FINAUX

1. **Génère UNIQUEMENT du JSON valide**
2. **Le plan sera exécuté À LA LETTRE**
3. **Bass swap = règle SACRÉE**
4. **Phrase alignment = obligatoire**
5. **Adapte au contexte du set**
6. **Confidence < 0.8 si doutes**
```

---

## PARTIE 7 : EXÉCUTION DU PLAN

### 7.1 Plan Executor principal

Créer `apps/workers/src/mixing/plan_executor.py` :

```python
"""
PLAN EXECUTOR

Ce module prend un plan JSON généré par le LLM et l'exécute EXACTEMENT.
C'est le cœur du système de génération de transitions.
"""

import numpy as np
from typing import Dict, Any, Tuple
import soundfile as sf

from .stems import separate_stems
from .effects import apply_delay, apply_reverb, create_filter_sweep
from .transitions import (
    create_stem_blend,
    create_crossfade,
    create_hard_cut,
    create_filter_transition,
    create_echo_out
)
from ..analysis import get_bar_duration

class TransitionPlanExecutor:
    def __init__(self, sr: int = 44100):
        self.sr = sr
    
    def execute(
        self,
        track_a_path: str,
        track_b_path: str,
        plan: Dict[str, Any],
        analysis_a: dict,
        analysis_b: dict
    ) -> np.ndarray:
        """
        Exécute le plan de transition complet.
        
        Returns:
            Audio numpy array de la transition complète
        """
        bpm = analysis_a["bpm"]
        bar_duration = get_bar_duration(bpm)
        
        # 1. Charger les segments audio selon les points de cut
        audio_a = self._load_segment(
            track_a_path,
            start=plan["track_a"]["play_from_seconds"],
            end=plan["track_a"]["play_until_seconds"]
        )
        
        audio_b = self._load_segment(
            track_b_path,
            start=plan["track_b"]["start_from_seconds"],
            end=None  # Jusqu'à la fin ou géré par la prochaine transition
        )
        
        # 2. Time-stretch B si nécessaire pour matcher le BPM
        if abs(analysis_a["bpm"] - analysis_b["bpm"]) > 0.5:
            audio_b = self._time_stretch(audio_b, analysis_b["bpm"], analysis_a["bpm"])
        
        # 3. Séparer les stems si nécessaire
        transition_type = plan["transition"]["type"]
        
        if transition_type == "STEM_BLEND" and plan["transition"]["stems"]["enabled"]:
            stems_a = separate_stems(audio_a, self.sr)
            stems_b = separate_stems(audio_b, self.sr)
            
            result = self._execute_stem_blend(
                audio_a, audio_b,
                stems_a, stems_b,
                plan, bpm
            )
        
        elif transition_type == "CROSSFADE":
            result = self._execute_crossfade(audio_a, audio_b, plan, bpm)
        
        elif transition_type == "HARD_CUT":
            result = self._execute_hard_cut(audio_a, audio_b, plan, bpm)
        
        elif transition_type == "FILTER_SWEEP":
            result = self._execute_filter_sweep(audio_a, audio_b, plan, bpm)
        
        elif transition_type == "ECHO_OUT":
            result = self._execute_echo_out(audio_a, audio_b, plan, bpm)
        
        else:
            # Fallback: simple crossfade
            result = self._execute_crossfade(audio_a, audio_b, plan, bpm)
        
        return result
    
    def _execute_stem_blend(
        self,
        audio_a: np.ndarray,
        audio_b: np.ndarray,
        stems_a: Dict[str, np.ndarray],
        stems_b: Dict[str, np.ndarray],
        plan: dict,
        bpm: float
    ) -> np.ndarray:
        """
        Exécute un stem blend avec l'automation phase par phase.
        """
        bar_samples = int(get_bar_duration(bpm) * self.sr)
        transition_bars = plan["transition"]["duration_bars"]
        transition_samples = transition_bars * bar_samples
        
        # Point de début de la transition dans track A
        trans_start_a = plan["transition"]["start_time_in_a"]
        trans_start_sample = int(trans_start_a * self.sr)
        
        # Partie de A avant la transition (joue normalement)
        result_before = audio_a[:trans_start_sample]
        
        # Zone de transition - appliquer l'automation des stems
        phases = plan["transition"]["stems"]["phases"]
        bass_swap_bar = plan["transition"]["stems"]["bass_swap_bar"]
        
        transition_audio = np.zeros(transition_samples)
        
        for phase in phases:
            bar_start = phase["bars"][0] - 1  # 0-indexed
            bar_end = phase["bars"][1]
            
            phase_start_sample = bar_start * bar_samples
            phase_end_sample = bar_end * bar_samples
            phase_length = phase_end_sample - phase_start_sample
            
            # Positions dans les stems originaux
            a_start = trans_start_sample + phase_start_sample
            a_end = trans_start_sample + phase_end_sample
            b_start = phase_start_sample
            b_end = phase_end_sample
            
            # Mixer les stems selon les niveaux de la phase
            for stem_name in ["drums", "bass", "other", "vocals"]:
                level_a = phase["a"].get(stem_name, 0)
                level_b = phase["b"].get(stem_name, 0)
                
                if a_end <= len(stems_a[stem_name]) and b_end <= len(stems_b[stem_name]):
                    stem_a_segment = stems_a[stem_name][a_start:a_end] * level_a
                    stem_b_segment = stems_b[stem_name][b_start:b_end] * level_b
                    
                    # Gérer le bass swap NET
                    if stem_name == "bass":
                        swap_sample_in_phase = (bass_swap_bar - bar_start - 1) * bar_samples
                        if 0 <= swap_sample_in_phase < phase_length:
                            # Avant le swap: que A
                            # Après le swap: que B
                            stem_a_segment[swap_sample_in_phase:] = 0
                            stem_b_segment[:swap_sample_in_phase] = 0
                    
                    transition_audio[phase_start_sample:phase_end_sample] += stem_a_segment
                    transition_audio[phase_start_sample:phase_end_sample] += stem_b_segment
        
        # Partie de B après la transition
        result_after = audio_b[transition_samples:]
        
        # Assembler
        result = np.concatenate([result_before, transition_audio, result_after])
        
        return result
    
    def _execute_hard_cut(
        self,
        audio_a: np.ndarray,
        audio_b: np.ndarray,
        plan: dict,
        bpm: float
    ) -> np.ndarray:
        """
        Exécute un hard cut avec effet optionnel.
        """
        effect = plan["transition"]["effects"]["track_a"]
        
        if effect["type"] == "reverb":
            # Ajouter reverb tail sur les dernières secondes de A
            tail_duration = effect["params"].get("decay", 2.0)
            tail_samples = int(tail_duration * self.sr)
            
            # Appliquer reverb sur la fin de A
            audio_a_with_reverb = apply_reverb(
                audio_a[-tail_samples*2:],
                room_size=effect["params"].get("size", 0.8),
                decay=tail_duration,
                mix=effect["params"].get("mix", 0.7),
                sr=self.sr
            )
            
            # Fade out le dry, garde le wet
            # ... implémenter le fade
            
            audio_a = np.concatenate([audio_a[:-tail_samples*2], audio_a_with_reverb])
        
        elif effect["type"] == "delay":
            # Similaire avec delay
            pass
        
        # Concaténer directement
        return np.concatenate([audio_a, audio_b])
    
    def _load_segment(self, path: str, start: float, end: float = None) -> np.ndarray:
        """Charge un segment audio."""
        audio, sr = sf.read(path)
        
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)  # Mono
        
        start_sample = int(start * sr)
        end_sample = int(end * sr) if end else len(audio)
        
        return audio[start_sample:end_sample]
    
    def _time_stretch(self, audio: np.ndarray, source_bpm: float, target_bpm: float) -> np.ndarray:
        """Time-stretch l'audio pour matcher le BPM cible."""
        import pyrubberband as pyrb
        
        ratio = source_bpm / target_bpm
        return pyrb.time_stretch(audio, self.sr, ratio)
```

---

## PARTIE 8 : TESTS ET VALIDATION

### 8.1 Cas de test à implémenter

```python
# tests/test_transitions.py

def test_stem_blend_bass_swap():
    """Vérifie que le bass swap est NET (pas de superposition)."""
    # Le test doit échouer si on détecte 2 basses simultanées > 2 beats
    pass

def test_phrase_alignment():
    """Vérifie que les transitions commencent sur des phrase boundaries."""
    pass

def test_harmonic_compatibility_respected():
    """Vérifie que les règles harmoniques sont respectées."""
    # Score < 50 → doit être HARD_CUT
    pass

def test_vocal_clash_avoided():
    """Vérifie qu'il n'y a pas de clash vocal."""
    pass

def test_energy_flow():
    """Vérifie que l'énergie suit le serpentine flow."""
    pass
```

---

## RÉSUMÉ DES FICHIERS À CRÉER/MODIFIER

```
apps/workers/
├── prompts/
│   └── AUTODJ_BRAIN_PROMPT.md        # REMPLACER par version v2.0 complète
│
├── src/
│   ├── theory/                        # NOUVEAU
│   │   ├── __init__.py
│   │   ├── camelot.py                # Roue Camelot complète
│   │   └── bpm_reference.py          # BPM par genre
│   │
│   ├── analysis/                      # ENRICHIR
│   │   ├── structure_detector.py     # RÉÉCRIRE - sections complètes
│   │   ├── phrase_detector.py        # NOUVEAU - phrases 8/16/32 bars
│   │   ├── vocal_detector.py         # NOUVEAU - détection vocals
│   │   └── mix_points.py             # NOUVEAU - points de mix
│   │
│   ├── mixing/
│   │   ├── transitions/               # NOUVEAU dossier
│   │   │   ├── __init__.py
│   │   │   ├── blend.py              # Stem blend
│   │   │   ├── bass_swap.py          # Bass swap
│   │   │   ├── cut.py                # Hard cut
│   │   │   ├── filter_transition.py  # Filter sweep
│   │   │   ├── echo_out.py           # Echo/reverb out
│   │   │   ├── loop_mixing.py        # Loop extend
│   │   │   ├── double_drop.py        # Double drop
│   │   │   └── acapella.py           # Acapella mix
│   │   │
│   │   ├── effects/                   # NOUVEAU dossier
│   │   │   ├── __init__.py
│   │   │   ├── delay.py
│   │   │   ├── reverb.py
│   │   │   ├── filters.py
│   │   │   └── advanced.py           # Flanger, phaser, etc.
│   │   │
│   │   ├── plan_executor.py          # NOUVEAU - exécute les plans LLM
│   │   └── transition_generator.py   # RÉÉCRIRE pour utiliser plan_executor
│   │
│   ├── energy/                        # NOUVEAU
│   │   ├── __init__.py
│   │   ├── set_manager.py            # Gestion phases du set
│   │   └── serpentine.py             # Serpentine flow
│   │
│   └── llm/
│       └── planner.py                # ENRICHIR avec nouveau prompt
│
└── tests/                             # NOUVEAU
    ├── test_transitions.py
    ├── test_bass_swap.py
    └── test_harmonic.py
```

---

## CRITÈRES DE SUCCÈS

Quand tu auras terminé, une transition générée devra:

1. ✅ Avoir un bass swap NET (vérifiable en analysant les fréquences basses)
2. ✅ Être alignée sur les phrases (vérifiable en comptant les bars)
3. ✅ Respecter les règles harmoniques Camelot
4. ✅ Éviter les clashes vocaux
5. ✅ Avoir la bonne durée selon le contexte du set
6. ✅ Utiliser les effets de manière appropriée
7. ✅ Couper les tracks aux bons endroits (pas joués en entier)
8. ✅ Sonner comme un mix de DJ professionnel

---

## INSTRUCTIONS FINALES

1. **Explore d'abord** le code existant pour comprendre la structure
2. **Crée les modules de base** (theory, analysis enrichi)
3. **Implémente les transitions** une par une en commençant par STEM_BLEND
4. **Teste chaque module** individuellement
5. **Intègre le tout** dans le plan_executor
6. **Teste end-to-end** avec différents cas

**Prends le temps nécessaire. Je préfère un système qui fonctionne parfaitement plutôt qu'un système rapide et médiocre.**