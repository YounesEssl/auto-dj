import {
  Controller,
  Get,
  Post,
  Delete,
  Param,
  UseGuards,
  UseInterceptors,
  UploadedFiles,
  BadRequestException,
  Inject,
  forwardRef,
  Res,
  Logger,
} from '@nestjs/common';
import { Response } from 'express';
import { createReadStream, statSync, existsSync } from 'fs';
import { FilesInterceptor } from '@nestjs/platform-express';
import {
  ApiTags,
  ApiOperation,
  ApiResponse,
  ApiBearerAuth,
  ApiConsumes,
  ApiBody,
} from '@nestjs/swagger';
import type { User } from '@autodj/database';
import { v4 as uuidv4 } from 'uuid';

import { TracksService } from './tracks.service';
import { MetadataService } from './metadata.service';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard';
import { CurrentUser } from '../common/decorators/current-user.decorator';
import { Public } from '../common/decorators/public.decorator';
import { StorageService } from '../storage/storage.service';
import { QueueService } from '../queue/queue.service';
import { ProjectsService } from '../projects/projects.service';

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

/**
 * Controller for track upload and management
 */
@ApiTags('tracks')
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller('projects/:projectId/tracks')
export class TracksController {
  private readonly logger = new Logger(TracksController.name);

  constructor(
    private readonly tracksService: TracksService,
    private readonly metadataService: MetadataService,
    private readonly storageService: StorageService,
    private readonly queueService: QueueService,
    @Inject(forwardRef(() => ProjectsService))
    private readonly projectsService: ProjectsService
  ) {}

  /**
   * Get all tracks for a project
   */
  @Get()
  @ApiOperation({ summary: 'List all tracks in a project' })
  @ApiResponse({ status: 200, description: 'Tracks retrieved successfully' })
  async findAll(@CurrentUser() user: User, @Param('projectId') projectId: string) {
    // Verify user owns the project
    await this.projectsService.findByIdAndUser(projectId, user.id);
    return this.tracksService.findByProjectId(projectId);
  }

