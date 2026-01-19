import {
  Controller,
  Get,
  Post,
  Delete,
  Param,
  Body,
  UseGuards,
  UseInterceptors,
  UploadedFile,
  BadRequestException,
  Res,
  Logger,
} from '@nestjs/common';
import { Response } from 'express';
import { createReadStream, statSync, existsSync } from 'fs';
import { FileInterceptor } from '@nestjs/platform-express';
import {
  ApiTags,
  ApiOperation,
  ApiResponse,
  ApiBearerAuth,
  ApiConsumes,
  ApiBody,
  ApiParam,
} from '@nestjs/swagger';
import type { User } from '@autodj/database';
import { v4 as uuidv4 } from 'uuid';

import { DraftsService } from './drafts.service';
import { CreateDraftDto } from './dto/create-draft.dto';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard';
import { CurrentUser } from '../common/decorators/current-user.decorator';
import { StorageService } from '../storage/storage.service';
import { QueueService } from '../queue/queue.service';

const ALLOWED_MIME_TYPES = [
  'audio/mpeg',
  'audio/wav',
  'audio/x-wav',
  'audio/mp3',
  'audio/mp4',
  'audio/x-m4a',
  'audio/aac',
  'audio/flac',
  'audio/ogg',
];
const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB

type SlotType = 'A' | 'B';

/**
 * Controller for draft management (2-track transitions)
 */
@ApiTags('drafts')
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller('drafts')
export class DraftsController {
  private readonly logger = new Logger(DraftsController.name);

  constructor(
    private readonly draftsService: DraftsService,
    private readonly storageService: StorageService,
    private readonly queueService: QueueService
  ) {}

  /**
   * Get all drafts for current user
   */
  @Get()
  @ApiOperation({ summary: 'List all drafts for the current user' })
  @ApiResponse({ status: 200, description: 'Drafts retrieved successfully' })
  async findAll(@CurrentUser() user: User) {
    return this.draftsService.findAllByUser(user.id);
  }

  /**
   * Create a new draft
   */
  @Post()
  @ApiOperation({ summary: 'Create a new draft' })
  @ApiResponse({ status: 201, description: 'Draft created successfully' })
  async create(@CurrentUser() user: User, @Body() dto: CreateDraftDto) {
    return this.draftsService.create(user.id, dto);
  }

  /**
   * Get a draft by ID
   */
  @Get(':id')
  @ApiOperation({ summary: 'Get a draft by ID' })
  @ApiResponse({ status: 200, description: 'Draft retrieved successfully' })
  @ApiResponse({ status: 404, description: 'Draft not found' })
  async findOne(@CurrentUser() user: User, @Param('id') id: string) {
    return this.draftsService.findByIdAndUser(id, user.id);
  }

  /**
   * Delete a draft
   */
  @Delete(':id')
  @ApiOperation({ summary: 'Delete a draft' })
  @ApiResponse({ status: 200, description: 'Draft deleted successfully' })
  @ApiResponse({ status: 404, description: 'Draft not found' })
  async remove(@CurrentUser() user: User, @Param('id') id: string) {
    await this.draftsService.delete(id, user.id);
    return { message: 'Draft deleted successfully' };
  }

  /**
   * Upload a track to slot A or B
   */
  @Post(':id/tracks/:slot')
  @ApiOperation({ summary: 'Upload a track to slot A or B' })
  @ApiParam({ name: 'slot', enum: ['A', 'B'], description: 'Track slot (A or B)' })
  @ApiConsumes('multipart/form-data')
  @ApiBody({
    schema: {
      type: 'object',
      properties: {
        file: { type: 'string', format: 'binary' },
      },
    },
  })
  @ApiResponse({ status: 201, description: 'Track uploaded successfully' })
  @ApiResponse({ status: 400, description: 'Invalid file or slot' })
  @UseInterceptors(FileInterceptor('file'))
  async uploadTrack(
    @CurrentUser() user: User,
    @Param('id') id: string,
    @Param('slot') slot: string,
    @UploadedFile() file: Express.Multer.File
  ) {
    // Validate slot
    const normalizedSlot = slot.toUpperCase() as SlotType;
    if (normalizedSlot !== 'A' && normalizedSlot !== 'B') {
      throw new BadRequestException('Slot must be A or B');
    }

    // Validate file exists
    if (!file) {
      throw new BadRequestException('No file uploaded');
    }

    // Validate file type
    if (!ALLOWED_MIME_TYPES.includes(file.mimetype)) {
      throw new BadRequestException(
        `Invalid file type: ${file.originalname}. Only audio files are allowed.`
      );
    }

    // Validate file size
    if (file.size > MAX_FILE_SIZE) {
      throw new BadRequestException(
        `File too large: ${file.originalname}. Maximum size is 100MB.`
      );
    }

    // Generate unique filename
    const extension = file.originalname.split('.').pop();
    const filename = `${uuidv4()}.${extension}`;

    // Save file to storage
    const filePath = await this.storageService.saveFile(
      file.buffer,
      `drafts/${id}/${filename}`
    );

    // Create track and link to draft
    const track = await this.draftsService.createTrackForSlot(id, user.id, normalizedSlot, {
      filename,
      originalName: file.originalname,
      filePath,
      fileSize: file.size,
      mimeType: file.mimetype,
    });

    // Queue analysis job (reuse existing analyze queue)
    // Note: We pass draftId instead of projectId, worker needs to handle this
    await this.queueService.queueAnalyzeJob({
      projectId: id, // Using draftId as projectId for the queue
      trackId: track.id,
      filePath,
    });

    this.logger.log(`Track uploaded to draft ${id} slot ${normalizedSlot}: ${track.id}`);

    return {
      message: `Track uploaded to slot ${normalizedSlot} and queued for analysis`,
      track,
    };
  }

