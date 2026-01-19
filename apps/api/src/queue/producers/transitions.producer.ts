import { Injectable, Logger } from '@nestjs/common';
import { InjectQueue } from '@nestjs/bullmq';
import { Queue } from 'bullmq';
import type { TransitionAudioJobPayload } from '@autodj/shared-types';

import { QUEUE_NAMES } from '../queue.constants';

/**
 * Producer for transition audio generation jobs
 */
@Injectable()
export class TransitionsProducer {
  private readonly logger = new Logger(TransitionsProducer.name);

  constructor(@InjectQueue(QUEUE_NAMES.TRANSITIONS) private readonly queue: Queue) {}

  /**
   * Add a transition audio generation job to the queue
   */
  async addJob(payload: TransitionAudioJobPayload): Promise<void> {
    this.logger.log(`Adding transition job: ${payload.transitionId}`);

    await this.queue.add('transition', payload, {
      attempts: 2, // Transition generation can be resource-intensive
      backoff: {
        type: 'exponential',
        delay: 10000,
      },
      removeOnComplete: {
        age: 3600, // Keep completed jobs for 1 hour
        count: 50, // Keep last 50 completed jobs
      },
      removeOnFail: {
        age: 86400, // Keep failed jobs for 24 hours
      },
    });
  }

  /**
   * Add multiple transition jobs for a project
   */
  async addBulkJobs(payloads: TransitionAudioJobPayload[]): Promise<void> {
    if (payloads.length === 0) return;

    this.logger.log(`Adding ${payloads.length} transition jobs`);

    const jobs = payloads.map((payload) => ({
      name: 'transition',
      data: payload,
      opts: {
        attempts: 2,
        backoff: {
          type: 'exponential' as const,
          delay: 10000,
        },
        removeOnComplete: {
          age: 3600,
          count: 50,
        },
        removeOnFail: {
          age: 86400,
        },
      },
    }));

    await this.queue.addBulk(jobs);
  }
}