  /**
   * Upload tracks to a project
   */
  @Post()
  @ApiOperation({ summary: 'Upload tracks to a project' })
  @ApiConsumes('multipart/form-data')
  @ApiBody({
    schema: {
      type: 'object',
      properties: {
        files: {
          type: 'array',
          items: {
            type: 'string',
            format: 'binary',
          },
        },
      },
    },
  })
  @ApiResponse({ status: 201, description: 'Tracks uploaded successfully' })
  @ApiResponse({ status: 400, description: 'Invalid file type or size' })
  @UseInterceptors(FilesInterceptor('files', 50))
  async upload(
    @CurrentUser() user: User,
    @Param('projectId') projectId: string,
    @UploadedFiles() files: Express.Multer.File[]
  ) {
    this.logger.log(`========== UPLOAD ENDPOINT CALLED ==========`);
    this.logger.log(`Project ID: ${projectId}, User: ${user?.id}, Files count: ${files?.length || 0}`);

    // Verify user owns the project
    await this.projectsService.findByIdAndUser(projectId, user.id);

    if (!files || files.length === 0) {
      this.logger.warn('No files in request');
      throw new BadRequestException('No files uploaded');
    }

    this.logger.log(`Processing ${files.length} file(s)...`);

    const uploadedTracks = [];

    for (const file of files) {
      // Validate file type
      if (!ALLOWED_MIME_TYPES.includes(file.mimetype)) {
        throw new BadRequestException(
          `Invalid file type: ${file.originalname}. Only MP3 and WAV files are allowed.`
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
        `projects/${projectId}/${filename}`
      );

      // Extract metadata from the saved file (need absolute path for reading)
      const absoluteFilePath = this.storageService.getAbsolutePath(filePath.replace(/^storage\//, ''));
      const metadata = await this.metadataService.extractMetadata(absoluteFilePath, projectId);

      // Create track record with metadata
      const track = await this.tracksService.create({
        projectId,
        filename,
        originalName: file.originalname,
        filePath,
        fileSize: file.size,
        mimeType: file.mimetype,
        duration: metadata.duration,
        metaTitle: metadata.title,
        metaArtist: metadata.artist,
        metaAlbum: metadata.album,
        metaGenre: metadata.genre,
        metaYear: metadata.year,
        coverPath: metadata.coverPath,
      });

      uploadedTracks.push(track);

      // Queue analysis job
      this.logger.log(`Queueing analysis job for track ${track.id}, filePath: ${filePath}`);
      try {
        await this.queueService.queueAnalyzeJob({
          projectId,
          trackId: track.id,
          filePath,
        });
        this.logger.log(`Successfully queued analysis job for track ${track.id}`);
      } catch (error) {
        this.logger.error(`Failed to queue analysis job for track ${track.id}:`, error);
        throw error;
      }
    }

    // Update project status to analyzing
    await this.projectsService.updateStatus(projectId, 'ANALYZING');

    return {
      message: `${uploadedTracks.length} track(s) uploaded and queued for analysis`,
      tracks: uploadedTracks,
    };
  }

  /**
   * Get a single track by ID
   */
  @Get(':trackId')
  @ApiOperation({ summary: 'Get a track by ID' })
  @ApiResponse({ status: 200, description: 'Track retrieved successfully' })
  @ApiResponse({ status: 404, description: 'Track not found' })
  async findOne(
    @CurrentUser() user: User,
    @Param('projectId') projectId: string,
    @Param('trackId') trackId: string
  ) {
    // Verify user owns the project
    await this.projectsService.findByIdAndUser(projectId, user.id);
    return this.tracksService.findById(trackId);
  }

  /**
   * Get track analysis
   */
  @Get(':trackId/analysis')
  @ApiOperation({ summary: 'Get track analysis results' })
  @ApiResponse({ status: 200, description: 'Analysis retrieved successfully' })
  @ApiResponse({ status: 404, description: 'Analysis not found' })
  async getAnalysis(
    @CurrentUser() user: User,
    @Param('projectId') projectId: string,
    @Param('trackId') trackId: string
  ) {
    // Verify user owns the project
    await this.projectsService.findByIdAndUser(projectId, user.id);
    return this.tracksService.getAnalysis(trackId);
  }

  /**
   * Stream track audio file (public for audio element access)
   */
  @Public()
  @Get(':trackId/audio')
  @ApiOperation({ summary: 'Stream track audio file' })
  @ApiResponse({ status: 200, description: 'Audio stream' })
  @ApiResponse({ status: 404, description: 'Track not found' })
  async streamAudio(
    @Param('projectId') projectId: string,
    @Param('trackId') trackId: string,
    @Res() res: Response
  ): Promise<void> {
    const track = await this.tracksService.findById(trackId);

    // Verify track belongs to project
    if (track.projectId !== projectId) {
      res.status(404).json({ error: 'Track not found' });
      return;
    }

    // Convert relative path to absolute
    const absolutePath = this.storageService.getAbsolutePath(track.filePath.replace(/^storage\//, ''));

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
   * Delete a track
   */
  @Delete(':trackId')
  @ApiOperation({ summary: 'Delete a track' })
  @ApiResponse({ status: 200, description: 'Track deleted successfully' })
  @ApiResponse({ status: 404, description: 'Track not found' })
  async remove(
    @CurrentUser() user: User,
    @Param('projectId') projectId: string,
    @Param('trackId') trackId: string
  ) {
    // Verify user owns the project
    await this.projectsService.findByIdAndUser(projectId, user.id);

    const track = await this.tracksService.findById(trackId);

    // Delete file from storage
    await this.storageService.deleteFile(track.filePath);

    // Delete track record
    await this.tracksService.delete(trackId);

    return { message: 'Track deleted successfully' };
  }

  /**
   * Stream track cover image (public endpoint)
   */
  @Public()
  @Get(':trackId/cover')
  @ApiOperation({ summary: 'Get track cover art' })
  @ApiResponse({ status: 200, description: 'Cover image' })
  @ApiResponse({ status: 404, description: 'Cover not found' })
  async getCover(
    @Param('projectId') projectId: string,
    @Param('trackId') trackId: string,
    @Res() res: Response
  ): Promise<void> {
    const track = await this.tracksService.findById(trackId);

    // Verify track belongs to the project
    if (track.projectId !== projectId) {
      res.status(404).json({ error: 'Track not found' });
      return;
    }

    if (!track.coverPath) {
      res.status(404).json({ error: 'No cover art available' });
      return;
    }

    const storagePath = process.env.STORAGE_PATH || '/app/storage';
    const absolutePath = `${storagePath}/${track.coverPath}`;

    if (!existsSync(absolutePath)) {
      res.status(404).json({ error: 'Cover file not found' });
      return;
    }

    const stat = statSync(absolutePath);
    const ext = track.coverPath.split('.').pop()?.toLowerCase();
    const mimeTypes: Record<string, string> = {
      jpg: 'image/jpeg',
      jpeg: 'image/jpeg',
      png: 'image/png',
      gif: 'image/gif',
      webp: 'image/webp',
    };

    res.set({
      'Content-Type': mimeTypes[ext || 'jpg'] || 'image/jpeg',
      'Content-Length': stat.size,
      'Cache-Control': 'public, max-age=31536000',
    });

    const file = createReadStream(absolutePath);
    file.pipe(res);
  }
}
