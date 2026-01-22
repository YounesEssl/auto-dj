import { Processor, WorkerHost } from '@nestjs/bullmq';
import { Logger, Inject, forwardRef } from '@nestjs/common';
import { Job } from 'bullmq';
import type { AnalyzeJobResult, MixJobResult, TransitionAudioJobResult, OrderingResult, DraftTransitionJobResult } from '@autodj/shared-types';
import { prisma, Prisma } from '@autodj/database';

import { QUEUE_NAMES } from '../queue.constants';
import { WebsocketGateway } from '../../websocket/websocket.gateway';
import { OrderingService } from '../../ordering/ordering.service';
import { ChatService } from '../../chat/chat.service';

interface ChatReorderResult {
  response: string;
  new_order?: string[] | null;
  reasoning?: string | null;
  changes_made?: string[];
}

interface ResultJob {
  type: 'analyze' | 'transition_audio' | 'mix' | 'draft_transition' | 'chat_reorder' | 'progress';
  projectId?: string;
  trackId?: string;
  transitionId?: string;
  draftId?: string;
  result?: AnalyzeJobResult | TransitionAudioJobResult | MixJobResult | DraftTransitionJobResult | ChatReorderResult;
  error?: string;
  // Progress fields
  stage?: string;
  progress?: number;
  message?: string;
}

/**
 * Consumer for processing results from Python workers
 */
@Processor(QUEUE_NAMES.RESULTS)
export class ResultConsumer extends WorkerHost {
  private readonly logger = new Logger(ResultConsumer.name);

  constructor(
    private readonly websocketGateway: WebsocketGateway,
    private readonly orderingService: OrderingService,
    @Inject(forwardRef(() => ChatService))
    private readonly chatService: ChatService,
  ) {
    super();
    this.logger.log('ResultConsumer initialized - listening for results');
  }

  async process(job: Job<ResultJob>): Promise<void> {
    const { type, projectId, trackId, transitionId, draftId, result, error } = job.data;

    this.logger.log(`=== PROCESSING RESULT ===`);
    this.logger.log(`Type: ${type}, Project: ${projectId}, Track: ${trackId}, Transition: ${transitionId}, Draft: ${draftId}`);

    if (error) {
      if (type === 'draft_transition' && draftId) {
        await this.handleDraftError(draftId, error);
      } else if (projectId) {
        await this.handleError(type, projectId, error, transitionId);
      }
      return;
    }

    switch (type) {
      case 'analyze':
        await this.handleAnalyzeResult(projectId!, trackId!, result as AnalyzeJobResult);
        break;
      case 'transition_audio':
        await this.handleTransitionAudioResult(projectId!, transitionId!, result as TransitionAudioJobResult);
        break;
      case 'mix':
        await this.handleMixResult(projectId!, result as MixJobResult);
        break;
      case 'draft_transition':
        await this.handleDraftTransitionResult(draftId!, result as DraftTransitionJobResult);
        break;
      case 'chat_reorder':
        await this.handleChatReorderResult(projectId!, result as ChatReorderResult);
        break;
      case 'progress':
        this.handleProgressUpdate(job.data);
        break;
    }
  }

  /**
   * Handle real-time progress updates from Python worker
   */
  private handleProgressUpdate(data: ResultJob): void {
    const { projectId, transitionId, draftId, stage, progress, message } = data;

    this.logger.debug(`Progress update: ${stage} ${progress}% - ${message}`);

    // Send progress to project room (for transition generation in projects)
    if (projectId && transitionId) {
      this.websocketGateway.sendTransitionProgress(projectId, {
        projectId,
        transitionId,
        status: 'PROCESSING',
        progress,
        stage,
        message,
      });
    }

    // Send progress to draft room (for draft transition generation)
    if (draftId) {
      this.websocketGateway.sendDraftProgress(draftId, {
        draftId,
        step: (stage as any) || 'extraction',
        progress: progress || 0,
        status: 'PROCESSING',
        message,
      });
    }
  }

