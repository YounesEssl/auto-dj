import {
  Injectable,
  NotFoundException,
  ForbiddenException,
  BadRequestException,
  Logger,
} from '@nestjs/common';
import { prisma, Prisma } from '@autodj/database';
import type { DraftStatus, DraftTransitionStatus, HarmonicCompatibility } from '@autodj/database';
import type { AnalyzeJobResult, DraftTransitionJobPayload } from '@autodj/shared-types';

import { CreateDraftDto } from './dto/create-draft.dto';

type SlotType = 'A' | 'B';

/**
 * Service for Draft data operations
 */
@Injectable()
export class DraftsService {
  private readonly logger = new Logger(DraftsService.name);

  /**
   * Find all drafts for a user
   */
  async findAllByUser(userId: string) {
    return prisma.draft.findMany({
      where: { userId },
      include: {
        trackA: {
          include: { analysis: true },
        },
        trackB: {
          include: { analysis: true },
        },
      },
      orderBy: { createdAt: 'desc' },
    });
  }

  /**
   * Find a draft by ID
   */
  async findById(id: string) {
    const draft = await prisma.draft.findUnique({
      where: { id },
      include: {
        trackA: {
          include: { analysis: true },
        },
        trackB: {
          include: { analysis: true },
        },
      },
    });

    if (!draft) {
      throw new NotFoundException('Draft not found');
    }

    return draft;
  }

  /**
   * Find a draft by ID and verify ownership
   */
  async findByIdAndUser(id: string, userId: string) {
    const draft = await this.findById(id);

    if (draft.userId !== userId) {
      throw new ForbiddenException('Access denied');
    }

    return draft;
  }

  /**
   * Create a new draft
   */
  async create(userId: string, dto: CreateDraftDto) {
    const name = dto.name || `Draft ${new Date().toLocaleDateString()}`;

    return prisma.draft.create({
      data: {
        name,
        userId,
        status: 'CREATED' ,
      },
    });
  }

  /**
   * Create a track for a draft slot (A or B)
   */
  async createTrackForSlot(
    draftId: string,
    userId: string,
    slot: SlotType,
    data: {
      filename: string;
      originalName: string;
      filePath: string;
      fileSize: number;
      mimeType: string;
    }
  ) {
    const draft = await this.findByIdAndUser(draftId, userId);

    // Check if slot is already occupied
    const existingTrackId = slot === 'A' ? draft.trackAId : draft.trackBId;
    if (existingTrackId) {
      throw new BadRequestException(`Slot ${slot} already has a track. Remove it first.`);
    }

    // Create track (without projectId since it's for a draft)
    const track = await prisma.track.create({
      data: {
        filename: data.filename,
        originalName: data.originalName,
        filePath: data.filePath,
        fileSize: data.fileSize,
        mimeType: data.mimeType,
      },
    });

    // Link track to draft slot
    const updateData = slot === 'A' ? { trackAId: track.id } : { trackBId: track.id };

    await prisma.draft.update({
      where: { id: draftId },
      data: {
        ...updateData,
        status: 'UPLOADING' ,
        // Reset transition when tracks change
        transitionStatus: 'PENDING' ,
        transitionFilePath: null,
        transitionDurationMs: null,
        transitionError: null,
        compatibilityScore: null,
        harmonicScore: null,
        bpmScore: null,
        energyScore: null,
        bpmDifference: null,
      },
    });

    return track;
  }

  /**
   * Remove a track from a draft slot
   */
  async removeTrackFromSlot(draftId: string, userId: string, slot: SlotType) {
    const draft = await this.findByIdAndUser(draftId, userId);

    const trackId = slot === 'A' ? draft.trackAId : draft.trackBId;
    if (!trackId) {
      throw new BadRequestException(`Slot ${slot} has no track`);
    }

    // Remove track from draft
    const updateData = slot === 'A' ? { trackAId: null } : { trackBId: null };

    await prisma.draft.update({
      where: { id: draftId },
      data: {
        ...updateData,
        status: 'CREATED' ,
        // Reset transition
        transitionStatus: 'PENDING' ,
        transitionFilePath: null,
        transitionDurationMs: null,
        transitionError: null,
        compatibilityScore: null,
        harmonicScore: null,
        bpmScore: null,
        energyScore: null,
        bpmDifference: null,
      },
    });

    // Delete the track (and its analysis via cascade)
    await prisma.track.delete({
      where: { id: trackId },
    });
  }

