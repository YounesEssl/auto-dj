import { Injectable } from '@nestjs/common';
import { InjectQueue } from '@nestjs/bullmq';
import { Queue } from 'bullmq';
import type { MixJobPayload } from '@autodj/shared-types';

import { QUEUE_NAMES } from '../queue.constants';

/**
 * Producer for mix generation jobs
 */
@Injectable()
export class MixProducer {
  constructor(@InjectQueue(QUEUE_NAMES.MIX) private readonly queue: Queue) {}

  /**
   * Add a mix generation job to the queue
   */
  async addJob(payload: MixJobPayload): Promise<void> {
    await this.queue.add('mix', payload, {
      attempts: 2,
      backoff: {
        type: 'exponential',
        delay: 10000,
      },
      removeOnComplete: {
        age: 86400, // Keep completed jobs for 24 hours
        count: 50,
      },
      removeOnFail: {
        age: 604800, // Keep failed jobs for 7 days
      },
    });
  }
}
