import {
  Controller,
  Get,
  Post,
  Patch,
  Delete,
  Param,
  Body,
  UseGuards,
  StreamableFile,
  Res,
  HttpCode,
  HttpStatus,
} from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiBearerAuth } from '@nestjs/swagger';
import { Response } from 'express';
import type { User } from '@autodj/database';
import { prisma } from '@autodj/database';
import type { TransitionAudioJobPayload } from '@autodj/shared-types';
import * as fs from 'fs';
import * as path from 'path';

import { ProjectsService } from './projects.service';
import { CreateProjectDto } from './dto/create-project.dto';
import { UpdateProjectDto } from './dto/update-project.dto';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard';
import { Public } from '../common/decorators/public.decorator';
import { CurrentUser } from '../common/decorators/current-user.decorator';
import { QueueService } from '../queue/queue.service';
import { OrderingService } from '../ordering/ordering.service';
import { WebsocketGateway } from '../websocket/websocket.gateway';
import { TransitionsProducer } from '../queue/producers/transitions.producer';

/**
 * Controller for project management endpoints
 */
@ApiTags('projects')
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller('projects')
export class ProjectsController {
  constructor(
    private readonly projectsService: ProjectsService,
    private readonly queueService: QueueService,
    private readonly orderingService: OrderingService,
    private readonly websocketGateway: WebsocketGateway,
    private readonly transitionsProducer: TransitionsProducer,
  ) {}

  /**
   * Get all projects for current user
   */
  @Get()
  @ApiOperation({ summary: 'List all projects' })
  @ApiResponse({ status: 200, description: 'Projects retrieved successfully' })
  async findAll(@CurrentUser() user: User) {
    return this.projectsService.findAllByUser(user.id);
  }

  /**
   * Create a new project
   */
  @Post()
  @ApiOperation({ summary: 'Create a new project' })
  @ApiResponse({ status: 201, description: 'Project created successfully' })
  async create(@CurrentUser() user: User, @Body() dto: CreateProjectDto) {
    return this.projectsService.create(user.id, dto);
  }

  /**
   * Get a single project by ID
   */
  @Get(':id')
  @ApiOperation({ summary: 'Get a project by ID' })
  @ApiResponse({ status: 200, description: 'Project retrieved successfully' })
  @ApiResponse({ status: 404, description: 'Project not found' })
  async findOne(@CurrentUser() user: User, @Param('id') id: string) {
    return this.projectsService.findByIdAndUser(id, user.id);
  }

  /**
   * Update a project
   */
  @Patch(':id')
  @ApiOperation({ summary: 'Update a project' })
  @ApiResponse({ status: 200, description: 'Project updated successfully' })
  @ApiResponse({ status: 404, description: 'Project not found' })
  async update(
    @CurrentUser() user: User,
    @Param('id') id: string,
    @Body() dto: UpdateProjectDto
  ) {
    return this.projectsService.update(id, user.id, dto);
  }

  /**
   * Delete a project
   */
  @Delete(':id')
  @ApiOperation({ summary: 'Delete a project' })
  @ApiResponse({ status: 200, description: 'Project deleted successfully' })
  @ApiResponse({ status: 404, description: 'Project not found' })
  async remove(@CurrentUser() user: User, @Param('id') id: string) {
    await this.projectsService.delete(id, user.id);
    return { message: 'Project deleted successfully' };
  }

  /**
   * Calculate optimal track order for a project
   * Can be triggered manually to re-calculate after adding/removing tracks
   */
  @Post(':id/mix/order')
  @HttpCode(HttpStatus.ACCEPTED)
  @ApiOperation({ summary: 'Calculate optimal track order' })
  @ApiResponse({ status: 202, description: 'Ordering calculation started' })
  @ApiResponse({ status: 400, description: 'Not enough tracks for ordering' })
  async calculateOrder(@CurrentUser() user: User, @Param('id') id: string) {
    const project = await this.projectsService.findByIdAndUser(id, user.id);

    // Validate project has enough analyzed tracks
    const analyzedTracks = project.tracks.filter((t) => t.analysis);
    if (analyzedTracks.length < 2) {
      return { error: 'Project must have at least 2 analyzed tracks' };
    }

    // Calculate optimal order
    const result = await this.orderingService.calculateOptimalOrder(id);

    // Emit WebSocket event
    this.websocketGateway.sendMixOrdered(id, {
      projectId: id,
      orderedTrackIds: result.orderedTrackIds,
      transitions: result.transitions,
      averageScore: result.averageScore,
      processingTimeMs: result.processingTimeMs,
    });

    return {
      message: 'Track order calculated',
      projectId: id,
      orderedTrackIds: result.orderedTrackIds,
      averageScore: result.averageScore,
      processingTimeMs: result.processingTimeMs,
      excludedTrackIds: result.excludedTrackIds,
    };
  }

