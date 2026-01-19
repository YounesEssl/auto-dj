import { Injectable } from '@nestjs/common';
import { InjectQueue } from '@nestjs/bullmq';
import { Queue } from 'bullmq';
import type { DraftTransitionJobPayload } from '@autodj/shared-types';

import { QUEUE_NAMES } from '../queue.constants';

/**
 * Producer for draft transition generation jobs
 */
@Injectable()
export class DraftTransitionProducer {
  constructor(@InjectQueue(QUEUE_NAMES.DRAFT_TRANSITION) private readonly queue: Queue) {}

  /**
   * Add a draft transition job to the queue
   */
  async addJob(payload: DraftTransitionJobPayload): Promise<void> {
    await this.queue.add('generate-draft-transition', payload, {
      attempts: 2,
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
}