  /**
   * Swap tracks A and B
   */
  async swapTracks(draftId: string, userId: string) {
    const draft = await this.findByIdAndUser(draftId, userId);

    if (!draft.trackAId && !draft.trackBId) {
      throw new BadRequestException('No tracks to swap');
    }

    await prisma.draft.update({
      where: { id: draftId },
      data: {
        trackAId: draft.trackBId,
        trackBId: draft.trackAId,
        // Reset transition since order changed
        transitionStatus: 'PENDING' ,
        transitionFilePath: null,
        transitionDurationMs: null,
        transitionError: null,
      },
    });

    return this.findById(draftId);
  }

  /**
   * Save track analysis and recalculate compatibility if both tracks analyzed
   */
  async saveAnalysis(trackId: string, result: AnalyzeJobResult) {
    // Update track duration
    if (result.outroEnd) {
      await prisma.track.update({
        where: { id: trackId },
        data: { duration: result.outroEnd },
      });
    }

    // Upsert analysis
    await prisma.trackAnalysis.upsert({
      where: { trackId },
      create: {
        trackId,
        bpm: result.bpm,
        bpmConfidence: result.bpmConfidence,
        key: result.key,
        keyConfidence: result.keyConfidence,
        camelot: result.camelot,
        energy: result.energy,
        danceability: result.danceability,
        loudness: result.loudness,
        introStart: result.introStart,
        introEnd: result.introEnd,
        outroStart: result.outroStart,
        outroEnd: result.outroEnd,
        beats: result.beats as Prisma.InputJsonValue | undefined,
        structureJson: result.structureJson as Prisma.InputJsonValue | undefined,
      },
      update: {
        bpm: result.bpm,
        bpmConfidence: result.bpmConfidence,
        key: result.key,
        keyConfidence: result.keyConfidence,
        camelot: result.camelot,
        energy: result.energy,
        danceability: result.danceability,
        loudness: result.loudness,
        introStart: result.introStart,
        introEnd: result.introEnd,
        outroStart: result.outroStart,
        outroEnd: result.outroEnd,
        beats: result.beats as Prisma.InputJsonValue | undefined,
        structureJson: result.structureJson as Prisma.InputJsonValue | undefined,
      },
    });

    // Find the draft this track belongs to
    const draft = await prisma.draft.findFirst({
      where: {
        OR: [{ trackAId: trackId }, { trackBId: trackId }],
      },
      include: {
        trackA: { include: { analysis: true } },
        trackB: { include: { analysis: true } },
      },
    });

    if (!draft) {
      this.logger.warn(`Track ${trackId} is not associated with any draft`);
      return;
    }

    // Check if both tracks have analysis
    const trackAAnalysis = draft.trackA?.analysis;
    const trackBAnalysis = draft.trackB?.analysis;

    if (trackAAnalysis && trackBAnalysis) {
      // Both tracks analyzed, calculate compatibility
      await this.calculateAndSaveCompatibility(draft.id, trackAAnalysis, trackBAnalysis);
    } else {
      // Still analyzing
      await prisma.draft.update({
        where: { id: draft.id },
        data: { status: 'ANALYZING'  },
      });
    }
  }