  /**
   * Generate transition audio files for all transitions in a project
   * This creates smooth beat-matched transitions using stem separation
   */
  @Post(':id/transitions/generate')
  @HttpCode(HttpStatus.ACCEPTED)
  @ApiOperation({ summary: 'Generate transition audio files' })
  @ApiResponse({ status: 202, description: 'Transition generation started' })
  @ApiResponse({ status: 400, description: 'Project not ready for transition generation' })
  async generateTransitions(@CurrentUser() user: User, @Param('id') id: string) {
    const project = await this.projectsService.findByIdAndUser(id, user.id);

    // Validate project has ordered tracks
    if (!project.orderedTracks || project.orderedTracks.length < 2) {
      return { error: 'Project must have ordered tracks before generating transitions' };
    }

    // Get transitions with track data
    const transitions = await prisma.transition.findMany({
      where: { projectId: id },
      orderBy: { position: 'asc' },
    });

    if (transitions.length === 0) {
      return { error: 'No transitions found. Please calculate track order first.' };
    }

    // Build track lookup map
    const trackMap = new Map(project.tracks.map(t => [t.id, t]));

    // Prepare job payloads
    const jobPayloads: TransitionAudioJobPayload[] = [];

    for (const transition of transitions) {
      const fromTrack = trackMap.get(transition.fromTrackId);
      const toTrack = trackMap.get(transition.toTrackId);

      if (!fromTrack?.analysis || !toTrack?.analysis) {
        continue; // Skip transitions without full analysis
      }

      const fromBeats = (fromTrack.analysis.beats as number[]) || [];
      const toBeats = (toTrack.analysis.beats as number[]) || [];

      const payload: TransitionAudioJobPayload = {
        projectId: id,
        transitionId: transition.id,
        fromTrackId: transition.fromTrackId,
        toTrackId: transition.toTrackId,
        fromTrackPath: fromTrack.filePath,
        toTrackPath: toTrack.filePath,
        fromTrackBpm: fromTrack.analysis.bpm,
        toTrackBpm: toTrack.analysis.bpm,
        fromTrackBeats: fromBeats,
        toTrackBeats: toBeats,
        fromTrackOutroStart: fromTrack.analysis.outroStart || (fromTrack.duration ? fromTrack.duration - 30 : 0),
        toTrackIntroEnd: toTrack.analysis.introEnd || 30,
      };

      jobPayloads.push(payload);

      // Update transition status to PROCESSING
      await prisma.transition.update({
        where: { id: transition.id },
        data: { audioStatus: 'PROCESSING' },
      });
    }

    if (jobPayloads.length === 0) {
      return { error: 'No valid transitions to generate' };
    }

    // Update project status
    await prisma.project.update({
      where: { id },
      data: { status: 'MIXING' },
    });

    // Queue all transition jobs
    await this.transitionsProducer.addBulkJobs(jobPayloads);

    // Send initial progress
    this.websocketGateway.sendProgress(id, {
      projectId: id,
      stage: 'mixing',
      progress: 0,
      currentStep: `Generating ${jobPayloads.length} transitions...`,
    });

    return {
      message: 'Transition generation started',
      projectId: id,
      transitionCount: jobPayloads.length,
    };
  }

  /**
   * Start mix generation for a project
   * This calculates segments and generates transition audio files
   */
  @Post(':id/generate')
  @HttpCode(HttpStatus.ACCEPTED)
  @ApiOperation({ summary: 'Start mix generation' })
  @ApiResponse({ status: 202, description: 'Mix generation started' })
  @ApiResponse({ status: 400, description: 'Project not ready for mixing' })
  async generateMix(@CurrentUser() user: User, @Param('id') id: string) {
    const project = await this.projectsService.findByIdAndUser(id, user.id);

    // Validate project has enough tracks
    if (project.tracks.length < 2) {
      return { error: 'Project must have at least 2 tracks' };
    }

    // Check all tracks are analyzed
    const unanalyzedTracks = project.tracks.filter((t) => !t.analysis);
    if (unanalyzedTracks.length > 0) {
      return { error: 'All tracks must be analyzed before generating mix' };
    }

    // Update project status to MIXING
    await prisma.project.update({
      where: { id },
      data: { status: 'MIXING' },
    });

    // Send initial progress via WebSocket
    this.websocketGateway.sendProgress(id, {
      projectId: id,
      stage: 'mixing',
      progress: 0,
      currentStep: 'Calculating mix segments...',
    });

    // Queue the mix job
    await this.queueService.queueMixJob(project);

    return {
      message: 'Mix generation started',
      projectId: id,
      trackCount: project.tracks.length,
    };
  }

