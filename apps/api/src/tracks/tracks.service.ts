import { Injectable, NotFoundException } from '@nestjs/common';
import { prisma, Prisma } from '@autodj/database';
import type { AnalyzeJobResult } from '@autodj/shared-types';

/**
 * Service for track data operations
 */
@Injectable()
export class TracksService {
  /**
   * Find a track by ID
   */
  async findById(id: string) {
    const track = await prisma.track.findUnique({
      where: { id },
      include: {
        analysis: true,
      },
    });

    if (!track) {
      throw new NotFoundException('Track not found');
    }

    return track;
  }

  /**
   * Find all tracks for a project
   */
  async findByProjectId(projectId: string) {
    return prisma.track.findMany({
      where: { projectId },
      include: {
        analysis: true,
      },
      orderBy: { createdAt: 'asc' },
    });
  }

  /**
   * Create a new track record
   */
  async create(data: {
    projectId: string;
    filename: string;
    originalName: string;
    filePath: string;
    fileSize: number;
    mimeType: string;
    duration?: number;
  }) {
    return prisma.track.create({
      data: {
        projectId: data.projectId,
        filename: data.filename,
        originalName: data.originalName,
        filePath: data.filePath,
        fileSize: data.fileSize,
        mimeType: data.mimeType,
        duration: data.duration,
      },
    });
  }

  /**
   * Update track duration after analysis
   */
  async updateDuration(id: string, duration: number) {
    return prisma.track.update({
      where: { id },
      data: { duration },
    });
  }

  /**
   * Save track analysis results
   */
  async saveAnalysis(trackId: string, result: AnalyzeJobResult) {
    // First update track duration if available
    if (result.outroEnd) {
      await prisma.track.update({
        where: { id: trackId },
        data: { duration: result.outroEnd },
      });
    }

    // Upsert analysis
    return prisma.trackAnalysis.upsert({
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
        structureJson: result.structureJson as Prisma.InputJsonValue | undefined,
      },
    });
  }

  /**
   * Delete a track
   */
  async delete(id: string) {
    return prisma.track.delete({
      where: { id },
    });
  }

  /**
   * Get track analysis
   */
  async getAnalysis(trackId: string) {
    return prisma.trackAnalysis.findUnique({
      where: { trackId },
    });
  }
}