  /**
   * Calculate and save compatibility scores between two tracks
   */
  private async calculateAndSaveCompatibility(
    draftId: string,
    analysisA: { bpm: number; camelot: string; energy: number },
    analysisB: { bpm: number; camelot: string; energy: number }
  ) {
    const harmonicResult = this.calculateHarmonicScore(analysisA.camelot, analysisB.camelot);
    const bpmResult = this.calculateBpmScore(analysisA.bpm, analysisB.bpm);
    const energyResult = this.calculateEnergyScore(analysisA.energy, analysisB.energy);

    // Weighted overall score
    const compatibilityScore = Math.round(
      harmonicResult.score * 0.5 + bpmResult.score * 0.3 + energyResult.score * 0.2
    );

    await prisma.draft.update({
      where: { id: draftId },
      data: {
        status: 'READY' ,
        compatibilityScore,
        harmonicScore: harmonicResult.score,
        bpmScore: bpmResult.score,
        energyScore: energyResult.score,
        bpmDifference: bpmResult.difference,
      },
    });

    this.logger.log(
      `Draft ${draftId} compatibility: ${compatibilityScore} (harmonic: ${harmonicResult.score}, bpm: ${bpmResult.score}, energy: ${energyResult.score})`
    );
  }

  /**
   * Calculate harmonic score based on Camelot wheel
   */
  private calculateHarmonicScore(
    camelotA: string,
    camelotB: string
  ): { score: number; type: HarmonicCompatibility } {
    const parseKey = (camelot: string) => {
      const match = camelot.match(/^(\d+)([AB])$/);
      if (!match || !match[1] || !match[2]) return { number: 0, mode: 'A' };
      return { number: parseInt(match[1], 10), mode: match[2] };
    };

    const keyA = parseKey(camelotA);
    const keyB = parseKey(camelotB);

    // Perfect Match
    if (camelotA === camelotB) {
      return { score: 100, type: 'PERFECT_MATCH' };
    }

    // Adjacent (±1, same mode)
    if (keyA.mode === keyB.mode) {
      const diff = this.circularDistance(keyA.number, keyB.number, 12);
      if (diff === 1) {
        return { score: 90, type: 'ADJACENT' };
      }
    }

    // Relative (same number, opposite mode)
    if (keyA.number === keyB.number && keyA.mode !== keyB.mode) {
      return { score: 85, type: 'RELATIVE' };
    }

    // Diagonal Adjacent
    if (keyA.mode !== keyB.mode) {
      const diff = this.circularDistance(keyA.number, keyB.number, 12);
      if (diff === 1) {
        return { score: 75, type: 'DIAGONAL_ADJACENT' };
      }
    }

    // Energy Boost (+7)
    if (keyA.mode === keyB.mode) {
      const expectedB = ((keyA.number + 6) % 12) + 1;
      if (keyB.number === expectedB) {
        return { score: 65, type: 'ENERGY_BOOST' };
      }
    }

    // Compatible (±2)
    if (keyA.mode === keyB.mode) {
      const diff = this.circularDistance(keyA.number, keyB.number, 12);
      if (diff === 2) {
        return { score: 60, type: 'COMPATIBLE' };
      }
    }

    return { score: 20, type: 'RISKY' };
  }

  private circularDistance(a: number, b: number, max: number): number {
    const diff = Math.abs(a - b);
    return Math.min(diff, max - diff);
  }

  /**
   * Calculate BPM score
   */
  private calculateBpmScore(bpmA: number, bpmB: number): { score: number; difference: number } {
    const difference = (Math.abs(bpmA - bpmB) / bpmA) * 100;

    let score: number;
    if (difference <= 2) score = 100;
    else if (difference <= 4) score = 85;
    else if (difference <= 6) score = 70;
    else if (difference <= 8) score = 55;
    else score = 25;

    return { score, difference: Math.round(difference * 100) / 100 };
  }

  /**
   * Calculate energy score
   */
  private calculateEnergyScore(
    energyA: number,
    energyB: number
  ): { score: number; difference: number } {
    const difference = energyB - energyA;

    let score: number;
    if (difference >= 0.05 && difference <= 0.15) score = 100;
    else if (difference >= -0.05 && difference < 0.05) score = 85;
    else if (difference > 0.15 && difference <= 0.25) score = 70;
    else if (difference >= -0.15 && difference < -0.05) score = 65;
    else if (difference >= -0.25 && difference < -0.15) score = 45;
    else score = 25;

    return { score, difference: Math.round(difference * 1000) / 1000 };
  }