  /**
   * Download the generated mix
   */
  @Get(':id/download')
  @ApiOperation({ summary: 'Download the generated mix' })
  @ApiResponse({ status: 200, description: 'File download started' })
  @ApiResponse({ status: 404, description: 'Mix file not found' })
  async download(
    @CurrentUser() user: User,
    @Param('id') id: string,
    @Res({ passthrough: true }) res: Response
  ) {
    const project = await this.projectsService.findByIdAndUser(id, user.id);

    if (!project.outputFile) {
      return { error: 'Mix file not ready' };
    }

    const filePath = project.outputFile;

    if (!fs.existsSync(filePath)) {
      return { error: 'Mix file not found on disk' };
    }

    // Determine content type based on file extension
    const isWav = filePath.endsWith('.wav');
    const contentType = isWav ? 'audio/wav' : 'audio/mpeg';
    const extension = isWav ? 'wav' : 'mp3';
    const fileName = `${project.name.replace(/[^a-zA-Z0-9]/g, '_')}_mix.${extension}`;

    res.set({
      'Content-Type': contentType,
      'Content-Disposition': `attachment; filename="${fileName}"`,
    });

    const file = fs.createReadStream(filePath);
    return new StreamableFile(file);
  }

  /**
   * Stream the final mix audio (public endpoint for audio element)
   */
  @Public()
  @Get(':id/stream')
  @ApiOperation({ summary: 'Stream the final mix audio' })
  @ApiResponse({ status: 200, description: 'Audio stream' })
  @ApiResponse({ status: 404, description: 'Mix file not found' })
  async streamMix(
    @Param('id') id: string,
    @Res() res: Response
  ): Promise<void> {
    const project = await prisma.project.findUnique({
      where: { id },
    });

    if (!project) {
      res.status(404).json({ error: 'Project not found' });
      return;
    }

    if (!project.outputFile) {
      res.status(404).json({ error: 'Mix file not ready' });
      return;
    }

    const filePath = project.outputFile;

    if (!fs.existsSync(filePath)) {
      res.status(404).json({ error: 'Mix file not found on disk' });
      return;
    }

    const stat = fs.statSync(filePath);
    const isWav = filePath.endsWith('.wav');
    const contentType = isWav ? 'audio/wav' : 'audio/mpeg';

    res.set({
      'Content-Type': contentType,
      'Content-Length': stat.size,
      'Accept-Ranges': 'bytes',
      'Cache-Control': 'public, max-age=31536000',
    });

    const file = fs.createReadStream(filePath);
    file.pipe(res);
  }

  /**
   * Stream transition audio file (public for audio element access)
   */
  @Public()
  @Get(':id/transitions/:transitionId/audio')
  @ApiOperation({ summary: 'Stream transition audio file' })
  @ApiResponse({ status: 200, description: 'Audio stream' })
  @ApiResponse({ status: 404, description: 'Transition not found or audio not ready' })
  async streamTransitionAudio(
    @Param('id') id: string,
    @Param('transitionId') transitionId: string,
    @Res() res: Response
  ): Promise<void> {
    const transition = await prisma.transition.findUnique({
      where: { id: transitionId },
    });

    if (!transition || transition.projectId !== id) {
      res.status(404).json({ error: 'Transition not found' });
      return;
    }

    if (!transition.audioFilePath || transition.audioStatus !== 'COMPLETED') {
      res.status(404).json({ error: 'Transition audio not ready' });
      return;
    }

    // Get absolute path from storage
    const storagePath = path.resolve(process.env.STORAGE_PATH || './storage');
    const absolutePath = path.join(storagePath, transition.audioFilePath);

    if (!fs.existsSync(absolutePath)) {
      res.status(404).json({ error: 'Audio file not found' });
      return;
    }

    const stat = fs.statSync(absolutePath);

    res.set({
      'Content-Type': 'audio/wav',
      'Content-Length': stat.size,
      'Accept-Ranges': 'bytes',
      'Cache-Control': 'public, max-age=31536000',
    });

    const file = fs.createReadStream(absolutePath);
    file.pipe(res);
  }

