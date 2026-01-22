import {
  WebSocketGateway,
  WebSocketServer,
  SubscribeMessage,
  OnGatewayConnection,
  OnGatewayDisconnect,
  ConnectedSocket,
  MessageBody,
} from '@nestjs/websockets';
import { Logger } from '@nestjs/common';
import { Server, Socket } from 'socket.io';
import type { JobProgress, MixOrderedEvent, DraftProgress, DraftTransitionCompleteEvent } from '@autodj/shared-types';

/**
 * WebSocket gateway for real-time communication with clients.
 * Handles job progress updates and notifications.
 */
@WebSocketGateway({
  cors: {
    origin: process.env.CORS_ORIGINS?.split(',') || [
      'http://localhost:5173',
      'http://localhost:3000',
      'http://localhost',
      'http://localhost:80',
    ],
    credentials: true,
  },
  namespace: '/',
})
export class WebsocketGateway implements OnGatewayConnection, OnGatewayDisconnect {
  @WebSocketServer()
  server!: Server;

  private readonly logger = new Logger(WebsocketGateway.name);

  /**
   * Handle client connection
   */
  handleConnection(client: Socket) {
    this.logger.log(`Client connected: ${client.id}`);
  }

  /**
   * Handle client disconnection
   */
  handleDisconnect(client: Socket) {
    this.logger.log(`Client disconnected: ${client.id}`);
  }

  /**
   * Subscribe to project updates
   */
  @SubscribeMessage('subscribe')
  handleSubscribe(
    @ConnectedSocket() client: Socket,
    @MessageBody() data: { projectId: string }
  ) {
    const room = `project:${data.projectId}`;
    client.join(room);
    this.logger.log(`Client ${client.id} subscribed to ${room}`);
    return { event: 'subscribed', data: { projectId: data.projectId } };
  }

  /**
   * Unsubscribe from project updates
   */
  @SubscribeMessage('unsubscribe')
  handleUnsubscribe(
    @ConnectedSocket() client: Socket,
    @MessageBody() data: { projectId: string }
  ) {
    const room = `project:${data.projectId}`;
    client.leave(room);
    this.logger.log(`Client ${client.id} unsubscribed from ${room}`);
    return { event: 'unsubscribed', data: { projectId: data.projectId } };
  }

  /**
   * Send progress update to all clients subscribed to a project
   */
  sendProgress(projectId: string, progress: JobProgress) {
    const room = `project:${projectId}`;
    this.logger.log(`Sending progress to ${room}: ${JSON.stringify(progress)}`);
    this.server.to(room).emit('progress', progress);
    this.logger.log(`Progress sent to ${room}: ${progress.stage} ${progress.progress}%`);
  }

  /**
   * Send notification to a specific user
   */
  sendNotification(userId: string, message: string, type: 'info' | 'success' | 'error') {
    const room = `user:${userId}`;
    this.server.to(room).emit('notification', { message, type });
  }

  /**
   * Send mix ordered event to all clients subscribed to a project
   */
  sendMixOrdered(projectId: string, data: MixOrderedEvent) {
    const room = `project:${projectId}`;
    this.logger.log(`Sending mix:ordered to ${room}: ${data.orderedTrackIds.length} tracks, avg score: ${data.averageScore}`);
    this.server.to(room).emit('mix:ordered', data);
  }

  /**
   * Send transition audio progress update to all clients subscribed to a project
   */
  sendTransitionProgress(projectId: string, data: {
    projectId: string;
    transitionId: string;
    status: 'PROCESSING' | 'COMPLETED' | 'ERROR';
    progress?: number;
    completedCount?: number;
    totalCount?: number;
    error?: string;
    stage?: string;
    message?: string;
  }) {
    const room = `project:${projectId}`;
    this.logger.log(`Sending transition:progress to ${room}: ${data.transitionId} - ${data.status}`);
    this.server.to(room).emit('transition:progress', data);
  }

  // ==========================================================================
  // Draft-specific events
  // ==========================================================================

  /**
   * Subscribe to draft updates
   */
  @SubscribeMessage('draft:subscribe')
  handleDraftSubscribe(
    @ConnectedSocket() client: Socket,
    @MessageBody() data: { draftId: string }
  ) {
    const room = `draft:${data.draftId}`;
    client.join(room);
    this.logger.log(`Client ${client.id} subscribed to ${room}`);
    return { event: 'draft:subscribed', data: { draftId: data.draftId } };
  }

  /**
   * Unsubscribe from draft updates
   */
  @SubscribeMessage('draft:unsubscribe')
  handleDraftUnsubscribe(
    @ConnectedSocket() client: Socket,
    @MessageBody() data: { draftId: string }
  ) {
    const room = `draft:${data.draftId}`;
    client.leave(room);
    this.logger.log(`Client ${client.id} unsubscribed from ${room}`);
    return { event: 'draft:unsubscribed', data: { draftId: data.draftId } };
  }

  /**
   * Send draft transition progress update
   */
  sendDraftProgress(draftId: string, progress: DraftProgress) {
    const room = `draft:${draftId}`;
    this.logger.log(`Sending draft:progress to ${room}: ${progress.step} ${progress.progress}%`);
    this.server.to(room).emit('draft:progress', progress);
  }

  /**
   * Send draft transition complete event
   */
  sendDraftComplete(draftId: string, data: DraftTransitionCompleteEvent) {
    const room = `draft:${draftId}`;
    this.logger.log(`Sending draft:complete to ${room}: ${data.transitionMode}`);
    this.server.to(room).emit('draft:complete', data);
  }

  /**
   * Send draft error event
   */
  sendDraftError(draftId: string, error: string) {
    const room = `draft:${draftId}`;
    this.logger.log(`Sending draft:error to ${room}: ${error}`);
    this.server.to(room).emit('draft:error', { draftId, error });
  }

  /**
   * Send draft analysis complete event (when a track analysis finishes)
   */
  sendDraftAnalysisComplete(draftId: string, data: {
    draftId: string;
    slot: 'A' | 'B';
    trackId: string;
    status: 'ANALYZING' | 'READY';
  }) {
    const room = `draft:${draftId}`;
    this.logger.log(`Sending draft:analysis to ${room}: slot ${data.slot} - ${data.status}`);
    this.server.to(room).emit('draft:analysis', data);
  }

  // ==========================================================================
  // Chat-specific events
  // ==========================================================================

  /**
   * Send chat response event to all clients subscribed to a project
   */
  sendChatResponse(projectId: string, data: {
    projectId: string;
    response: string;
    newOrder?: string[] | null;
    reasoning?: string | null;
    changesMade: string[];
    projectData?: {
      orderedTracks: string[];
      transitions: unknown[];
      averageMixScore: number | null;
    } | null;
  }) {
    const room = `project:${projectId}`;
    this.logger.log(`Sending chat:response to ${room}: hasNewOrder=${!!data.newOrder}`);
    this.server.to(room).emit('chat:response', data);
  }
}
