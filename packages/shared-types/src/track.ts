/**
 * Section types for song structure analysis
 */
export type SectionType = 'intro' | 'verse' | 'chorus' | 'drop' | 'breakdown' | 'bridge' | 'outro' | 'other';

/**
 * Represents a section in a track's structure
 */
export interface TrackSection {
  /** Type of the section */
  type: SectionType;
  /** Start time in seconds */
  start: number;
  /** End time in seconds */
  end: number;
}

/**
 * Track structure analysis result
 */
export interface TrackStructure {
  /** Intro section boundaries */
  intro: {
    start: number;
    end: number;
  };
  /** Outro section boundaries */
  outro: {
    start: number;
    end: number;
  };
  /** All detected sections */
  sections: TrackSection[];
}

/**
 * Confidence scores for analysis results
 */
export interface AnalysisConfidence {
  /** BPM detection confidence (0-1) */
  bpm: number;
  /** Key detection confidence (0-1) */
  key: number;
}

/**
 * Complete audio analysis results for a track
 */
export interface TrackAnalysis {
  /** Beats per minute */
  bpm: number;
  /** Musical key (e.g., "Am", "C", "F#m") */
  key: string;
  /** Camelot wheel notation (e.g., "8A", "5B") */
  camelot: string;
  /** Energy level (0-1) */
  energy: number;
  /** Danceability score (0-1) */
  danceability: number;
  /** Loudness in dB */
  loudness: number;
  /** Confidence scores for analysis */
  confidence: AnalysisConfidence;
  /** Song structure (optional, may not always be detected) */
  structure?: TrackStructure;
}

/**
 * Represents an audio track in the system
 */
export interface Track {
  /** Unique identifier */
  id: string;
  /** Stored filename (sanitized) */
  filename: string;
  /** Original upload filename */
  originalName: string;
  /** Duration in seconds */
  duration: number;
  /** File size in bytes */
  fileSize: number;
  /** MIME type (e.g., "audio/mpeg", "audio/wav") */
  mimeType: string;
  /** Upload timestamp */
  uploadedAt: Date;
  /** Analysis results (populated after processing) */
  analysis?: TrackAnalysis;
}

/**
 * Track creation input (for API requests)
 */
export interface CreateTrackInput {
  projectId: string;
  filename: string;
  originalName: string;
  filePath: string;
  fileSize: number;
  mimeType: string;
}