  /**
   * Get mix segments for a project (for the player)
   */
  @Get(':id/mix/segments')
  @ApiOperation({ summary: 'Get mix segments for playback' })
  @ApiResponse({ status: 200, description: 'Mix segments retrieved successfully' })
  @ApiResponse({ status: 404, description: 'Project not found' })
  async getMixSegments(@CurrentUser() user: User, @Param('id') id: string) {
    // Verify user owns the project
    const project = await this.projectsService.findByIdAndUser(id, user.id);

    // Get mix segments ordered by position
    const segments = await prisma.mixSegment.findMany({
      where: { projectId: id },
      orderBy: { position: 'asc' },
    });

    // Build track lookup map for SOLO segments
    const trackMap = new Map(project.tracks.map(t => [t.id, t]));

    // Enhance segments with track info for SOLO segments
    const enhancedSegments = segments.map(segment => {
      if (segment.type === 'SOLO' && segment.trackId) {
        const track = trackMap.get(segment.trackId);
        return {
          ...segment,
          track: track ? {
            id: track.id,
            originalName: track.originalName,
            filePath: track.filePath,
            mimeType: track.mimeType,
          } : null,
        };
      }
      return segment;
    });

    return {
      projectId: id,
      status: project.status,
      segments: enhancedSegments,
      totalDurationMs: segments.reduce((sum, s) => sum + s.durationMs, 0),
    };
  }

  /**
   * Stream mix segment audio file
   */
  @Get(':id/mix/segments/:segmentId/audio')
  @ApiOperation({ summary: 'Stream mix segment audio' })
  @ApiResponse({ status: 200, description: 'Audio stream' })
  @ApiResponse({ status: 404, description: 'Segment not found or audio not ready' })
  async streamSegmentAudio(
    @CurrentUser() user: User,
    @Param('id') id: string,
    @Param('segmentId') segmentId: string,
    @Res() res: Response
  ): Promise<void> {
    // Verify user owns the project
    const project = await this.projectsService.findByIdAndUser(id, user.id);

    const segment = await prisma.mixSegment.findUnique({
      where: { id: segmentId },
    });

    if (!segment || segment.projectId !== id) {
      res.status(404).json({ error: 'Segment not found' });
      return;
    }

    // For SOLO segments, redirect to the track audio with time range
    if (segment.type === 'SOLO') {
      if (!segment.trackId) {
        res.status(404).json({ error: 'Track not found for segment' });
        return;
      }

      const track = project.tracks.find(t => t.id === segment.trackId);
      if (!track) {
        res.status(404).json({ error: 'Track not found' });
        return;
      }

      // Stream the full track file - the player will handle start/end times
      const absolutePath = track.filePath;

      if (!fs.existsSync(absolutePath)) {
        res.status(404).json({ error: 'Audio file not found' });
        return;
      }

      const stat = fs.statSync(absolutePath);

      res.set({
        'Content-Type': track.mimeType,
        'Content-Length': stat.size,
        'Accept-Ranges': 'bytes',
        'Cache-Control': 'public, max-age=31536000',
        'X-Segment-Start-Ms': segment.startMs.toString(),
        'X-Segment-End-Ms': segment.endMs.toString(),
      });

      const file = fs.createReadStream(absolutePath);
      file.pipe(res);
      return;
    }

    // For TRANSITION segments, stream the generated audio file
    if (!segment.audioFilePath || segment.audioStatus !== 'COMPLETED') {
      res.status(404).json({ error: 'Segment audio not ready' });
      return;
    }

    const storagePath = path.resolve(process.env.STORAGE_PATH || './storage');
    const absolutePath = path.join(storagePath, segment.audioFilePath);

    if (!fs.existsSync(absolutePath)) {
      res.status(404).json({ error: 'Audio file not found' });
      return;
    }

    const stat = fs.statSync(absolutePath);

    res.set({
      'Content-Type': 'audio/wav',
      'Content-Length': stat.size,
      'Accept-Ranges': 'bytes',
      'Cache-Control': 'public, max-age=31536000',
    });

    const file = fs.createReadStream(absolutePath);
    file.pipe(res);
  }
}
