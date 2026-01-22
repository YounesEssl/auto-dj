import { Injectable, Logger } from '@nestjs/common';
import type { AnalyzeJobPayload, MixJobPayload, MixTrackData, DraftTransitionJobPayload } from '@autodj/shared-types';

import { AnalyzeProducer } from './producers/analyze.producer';
import { MixProducer } from './producers/mix.producer';
import { DraftTransitionProducer } from './producers/draft-transition.producer';

interface ProjectWithTracks {
  id: string;
  tracks: Array<{
    id: string;
    filePath: string;
    duration: number | null;
    analysis?: {
      camelot: string;
      energy: number;
      bpm: number;
      beats?: unknown;
      introEnd?: number | null;
      outroStart?: number | null;
    } | null;
  }>;
  orderedTracks: string[];
}

/**
 * Service for managing job queues
 */
@Injectable()
export class QueueService {
  private readonly logger = new Logger(QueueService.name);

  constructor(
    private readonly analyzeProducer: AnalyzeProducer,
    private readonly mixProducer: MixProducer,
    private readonly draftTransitionProducer: DraftTransitionProducer
  ) {}

  /**
   * Queue a track for analysis
   */
  async queueAnalyzeJob(payload: AnalyzeJobPayload): Promise<void> {
    this.logger.log(`QueueService.queueAnalyzeJob called for track: ${payload.trackId}, file: ${payload.filePath}`);
    try {
      await this.analyzeProducer.addJob(payload);
      this.logger.log(`QueueService: Successfully queued analysis job for track: ${payload.trackId}`);
    } catch (error) {
      this.logger.error(`QueueService: Failed to queue analysis job:`, error);
      throw error;
    }
  }

  /**
   * Queue multiple tracks for analysis
   */
  async queueAnalyzeJobs(
    projectId: string,
    tracks: Array<{ id: string; filePath: string }>
  ): Promise<void> {
    for (const track of tracks) {
      await this.queueAnalyzeJob({
        projectId,
        trackId: track.id,
        filePath: track.filePath,
      });
    }
    this.logger.log(`Queued ${tracks.length} analysis jobs for project: ${projectId}`);
  }

  /**
   * Queue a mix generation job
   */
  async queueMixJob(project: ProjectWithTracks): Promise<void> {
    // Get ordered track IDs
    const orderedTrackIds =
      project.orderedTracks.length > 0
        ? project.orderedTracks
        : project.tracks.map((t) => t.id);

    // Build track lookup map
    const trackMap = new Map(project.tracks.map(t => [t.id, t]));

    // Build ordered tracks with full data
    const tracks: MixTrackData[] = [];
    for (const trackId of orderedTrackIds) {
      const track = trackMap.get(trackId);
      if (!track) continue;

      tracks.push({
        id: track.id,
        filePath: track.filePath,
        duration: track.duration,
        analysis: track.analysis ? {
          bpm: track.analysis.bpm,
          energy: track.analysis.energy,
          beats: Array.isArray(track.analysis.beats) ? track.analysis.beats as number[] : undefined,
          introEnd: track.analysis.introEnd,
          outroStart: track.analysis.outroStart,
        } : null,
      });
    }

    // Generate transition configs
    const transitions: MixJobPayload['transitions'] = [];
    for (let i = 0; i < tracks.length - 1; i++) {
      const fromTrack = tracks[i];
      const toTrack = tracks[i + 1];

      if (!fromTrack || !toTrack) continue;

      transitions.push({
        fromTrackId: fromTrack.id,
        toTrackId: toTrack.id,
        type: 'stems', // Use stem separation for professional mixing
        durationBars: 16, // Base duration, will be adjusted by energy
        useStemSeparation: true,
      });
    }

    const payload: MixJobPayload = {
      projectId: project.id,
      tracks,
      transitions,
    };

    await this.mixProducer.addJob(payload);
    this.logger.log(`Queued mix job for project: ${project.id} with ${tracks.length} tracks`);
  }

  /**
   * Queue a draft transition generation job
   */
  async queueDraftTransitionJob(payload: DraftTransitionJobPayload): Promise<void> {
    await this.draftTransitionProducer.addJob(payload);
    this.logger.log(`Queued draft transition job for draft: ${payload.draftId}`);
  }
}
