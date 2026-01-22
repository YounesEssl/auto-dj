import { Injectable, Logger } from '@nestjs/common';
import { prisma, HarmonicCompatibility } from '@autodj/database';
import type { Transition, OrderingResult } from '@autodj/shared-types';

/**
 * Track with analysis data for ordering calculations
 */
interface TrackWithAnalysis {
  id: string;
  analysis: {
    bpm: number;
    camelot: string;
    energy: number;
  } | null;
}

/**
 * Internal transition data during calculation
 */
interface TransitionData {
  fromTrackId: string;
  toTrackId: string;
  position: number;
  score: number;
  harmonicScore: number;
  bpmScore: number;
  energyScore: number;
  compatibilityType: HarmonicCompatibility;
  bpmDifference: number;
  energyDifference: number;
}


/**
 * Service for calculating optimal track order in a mix
 * Implements the Camelot wheel-based harmonic mixing algorithm
 */
@Injectable()
export class OrderingService {
  private readonly logger = new Logger(OrderingService.name);

  /**
   * Calculate the optimal track order for a project
   * Uses Nearest Neighbor algorithm with weighted scoring
   */
  async calculateOptimalOrder(projectId: string): Promise<OrderingResult> {
    const startTime = Date.now();
    this.logger.log(`Calculating optimal order for project: ${projectId}`);

    // Get all tracks with their analysis
    const project = await prisma.project.findUnique({
      where: { id: projectId },
      include: {
        tracks: {
          include: { analysis: true },
        },
      },
    });

    if (!project) {
      throw new Error(`Project not found: ${projectId}`);
    }

    // Filter tracks with complete analysis
    const tracksWithAnalysis: TrackWithAnalysis[] = [];
    const excludedTrackIds: string[] = [];

    for (const track of project.tracks) {
      if (track.analysis && track.analysis.bpm && track.analysis.camelot && track.analysis.energy !== null) {
        tracksWithAnalysis.push({
          id: track.id,
          analysis: {
            bpm: track.analysis.bpm,
            camelot: track.analysis.camelot,
            energy: track.analysis.energy,
          },
        });
      } else {
        excludedTrackIds.push(track.id);
        this.logger.warn(`Track ${track.id} excluded: missing analysis data`);
      }
    }

    // Handle edge cases
    if (tracksWithAnalysis.length < 2) {
      const orderedTrackIds = tracksWithAnalysis.map(t => t.id);
      const processingTimeMs = Date.now() - startTime;

      // Save minimal result
      await this.saveOrderingResult(projectId, orderedTrackIds, [], 0, processingTimeMs);

      return {
        projectId,
        orderedTrackIds,
        transitions: [],
        averageScore: 0,
        processingTimeMs,
        excludedTrackIds,
      };
    }

    // Run Nearest Neighbor algorithm
    const { orderedTracks, transitions } = this.nearestNeighborOrder(tracksWithAnalysis);
    const orderedTrackIds = orderedTracks.map(t => t.id);

    // Calculate average score
    const averageScore = transitions.length > 0
      ? Math.round(transitions.reduce((sum, t) => sum + t.score, 0) / transitions.length)
      : 0;

    const processingTimeMs = Date.now() - startTime;

    // Save to database
    await this.saveOrderingResult(projectId, orderedTrackIds, transitions, averageScore, processingTimeMs);

    this.logger.log(`Ordering complete: ${orderedTrackIds.length} tracks, avg score: ${averageScore}, time: ${processingTimeMs}ms`);

    // Convert to full Transition objects for return
    const fullTransitions = await this.getTransitions(projectId);

    return {
      projectId,
      orderedTrackIds,
      transitions: fullTransitions,
      averageScore,
      processingTimeMs,
      excludedTrackIds,
    };
  }

