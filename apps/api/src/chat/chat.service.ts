import { Injectable, Logger, NotFoundException, BadRequestException } from '@nestjs/common';
import { prisma } from '@autodj/database';

import { ChatReorderProducer, ChatReorderJobPayload } from '../queue/producers/chat-reorder.producer';
import { OrderingService } from '../ordering/ordering.service';

/**
 * Chat message stored in conversation history
 */
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  newOrder?: string[] | null;
  changesMade?: string[];
}

/**
 * Response from chat endpoint
 */
export interface ChatResponse {
  jobId: string;
  message: string;
}

/**
 * Service for chat-based track reordering
 */
@Injectable()
export class ChatService {
  private readonly logger = new Logger(ChatService.name);

  // In-memory conversation storage (per project)
  // In production, this could be stored in Redis or database
  private conversations = new Map<string, ChatMessage[]>();

  constructor(
    private readonly chatReorderProducer: ChatReorderProducer,
    private readonly orderingService: OrderingService,
  ) {}

  /**
   * Send a chat message for a project
   */
  async sendMessage(
    projectId: string,
    userId: string,
    message: string,
  ): Promise<ChatResponse> {
    // Verify project exists and belongs to user
    const project = await prisma.project.findFirst({
      where: {
        id: projectId,
        userId,
      },
      include: {
        tracks: {
          include: {
            analysis: true,
          },
        },
      },
    });

    if (!project) {
      throw new NotFoundException('Project not found');
    }

    // Check if project has tracks
    if (project.tracks.length < 2) {
      throw new BadRequestException('Project must have at least 2 tracks to use chat reordering');
    }

    // Check if all tracks are analyzed
    const unanalyzedTracks = project.tracks.filter((t) => !t.analysis);
    if (unanalyzedTracks.length > 0) {
      throw new BadRequestException('All tracks must be analyzed before using chat reordering');
    }

    // Get or create conversation history
    let history = this.conversations.get(projectId) || [];

    // Add user message to history
    history.push({
      role: 'user',
      content: message,
      timestamp: new Date(),
    });

    // Limit history to last 10 messages to keep context manageable
    if (history.length > 10) {
      history = history.slice(-10);
    }

    this.conversations.set(projectId, history);

    // Prepare track data for the AI
    const tracks = project.tracks.map((track) => ({
      id: track.id,
      title: track.metaTitle || undefined,
      artist: track.metaArtist || undefined,
      original_name: track.originalName,
      bpm: track.analysis?.bpm,
      key: track.analysis?.key,
      camelot: track.analysis?.camelot,
      energy: track.analysis?.energy,
      duration: track.duration ?? undefined,
    }));

    // Get current order (or use track order from DB)
    const currentOrder = project.orderedTracks?.length > 0
      ? project.orderedTracks
      : project.tracks.map((t) => t.id);

    // Prepare job payload
    const payload: ChatReorderJobPayload = {
      projectId,
      message,
      tracks,
      currentOrder,
      conversationHistory: history.slice(0, -1).map((m) => ({
        role: m.role,
        content: m.content,
      })),
    };

    // Queue the job
    const jobId = await this.chatReorderProducer.addJob(payload);

    this.logger.log(`Chat reorder job queued: ${jobId} for project ${projectId}`);

    return {
      jobId,
      message: 'Processing your request...',
    };
  }

  /**
   * Handle chat result from worker (called by ResultConsumer)
   */
  async handleChatResult(
    projectId: string,
    result: {
      response: string;
      new_order?: string[] | null;
      reasoning?: string | null;
      changes_made?: string[];
    },
  ): Promise<void> {
    // Get conversation history
    const history = this.conversations.get(projectId) || [];

    // Add assistant response to history
    history.push({
      role: 'assistant',
      content: result.response,
      timestamp: new Date(),
      newOrder: result.new_order,
      changesMade: result.changes_made,
    });

    this.conversations.set(projectId, history);

    // If there's a new order, apply it to the project
    if (result.new_order && result.new_order.length > 0) {
      await this.applyNewOrder(projectId, result.new_order);
    }

    this.logger.log(`Chat result processed for project ${projectId}`);
  }

  /**
   * Apply a new track order to the project
   */
  private async applyNewOrder(projectId: string, newOrder: string[]): Promise<void> {
    // Get the project's actual track IDs
    const project = await prisma.project.findUnique({
      where: { id: projectId },
      include: { tracks: { select: { id: true } } },
    });

    if (!project) {
      this.logger.error(`Project ${projectId} not found when applying new order`);
      return;
    }

    const validTrackIds = new Set(project.tracks.map((t) => t.id));

    // Validate and fix the new order
    // 1. Filter out invalid track IDs
    const validatedOrder = newOrder.filter((id) => validTrackIds.has(id));

    // 2. Add any missing tracks at the end (in case AI forgot some)
    const orderedSet = new Set(validatedOrder);
    for (const trackId of validTrackIds) {
      if (!orderedSet.has(trackId)) {
        validatedOrder.push(trackId);
        this.logger.warn(`Track ${trackId} was missing from AI order, added at end`);
      }
    }

    // 3. Check if we have any valid tracks to order
    if (validatedOrder.length < 2) {
      this.logger.error(`Not enough valid tracks in new order for project ${projectId}`);
      return;
    }

    this.logger.log(`Validated order: ${validatedOrder.length} tracks (original: ${newOrder.length})`);

    // Recalculate transitions for the validated order
    const { averageScore } =
      await this.orderingService.recalculateTransitionsForOrder(projectId, validatedOrder);

    // Update project with validated order
    await prisma.project.update({
      where: { id: projectId },
      data: {
        orderedTracks: validatedOrder,
        averageMixScore: averageScore,
        lastOrderedAt: new Date(),
      },
    });

    this.logger.log(`Applied new order to project ${projectId}: ${validatedOrder.length} tracks, avg score: ${averageScore}`);
  }

  /**
   * Get conversation history for a project
   */
  getConversationHistory(projectId: string): ChatMessage[] {
    return this.conversations.get(projectId) || [];
  }

  /**
   * Clear conversation history for a project
   */
  clearConversationHistory(projectId: string): void {
    this.conversations.delete(projectId);
  }
}
