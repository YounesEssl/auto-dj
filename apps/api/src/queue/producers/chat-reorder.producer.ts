import { Injectable } from '@nestjs/common';
import { InjectQueue } from '@nestjs/bullmq';
import { Queue } from 'bullmq';

import { QUEUE_NAMES } from '../queue.constants';

/**
 * Payload for chat reorder job
 */
export interface ChatReorderJobPayload {
  projectId: string;
  message: string;
  tracks: Array<{
    id: string;
    title?: string;
    artist?: string;
    original_name?: string;
    bpm?: number;
    key?: string;
    camelot?: string;
    energy?: number;
    duration?: number;
  }>;
  currentOrder: string[];
  conversationHistory: Array<{
    role: 'user' | 'assistant';
    content: string;
  }>;
}

/**
 * Producer for chat-based track reordering jobs
 */
@Injectable()
export class ChatReorderProducer {
  constructor(@InjectQueue(QUEUE_NAMES.CHAT_REORDER) private readonly queue: Queue) {}

  /**
   * Add a chat reorder job to the queue
   */
  async addJob(payload: ChatReorderJobPayload): Promise<string> {
    const job = await this.queue.add('chat-reorder', payload, {
      attempts: 2,
      backoff: {
        type: 'exponential',
        delay: 5000,
      },
      removeOnComplete: {
        age: 3600, // Keep completed jobs for 1 hour
        count: 100, // Keep last 100 completed jobs
      },
      removeOnFail: {
        age: 86400, // Keep failed jobs for 24 hours
      },
    });
    return job.id!;
  }
}