  /**
   * Recalculate transitions for a manually specified track order
   * Used when user manually reorders tracks in the timeline
   */
  async recalculateTransitionsForOrder(projectId: string, orderedTrackIds: string[]): Promise<{
    transitions: Transition[];
    averageScore: number;
  }> {
    this.logger.log(`Recalculating transitions for manual order: ${projectId}`);

    if (orderedTrackIds.length < 2) {
      // Not enough tracks for transitions
      await prisma.transition.deleteMany({ where: { projectId } });
      await prisma.project.update({
        where: { id: projectId },
        data: { averageMixScore: 0 },
      });
      return { transitions: [], averageScore: 0 };
    }

    // Get tracks with analysis
    const tracks = await prisma.track.findMany({
      where: { id: { in: orderedTrackIds } },
      include: { analysis: true },
    });

    // Build a map for quick lookup
    const trackMap = new Map(tracks.map(t => [t.id, t]));

    // Build ordered tracks with analysis
    const orderedTracks: TrackWithAnalysis[] = [];
    for (const trackId of orderedTrackIds) {
      const track = trackMap.get(trackId);
      if (track?.analysis) {
        orderedTracks.push({
          id: track.id,
          analysis: {
            bpm: track.analysis.bpm,
            camelot: track.analysis.camelot,
            energy: track.analysis.energy,
          },
        });
      }
    }

    if (orderedTracks.length < 2) {
      await prisma.transition.deleteMany({ where: { projectId } });
      await prisma.project.update({
        where: { id: projectId },
        data: { averageMixScore: 0 },
      });
      return { transitions: [], averageScore: 0 };
    }

    // Calculate transitions for the given order
    const transitionData: TransitionData[] = [];
    for (let i = 0; i < orderedTracks.length - 1; i++) {
      const current = orderedTracks[i];
      const next = orderedTracks[i + 1];
      if (current && next) {
        const transition = this.calculateTransition(current, next, i);
        transitionData.push(transition);
      }
    }

    // Calculate average score
    const averageScore = transitionData.length > 0
      ? Math.round(transitionData.reduce((sum, t) => sum + t.score, 0) / transitionData.length)
      : 0;

    // Save to database
    await prisma.transition.deleteMany({ where: { projectId } });

    if (transitionData.length > 0) {
      await prisma.transition.createMany({
        data: transitionData.map(t => ({
          projectId,
          fromTrackId: t.fromTrackId,
          toTrackId: t.toTrackId,
          position: t.position,
          score: t.score,
          harmonicScore: t.harmonicScore,
          bpmScore: t.bpmScore,
          energyScore: t.energyScore,
          compatibilityType: t.compatibilityType,
          bpmDifference: t.bpmDifference,
          energyDifference: t.energyDifference,
        })),
      });
    }

    // Update project average score
    await prisma.project.update({
      where: { id: projectId },
      data: { averageMixScore: averageScore },
    });

    this.logger.log(`Recalculated ${transitionData.length} transitions, avg score: ${averageScore}`);

    // Return full transitions
    const transitions = await this.getTransitions(projectId);
    return { transitions, averageScore };
  }

  /**
   * Get transitions for a project
   */
  async getTransitions(projectId: string): Promise<Transition[]> {
    const transitions = await prisma.transition.findMany({
      where: { projectId },
      orderBy: { position: 'asc' },
    });

    return transitions.map(t => ({
      id: t.id,
      projectId: t.projectId,
      fromTrackId: t.fromTrackId,
      toTrackId: t.toTrackId,
      position: t.position,
      score: t.score,
      harmonicScore: t.harmonicScore,
      bpmScore: t.bpmScore,
      energyScore: t.energyScore,
      compatibilityType: t.compatibilityType,
      bpmDifference: t.bpmDifference,
      energyDifference: t.energyDifference,
      audioStatus: t.audioStatus,
      audioFilePath: t.audioFilePath ?? undefined,
      audioDurationMs: t.audioDurationMs ?? undefined,
      trackACutMs: t.trackACutMs ?? undefined,
      trackBStartMs: t.trackBStartMs ?? undefined,
      audioError: t.audioError ?? undefined,
      createdAt: t.createdAt,
    }));
  }