  /**
   * Handle analysis result from Python worker
   */
  private async handleAnalyzeResult(
    projectId: string,
    trackId: string,
    result: AnalyzeJobResult
  ): Promise<void> {
    // Update track duration if provided
    if (result.duration) {
      await prisma.track.update({
        where: { id: trackId },
        data: { duration: result.duration },
      });
    }

    // Save analysis to database
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
        beats: result.beats as Prisma.InputJsonValue | undefined,
        introStart: result.introStart,
        introEnd: result.introEnd,
        outroStart: result.outroStart,
        outroEnd: result.outroEnd,
        structureJson: result.structureJson as Prisma.InputJsonValue | undefined,
        // Mixability
        introInstrumentalMs: result.introInstrumentalMs,
        outroInstrumentalMs: result.outroInstrumentalMs,
        vocalPercentage: result.vocalPercentage,
        vocalIntensity: result.vocalIntensity,
        maxBlendInDurationMs: result.maxBlendInDurationMs,
        maxBlendOutDurationMs: result.maxBlendOutDurationMs,
        bestMixInPointMs: result.bestMixInPointMs,
        bestMixOutPointMs: result.bestMixOutPointMs,
        mixFriendly: result.mixFriendly ?? true,
        mixabilityWarnings: result.mixabilityWarnings ?? [],
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
        beats: result.beats as Prisma.InputJsonValue | undefined,
        introStart: result.introStart,
        introEnd: result.introEnd,
        outroStart: result.outroStart,
        outroEnd: result.outroEnd,
        structureJson: result.structureJson as Prisma.InputJsonValue | undefined,
        // Mixability
        introInstrumentalMs: result.introInstrumentalMs,
        outroInstrumentalMs: result.outroInstrumentalMs,
        vocalPercentage: result.vocalPercentage,
        vocalIntensity: result.vocalIntensity,
        maxBlendInDurationMs: result.maxBlendInDurationMs,
        maxBlendOutDurationMs: result.maxBlendOutDurationMs,
        bestMixInPointMs: result.bestMixInPointMs,
        bestMixOutPointMs: result.bestMixOutPointMs,
        mixFriendly: result.mixFriendly ?? true,
        mixabilityWarnings: result.mixabilityWarnings ?? [],
      },
    });

    // Check if all tracks in project are analyzed
    const project = await prisma.project.findUnique({
      where: { id: projectId },
      include: {
        tracks: {
          include: { analysis: true },
        },
      },
    });

    // If not a project, check if it's a draft
    if (!project) {
      await this.handleDraftAnalysisComplete(projectId, trackId);
      return;
    }

    if (project) {
      const allAnalyzed = project.tracks.every((t) => t.analysis);
      const progress = Math.round(
        (project.tracks.filter((t) => t.analysis).length / project.tracks.length) * 100
      );

      // Notify via WebSocket
      this.websocketGateway.sendProgress(projectId, {
        projectId,
        stage: 'analyzing',
        progress,
        currentStep: `Analyzed track ${project.tracks.filter((t) => t.analysis).length}/${project.tracks.length}`,
      });

      // Update project status if all analyzed
      if (allAnalyzed) {
        await prisma.project.update({
          where: { id: projectId },
          data: { status: 'ORDERING' },
        });

        this.websocketGateway.sendProgress(projectId, {
          projectId,
          stage: 'ordering',
          progress: 0,
          currentStep: 'Calculating optimal track order...',
        });

        // Calculate optimal order
        try {
          const orderingResult: OrderingResult = await this.orderingService.calculateOptimalOrder(projectId);

          // Emit mix:ordered event with full transition data
          this.websocketGateway.sendMixOrdered(projectId, {
            projectId,
            orderedTrackIds: orderingResult.orderedTrackIds,
            transitions: orderingResult.transitions,
            averageScore: orderingResult.averageScore,
            processingTimeMs: orderingResult.processingTimeMs,
          });

          // Also send progress update for UI stepper
          this.websocketGateway.sendProgress(projectId, {
            projectId,
            stage: 'ready',
            progress: 100,
            currentStep: `Ready to generate mix! (Score: ${orderingResult.averageScore}/100)`,
          });

          this.logger.log(`Ordering complete for project: ${projectId}, avg score: ${orderingResult.averageScore}`);
        } catch (orderError) {
          this.logger.error(`Ordering failed: ${orderError}`);
          await this.handleError('ordering', projectId, String(orderError));
        }
      }
    }

    this.logger.log(`Analysis saved for track: ${trackId}`);
  }

  /**
   * Handle transition audio result from Python worker
   */
  private async handleTransitionAudioResult(
    projectId: string,
    transitionId: string,
    result: TransitionAudioJobResult
  ): Promise<void> {
    // Update transition with audio info
    await prisma.transition.update({
      where: { id: transitionId },
      data: {
        audioStatus: 'COMPLETED',
        audioFilePath: result.audioFilePath,
        audioDurationMs: result.audioDurationMs,
        trackACutMs: result.trackACutMs,
        trackBStartMs: result.trackBStartMs,
      },
    });

    // Check if all transitions for the project are complete
    const transitions = await prisma.transition.findMany({
      where: { projectId },
    });

    const completedCount = transitions.filter(t => t.audioStatus === 'COMPLETED').length;
    const totalCount = transitions.length;
    const progress = Math.round((completedCount / totalCount) * 100);

    // Notify via WebSocket
    this.websocketGateway.sendTransitionProgress(projectId, {
      projectId,
      transitionId,
      status: 'COMPLETED',
      progress,
      completedCount,
      totalCount,
    });

    // If all transitions complete, update project status
    if (completedCount === totalCount) {
      await prisma.project.update({
        where: { id: projectId },
        data: { status: 'READY' },
      });

      this.websocketGateway.sendProgress(projectId, {
        projectId,
        stage: 'ready',
        progress: 100,
        currentStep: 'All transitions generated! Ready to generate final mix.',
      });
    }

    this.logger.log(`Transition audio saved: ${transitionId} (${completedCount}/${totalCount})`);
  }

  /**
   * Handle mix result from Python worker
   */
  private async handleMixResult(projectId: string, result: MixJobResult): Promise<void> {
    this.logger.log(`Processing mix result with ${result.segments?.length || 0} segments, outputFile: ${result.outputFile}`);

    // Delete existing mix segments for this project
    await prisma.mixSegment.deleteMany({
      where: { projectId },
    });

    // Create mix segments from result
    if (result.segments && result.segments.length > 0) {
      for (const segment of result.segments) {
        await prisma.mixSegment.create({
          data: {
            projectId,
            position: segment.position,
            type: segment.type,
            trackId: segment.trackId,
            transitionId: segment.transitionId,
            startMs: segment.startMs,
            endMs: segment.endMs,
            durationMs: segment.durationMs,
            audioFilePath: segment.audioFilePath,
            audioStatus: segment.audioError ? 'ERROR' : (segment.audioFilePath ? 'COMPLETED' : 'PENDING'),
            audioError: segment.audioError,
          },
        });
      }
    }

    // Determine final status based on outputFile
    const hasOutputFile = !!result.outputFile;
    const storagePath = process.env.STORAGE_PATH || 'storage';
    const outputFilePath = hasOutputFile ? `${storagePath}/${result.outputFile}` : null;

    // Update project status and outputFile
    await prisma.project.update({
      where: { id: projectId },
      data: {
        status: hasOutputFile ? 'COMPLETED' : 'READY',
        outputFile: outputFilePath,
        errorMessage: result.concatenationError || null,
      },
    });

    // Notify via WebSocket
    this.websocketGateway.sendProgress(projectId, {
      projectId,
      stage: hasOutputFile ? 'completed' : 'ready',
      progress: 100,
      currentStep: hasOutputFile
        ? 'Mix complete! Ready for playback.'
        : 'Segments generated but final mix failed. Check error message.',
    });

    this.logger.log(`Mix completed for project: ${projectId} with ${result.segments?.length || 0} segments, outputFile: ${outputFilePath}`);
  }

  /**
   * Handle error from Python worker
   */
  private async handleError(
    type: string,
    projectId: string,
    error: string,
    transitionId?: string
  ): Promise<void> {
    // If this is a transition error, update the specific transition
    if (type === 'transition_audio' && transitionId) {
      await prisma.transition.update({
        where: { id: transitionId },
        data: {
          audioStatus: 'ERROR',
          audioError: error,
        },
      });

      this.websocketGateway.sendTransitionProgress(projectId, {
        projectId,
        transitionId,
        status: 'ERROR',
        error,
      });

      this.logger.error(`Transition ${transitionId} failed: ${error}`);
      return;
    }

    // For other errors, update the project
    await prisma.project.update({
      where: { id: projectId },
      data: {
        status: 'FAILED',
        errorMessage: error,
      },
    });

    // Notify via WebSocket
    this.websocketGateway.sendProgress(projectId, {
      projectId,
      stage: 'failed',
      progress: 0,
      error,
    });

    this.logger.error(`${type} failed for project ${projectId}: ${error}`);
  }

  /**
   * Handle draft transition result from Python worker
   */
  private async handleDraftTransitionResult(
    draftId: string,
    result: DraftTransitionJobResult
  ): Promise<void> {
    // Update draft with transition result
    await prisma.draft.update({
      where: { id: draftId },
      data: {
        status: 'COMPLETED',
        transitionStatus: 'COMPLETED',
        transitionFilePath: result.transitionFilePath,
        transitionDurationMs: result.transitionDurationMs,
        transitionMode: result.transitionMode,
        trackAOutroMs: result.trackAOutroMs,
        trackBIntroMs: result.trackBIntroMs,
        // Cut points for seamless playback (to avoid audio duplication)
        trackAPlayUntilMs: result.trackAPlayUntilMs,
        trackBStartFromMs: result.trackBStartFromMs,
      },
    });

    // Notify via WebSocket
    this.websocketGateway.sendDraftComplete(draftId, {
      draftId,
      transitionFilePath: result.transitionFilePath,
      transitionDurationMs: result.transitionDurationMs,
      transitionMode: result.transitionMode,
      trackAOutroMs: result.trackAOutroMs,
      trackBIntroMs: result.trackBIntroMs,
      // Cut points for seamless playback
      trackAPlayUntilMs: result.trackAPlayUntilMs,
      trackBStartFromMs: result.trackBStartFromMs,
    });

    this.logger.log(`Draft transition completed: ${draftId} (${result.transitionMode}, A until ${result.trackAPlayUntilMs}ms, B from ${result.trackBStartFromMs}ms)`);
  }

  /**
   * Handle draft error from Python worker
   */
  private async handleDraftError(draftId: string, error: string): Promise<void> {
    await prisma.draft.update({
      where: { id: draftId },
      data: {
        status: 'FAILED',
        transitionStatus: 'ERROR',
        transitionError: error,
        errorMessage: error,
      },
    });

    // Notify via WebSocket
    this.websocketGateway.sendDraftError(draftId, error);

    this.logger.error(`Draft transition failed for ${draftId}: ${error}`);
  }

  /**
   * Handle draft track analysis completion
   * Called when a track analysis completes and the projectId is actually a draftId
   */
  private async handleDraftAnalysisComplete(draftId: string, trackId: string): Promise<void> {
    // Find the draft with its tracks
    const draft = await prisma.draft.findUnique({
      where: { id: draftId },
      include: {
        trackA: { include: { analysis: true } },
        trackB: { include: { analysis: true } },
      },
    });

    if (!draft) {
      this.logger.warn(`Draft not found for analysis completion: ${draftId}`);
      return;
    }

    // Determine which slot this track belongs to
    const slot = draft.trackAId === trackId ? 'A' : draft.trackBId === trackId ? 'B' : null;
    if (!slot) {
      this.logger.warn(`Track ${trackId} not found in draft ${draftId}`);
      return;
    }

    // Check if both tracks are now analyzed
    const bothAnalyzed = draft.trackA?.analysis && draft.trackB?.analysis;

    // Notify via WebSocket about the analysis completion
    this.websocketGateway.sendDraftAnalysisComplete(draftId, {
      draftId,
      slot,
      trackId,
      status: bothAnalyzed ? 'READY' : 'ANALYZING',
    });

    if (bothAnalyzed) {
      // Calculate compatibility scores
      const analysisA = draft.trackA!.analysis!;
      const analysisB = draft.trackB!.analysis!;

      // BPM Score (100 if same, decreases with difference)
      const bpmDiff = Math.abs(analysisA.bpm - analysisB.bpm) / analysisA.bpm * 100;
      const bpmScore = Math.max(0, Math.round(100 - bpmDiff * 5));

      // Harmonic Score (using Camelot wheel)
      const harmonicScore = this.calculateHarmonicScore(analysisA.camelot, analysisB.camelot);

      // Energy Score (100 if same, decreases with difference)
      const energyDiff = Math.abs(analysisA.energy - analysisB.energy);
      const energyScore = Math.round((1 - energyDiff) * 100);

      // Overall compatibility (weighted average)
      const compatibilityScore = Math.round(
        harmonicScore * 0.4 + bpmScore * 0.35 + energyScore * 0.25
      );

      // Update draft with scores and READY status
      await prisma.draft.update({
        where: { id: draftId },
        data: {
          status: 'READY',
          compatibilityScore,
          harmonicScore,
          bpmScore,
          energyScore,
          bpmDifference: bpmDiff,
        },
      });

      this.logger.log(`Draft ${draftId} ready with compatibility score: ${compatibilityScore}`);
    } else {
      // Update status to ANALYZING if not already
      if (draft.status === 'CREATED' || draft.status === 'UPLOADING') {
        await prisma.draft.update({
          where: { id: draftId },
          data: { status: 'ANALYZING' },
        });
      }
    }
  }

  /**
   * Calculate harmonic compatibility score using Camelot wheel
   */
  private calculateHarmonicScore(camelotA: string, camelotB: string): number {
    // Parse Camelot notation (e.g., "8A", "11B")
    const parseCode = (code: string) => {
      const match = code.match(/^(\d+)([AB])$/);
      if (!match) return null;
      return { number: parseInt(match[1]!, 10), letter: match[2]! };
    };

    const a = parseCode(camelotA);
    const b = parseCode(camelotB);

    if (!a || !b) return 50; // Default if can't parse

    // Same key = 100
    if (a.number === b.number && a.letter === b.letter) return 100;

    // Same number, different letter (relative major/minor) = 90
    if (a.number === b.number) return 90;

    // Adjacent numbers, same letter = 85
    const numDiff = Math.abs(a.number - b.number);
    const wrappedDiff = Math.min(numDiff, 12 - numDiff);

    if (wrappedDiff === 1 && a.letter === b.letter) return 85;

    // One step on wheel = 70
    if (wrappedDiff === 1) return 70;

    // Two steps = 50
    if (wrappedDiff === 2) return 50;

    // More than 2 steps = decreasing score
    return Math.max(0, 50 - (wrappedDiff - 2) * 15);
  }

  /**
   * Handle chat reorder result from Python worker
   */
  private async handleChatReorderResult(
    projectId: string,
    result: ChatReorderResult
  ): Promise<void> {
    // Process the result through ChatService (updates conversation history and applies new order if any)
    await this.chatService.handleChatResult(projectId, result);

    // Get updated project data if a new order was applied
    let projectData = null;
    if (result.new_order && result.new_order.length > 0) {
      const project = await prisma.project.findUnique({
        where: { id: projectId },
        include: {
          transitions: {
            orderBy: { position: 'asc' },
          },
        },
      });
      projectData = project ? {
        orderedTracks: project.orderedTracks,
        transitions: project.transitions,
        averageMixScore: project.averageMixScore,
      } : null;
    }

    // Notify via WebSocket
    this.websocketGateway.sendChatResponse(projectId, {
      projectId,
      response: result.response,
      newOrder: result.new_order,
      reasoning: result.reasoning,
      changesMade: result.changes_made || [],
      projectData,
    });

    this.logger.log(`Chat reorder completed for project: ${projectId}, hasNewOrder: ${!!result.new_order}`);
  }
}