  /**
   * Update draft status
   */
  async updateStatus(id: string, status: DraftStatus, errorMessage?: string) {
    return prisma.draft.update({
      where: { id },
      data: { status, errorMessage },
    });
  }

  /**
   * Update transition status and result
   */
  async updateTransitionResult(
    draftId: string,
    result: {
      status: DraftTransitionStatus;
      filePath?: string;
      durationMs?: number;
      mode?: 'STEMS' | 'CROSSFADE';
      trackAOutroMs?: number;
      trackBIntroMs?: number;
      error?: string;
    }
  ) {
    return prisma.draft.update({
      where: { id: draftId },
      data: {
        transitionStatus: result.status,
        transitionFilePath: result.filePath,
        transitionDurationMs: result.durationMs,
        transitionMode: result.mode,
        trackAOutroMs: result.trackAOutroMs,
        trackBIntroMs: result.trackBIntroMs,
        transitionError: result.error,
        status: result.status === 'COMPLETED' ? ('COMPLETED' ) : undefined,
      },
    });
  }

  /**
   * Prepare transition job payload
   */
  async prepareTransitionJobPayload(draftId: string, userId: string): Promise<DraftTransitionJobPayload> {
    const draft = await this.findByIdAndUser(draftId, userId);

    // Allow regeneration from READY, COMPLETED, or ERROR states
    const allowedStatuses = ['READY', 'COMPLETED', 'ERROR'];
    if (!allowedStatuses.includes(draft.status)) {
      throw new BadRequestException(`Draft must be READY, COMPLETED, or ERROR to generate transition. Current status: ${draft.status}`);
    }

    if (!draft.trackA || !draft.trackB) {
      throw new BadRequestException('Both tracks must be uploaded');
    }

    const analysisA = draft.trackA.analysis;
    const analysisB = draft.trackB.analysis;

    if (!analysisA || !analysisB) {
      throw new BadRequestException('Both tracks must be analyzed');
    }

    // Calculate intro/outro points with fallbacks
    const trackADurationMs = (draft.trackA.duration || 0) * 1000;
    const trackBDurationMs = (draft.trackB.duration || 0) * 1000;

    // Outro start for track A (in ms) - fallback to last 60 seconds
    const trackAOutroStartMs = analysisA.outroStart
      ? analysisA.outroStart * 1000
      : Math.max(0, trackADurationMs - 60000);

    // Intro end for track B (in ms) - fallback to first 60 seconds
    const trackBIntroEndMs = analysisA.introEnd
      ? analysisB.introEnd! * 1000
      : Math.min(trackBDurationMs, 60000);

    return {
      draftId,
      trackAPath: draft.trackA.filePath,
      trackBPath: draft.trackB.filePath,
      trackABpm: analysisA.bpm,
      trackBBpm: analysisB.bpm,
      trackABeats: Array.isArray(analysisA.beats) ? (analysisA.beats as number[]) : [],
      trackBBeats: Array.isArray(analysisB.beats) ? (analysisB.beats as number[]) : [],
      trackAOutroStartMs,
      trackBIntroEndMs,
      trackAEnergy: analysisA.energy,
      trackBEnergy: analysisB.energy,
      trackADurationMs,
      trackBDurationMs,
      outputPath: `drafts/${draftId}/transition.mp3`,
      // Camelot keys for LLM-powered transition planning
      trackAKey: analysisA.camelot,
      trackBKey: analysisB.camelot,
    };
  }

  /**
   * Delete a draft and all associated data
   */
  async delete(id: string, userId: string) {
    const draft = await this.findByIdAndUser(id, userId);

    // Delete associated tracks (cascade will handle analysis)
    if (draft.trackAId) {
      await prisma.track.delete({ where: { id: draft.trackAId } }).catch(() => {});
    }
    if (draft.trackBId) {
      await prisma.track.delete({ where: { id: draft.trackBId } }).catch(() => {});
    }

    // Delete draft
    return prisma.draft.delete({ where: { id } });
  }
}