  /**
   * Nearest Neighbor algorithm implementation
   * Step 1: Select track with lowest energy (tie-breaker: lowest BPM)
   * Step 2: Iteratively select the best scoring next track
   */
  private nearestNeighborOrder(tracks: TrackWithAnalysis[]): {
    orderedTracks: TrackWithAnalysis[];
    transitions: TransitionData[];
  } {
    const remaining = [...tracks];
    const ordered: TrackWithAnalysis[] = [];
    const transitions: TransitionData[] = [];

    // Step 1: Select starting track (lowest energy, tie-breaker: lowest BPM)
    remaining.sort((a, b) => {
      const energyA = a.analysis!.energy;
      const energyB = b.analysis!.energy;
      if (energyA !== energyB) {
        return energyA - energyB;
      }
      return a.analysis!.bpm - b.analysis!.bpm;
    });

    const firstTrack = remaining.shift()!;
    ordered.push(firstTrack);
    this.logger.debug(`Starting track: ${firstTrack.id} (energy: ${firstTrack.analysis!.energy}, bpm: ${firstTrack.analysis!.bpm})`);

    // Step 2: Greedily select best next track
    while (remaining.length > 0) {
      const current = ordered[ordered.length - 1];
      if (!current) break;

      let bestIndex = 0;
      let bestScore = -Infinity;
      let bestTransition: TransitionData | null = null;

      for (let i = 0; i < remaining.length; i++) {
        const candidate = remaining[i];
        if (!candidate) continue;

        const transition = this.calculateTransition(
          current,
          candidate,
          ordered.length - 1
        );

        if (transition.score > bestScore) {
          bestScore = transition.score;
          bestIndex = i;
          bestTransition = transition;
        } else if (transition.score === bestScore && bestTransition) {
          // Tie-breaker: choose track with energy closest to current
          const currentEnergy = current.analysis!.energy;
          const candidateEnergy = candidate.analysis?.energy ?? 0;
          const bestCandidate = remaining[bestIndex];
          const bestCandidateEnergy = bestCandidate?.analysis?.energy ?? 0;
          const candidateEnergyDiff = Math.abs(candidateEnergy - currentEnergy);
          const bestEnergyDiff = Math.abs(bestCandidateEnergy - currentEnergy);
          if (candidateEnergyDiff < bestEnergyDiff) {
            bestIndex = i;
            bestTransition = transition;
          }
        }
      }

      const nextTrack = remaining.splice(bestIndex, 1)[0];
      if (nextTrack) {
        ordered.push(nextTrack);
      }

      if (bestTransition) {
        transitions.push(bestTransition);
      }
    }

    return { orderedTracks: ordered, transitions };
  }

  /**
   * Calculate transition data between two tracks
   */
  private calculateTransition(
    trackA: TrackWithAnalysis,
    trackB: TrackWithAnalysis,
    position: number
  ): TransitionData {
    const analysisA = trackA.analysis!;
    const analysisB = trackB.analysis!;

    // Calculate individual scores
    const harmonicScore = this.calculateHarmonicScore(analysisA.camelot, analysisB.camelot);
    const bpmScore = this.calculateBpmScore(analysisA.bpm, analysisB.bpm);
    const energyScore = this.calculateEnergyScore(analysisA.energy, analysisB.energy);

    // Calculate weighted final score
    const score = Math.round(
      (harmonicScore.score * 0.50) +
      (bpmScore.score * 0.30) +
      (energyScore.score * 0.20)
    );

    return {
      fromTrackId: trackA.id,
      toTrackId: trackB.id,
      position,
      score,
      harmonicScore: harmonicScore.score,
      bpmScore: bpmScore.score,
      energyScore: energyScore.score,
      compatibilityType: harmonicScore.type,
      bpmDifference: bpmScore.difference,
      energyDifference: energyScore.difference,
    };
  }

  /**
   * Calculate harmonic compatibility score based on Camelot wheel
   * Returns score (0-100) and compatibility type
   */
  private calculateHarmonicScore(camelotA: string, camelotB: string): {
    score: number;
    type: HarmonicCompatibility;
  } {
    // Parse Camelot notation (e.g., "8A" -> number: 8, mode: "A")
    const parseKey = (camelot: string) => {
      const match = camelot.match(/^(\d+)([AB])$/);
      if (!match || !match[1] || !match[2]) return { number: 0, mode: 'A' };
      return { number: parseInt(match[1], 10), mode: match[2] };
    };

    const keyA = parseKey(camelotA);
    const keyB = parseKey(camelotB);

    // 1. Perfect Match (same key)
    if (camelotA === camelotB) {
      return { score: 100, type: 'PERFECT_MATCH' };
    }

    // 2. Adjacent (±1 on wheel, same mode)
    if (keyA.mode === keyB.mode) {
      const diff = this.circularDistance(keyA.number, keyB.number, 12);
      if (diff === 1) {
        return { score: 90, type: 'ADJACENT' };
      }
    }

    // 3. Relative (same number, opposite mode)
    if (keyA.number === keyB.number && keyA.mode !== keyB.mode) {
      return { score: 85, type: 'RELATIVE' };
    }

    // 4. Diagonal Adjacent (±1 on wheel AND mode change)
    if (keyA.mode !== keyB.mode) {
      const diff = this.circularDistance(keyA.number, keyB.number, 12);
      if (diff === 1) {
        return { score: 75, type: 'DIAGONAL_ADJACENT' };
      }
    }

    // 5. Energy Boost (+7 positions, same mode)
    if (keyA.mode === keyB.mode) {
      const expectedB = ((keyA.number + 6) % 12) + 1; // +7 positions (circular)
      if (keyB.number === expectedB) {
        return { score: 65, type: 'ENERGY_BOOST' };
      }
    }

    // 6. Compatible (±2 positions, same mode)
    if (keyA.mode === keyB.mode) {
      const diff = this.circularDistance(keyA.number, keyB.number, 12);
      if (diff === 2) {
        return { score: 60, type: 'COMPATIBLE' };
      }
    }

    // 7. Risky (all other combinations)
    return { score: 20, type: 'RISKY' };
  }