  /**
   * Remove a track from slot A or B
   */
  @Delete(':id/tracks/:slot')
  @ApiOperation({ summary: 'Remove a track from slot A or B' })
  @ApiParam({ name: 'slot', enum: ['A', 'B'], description: 'Track slot (A or B)' })
  @ApiResponse({ status: 200, description: 'Track removed successfully' })
  @ApiResponse({ status: 400, description: 'Invalid slot or no track in slot' })
  async removeTrack(
    @CurrentUser() user: User,
    @Param('id') id: string,
    @Param('slot') slot: string
  ) {
    const normalizedSlot = slot.toUpperCase() as SlotType;
    if (normalizedSlot !== 'A' && normalizedSlot !== 'B') {
      throw new BadRequestException('Slot must be A or B');
    }

    await this.draftsService.removeTrackFromSlot(id, user.id, normalizedSlot);

    return { message: `Track removed from slot ${normalizedSlot}` };
  }

  /**
   * Swap tracks A and B
   */
  @Post(':id/swap')
  @ApiOperation({ summary: 'Swap tracks A and B' })
  @ApiResponse({ status: 200, description: 'Tracks swapped successfully' })
  async swapTracks(@CurrentUser() user: User, @Param('id') id: string) {
    const draft = await this.draftsService.swapTracks(id, user.id);
    return { message: 'Tracks swapped successfully', draft };
  }

  /**
   * Generate transition audio
   */
  @Post(':id/generate')
  @ApiOperation({ summary: 'Generate transition audio between tracks A and B' })
  @ApiResponse({ status: 202, description: 'Transition generation started' })
  @ApiResponse({ status: 400, description: 'Draft not ready for generation' })
  async generateTransition(@CurrentUser() user: User, @Param('id') id: string) {
    // Prepare job payload (validates draft state)
    const payload = await this.draftsService.prepareTransitionJobPayload(id, user.id);

    // Update status to GENERATING
    await this.draftsService.updateStatus(id, 'GENERATING');
    await this.draftsService.updateTransitionResult(id, { status: 'PROCESSING' });

    // Queue the draft transition job
    await this.queueService.queueDraftTransitionJob(payload);

    this.logger.log(`Transition generation queued for draft ${id}`);

    return {
      message: 'Transition generation started',
      draftId: id,
      payload,
    };
  }

  /**
   * Stream track audio from slot A or B
   */
  @Get(':id/tracks/:slot/audio')
  @ApiOperation({ summary: 'Stream track audio from slot A or B' })
  @ApiParam({ name: 'slot', enum: ['A', 'B'], description: 'Track slot (A or B)' })
  @ApiResponse({ status: 200, description: 'Audio stream' })
  @ApiResponse({ status: 404, description: 'Track not found' })
  async streamTrackAudio(
    @CurrentUser() user: User,
    @Param('id') id: string,
    @Param('slot') slot: string,
    @Res() res: Response
  ): Promise<void> {
    const normalizedSlot = slot.toUpperCase() as SlotType;
    if (normalizedSlot !== 'A' && normalizedSlot !== 'B') {
      throw new BadRequestException('Slot must be A or B');
    }

    const draft = await this.draftsService.findByIdAndUser(id, user.id);

    const track = normalizedSlot === 'A' ? draft.trackA : draft.trackB;
    if (!track) {
      throw new BadRequestException(`No track in slot ${normalizedSlot}`);
    }

    const absolutePath = track.filePath;
    const stat = statSync(absolutePath);

    res.set({
      'Content-Type': track.mimeType,
      'Content-Length': stat.size,
      'Accept-Ranges': 'bytes',
      'Cache-Control': 'public, max-age=31536000',
    });

    const file = createReadStream(absolutePath);
    file.pipe(res);
  }