  /**
   * Calculate circular distance on the Camelot wheel (1-12)
   */
  private circularDistance(a: number, b: number, max: number): number {
    const diff = Math.abs(a - b);
    return Math.min(diff, max - diff);
  }

  /**
   * Calculate BPM compatibility score
   * Based on percentage difference with ±8% stretch limit
   */
  private calculateBpmScore(bpmA: number, bpmB: number): {
    score: number;
    difference: number;
  } {
    // Calculate percentage difference
    const difference = Math.abs(bpmA - bpmB) / bpmA * 100;

    let score: number;
    if (difference <= 2) {
      score = 100;
    } else if (difference <= 4) {
      score = 85;
    } else if (difference <= 6) {
      score = 70;
    } else if (difference <= 8) {
      score = 55;
    } else {
      score = 25;
    }

    return { score, difference: Math.round(difference * 100) / 100 };
  }

  /**
   * Calculate energy flow score
   * Based on energy progression (positive = building, negative = dropping)
   */
  private calculateEnergyScore(energyA: number, energyB: number): {
    score: number;
    difference: number;
  } {
    // Calculate energy difference (can be negative)
    const difference = energyB - energyA;

    let score: number;
    if (difference >= 0.05 && difference <= 0.15) {
      // Montée douce (gentle rise) - ideal for building energy
      score = 100;
    } else if (difference >= -0.05 && difference < 0.05) {
      // Stable - maintains level
      score = 85;
    } else if (difference > 0.15 && difference <= 0.25) {
      // Montée forte (strong rise) - acceptable
      score = 70;
    } else if (difference >= -0.15 && difference < -0.05) {
      // Descente douce (gentle drop) - creates a valley
      score = 65;
    } else if (difference >= -0.25 && difference < -0.15) {
      // Descente forte (strong drop) - breaks energy
      score = 45;
    } else {
      // Variation extrême (>0.25 or <-0.25) - too abrupt
      score = 25;
    }

    return { score, difference: Math.round(difference * 1000) / 1000 };
  }

  /**
   * Save ordering result to database
   */
  private async saveOrderingResult(
    projectId: string,
    orderedTrackIds: string[],
    transitions: TransitionData[],
    averageScore: number,
    _processingTimeMs: number
  ): Promise<void> {
    // Delete existing transitions for this project
    await prisma.transition.deleteMany({
      where: { projectId },
    });

    // Create new transitions
    if (transitions.length > 0) {
      await prisma.transition.createMany({
        data: transitions.map(t => ({
          projectId,
          fromTrackId: t.fromTrackId,
          toTrackId: t.toTrackId,
          position: t.position,
          score: t.score,
          harmonicScore: t.harmonicScore,
          bpmScore: t.bpmScore,
          energyScore: t.energyScore,
          compatibilityType: t.compatibilityType,
          bpmDifference: t.bpmDifference,
          energyDifference: t.energyDifference,
        })),
      });
    }

    // Update project
    await prisma.project.update({
      where: { id: projectId },
      data: {
        orderedTracks: orderedTrackIds,
        averageMixScore: averageScore,
        lastOrderedAt: new Date(),
        status: 'READY',
      },
    });
  }
}