  /**
   * Stream transition audio
   */
  @Get(':id/transition/audio')
  @ApiOperation({ summary: 'Stream generated transition audio' })
  @ApiResponse({ status: 200, description: 'Audio stream' })
  @ApiResponse({ status: 404, description: 'Transition not found' })
  async streamTransitionAudio(
    @CurrentUser() user: User,
    @Param('id') id: string,
    @Res() res: Response
  ): Promise<void> {
    const draft = await this.draftsService.findByIdAndUser(id, user.id);

    if (draft.transitionStatus !== 'COMPLETED' || !draft.transitionFilePath) {
      throw new BadRequestException('Transition not ready');
    }

    const absolutePath = this.storageService.getAbsolutePath(draft.transitionFilePath);

    if (!existsSync(absolutePath)) {
      throw new BadRequestException('Transition file not found');
    }

    const stat = statSync(absolutePath);

    res.set({
      'Content-Type': 'audio/mpeg',
      'Content-Length': stat.size,
      'Accept-Ranges': 'bytes',
      'Cache-Control': 'public, max-age=3600', // 1 hour cache for transitions (regenerable)
      'ETag': `"${stat.size}-${stat.mtimeMs}"`,
    });

    const file = createReadStream(absolutePath);
    file.pipe(res);
  }

  /**
   * Get playback info for the player
   */
  @Get(':id/playback')
  @ApiOperation({ summary: 'Get playback info for the draft player' })
  @ApiResponse({ status: 200, description: 'Playback info retrieved' })
  async getPlaybackInfo(@CurrentUser() user: User, @Param('id') id: string) {
    const draft = await this.draftsService.findByIdAndUser(id, user.id);

    if (!draft.trackA || !draft.trackB) {
      throw new BadRequestException('Both tracks must be uploaded');
    }

    if (draft.transitionStatus !== 'COMPLETED') {
      throw new BadRequestException('Transition must be generated first');
    }

    const trackBDurationMs = (draft.trackB.duration || 0) * 1000;
    const transitionDurationMs = draft.transitionDurationMs || 0;

    // Use the cut points for seamless playback (to avoid audio duplication)
    // Fallback to old fields for backwards compatibility with existing drafts
    const trackAPlayUntilMs = draft.trackAPlayUntilMs ?? draft.trackAOutroMs ?? 0;
    const trackBStartFromMs = draft.trackBStartFromMs ?? draft.trackBIntroMs ?? 0;

    // Calculate segment timings
    // Track A solo: 0 -> trackAPlayUntilMs (play Track A until the transition takes over)
    // Transition: play the transition file (contains the overlap)
    // Track B solo: trackBStartFromMs -> end (play Track B from after the overlap)

    const trackASoloDuration = trackAPlayUntilMs;
    const trackBSoloDuration = trackBDurationMs - trackBStartFromMs;
    const totalDurationMs = trackASoloDuration + transitionDurationMs + trackBSoloDuration;

    return {
      draftId: id,
      totalDurationMs,
      segments: [
        {
          type: 'trackA',
          startMs: 0,
          endMs: trackASoloDuration,
          durationMs: trackASoloDuration,
          sourceStartMs: 0,
          sourceEndMs: trackAPlayUntilMs,  // Stop playing Track A here
        },
        {
          type: 'transition',
          startMs: trackASoloDuration,
          endMs: trackASoloDuration + transitionDurationMs,
          durationMs: transitionDurationMs,
          sourceStartMs: 0,
          sourceEndMs: transitionDurationMs,
        },
        {
          type: 'trackB',
          startMs: trackASoloDuration + transitionDurationMs,
          endMs: totalDurationMs,
          durationMs: trackBSoloDuration,
          sourceStartMs: trackBStartFromMs,  // Start playing Track B from here
          sourceEndMs: trackBDurationMs,
        },
      ],
      // Include both old and new fields for compatibility
      trackAOutroMs: draft.trackAOutroMs ?? 0,
      trackBIntroMs: draft.trackBIntroMs ?? 0,
      trackAPlayUntilMs,
      trackBStartFromMs,
      transitionDurationMs,
    };
  }
}
