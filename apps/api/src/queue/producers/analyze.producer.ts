import { Injectable } from '@nestjs/common';
import { InjectQueue } from '@nestjs/bullmq';
import { Queue } from 'bullmq';
import type { AnalyzeJobPayload } from '@autodj/shared-types';

import { QUEUE_NAMES } from '../queue.constants';

/**
 * Producer for analysis jobs
 */
@Injectable()
export class AnalyzeProducer {
  constructor(@InjectQueue(QUEUE_NAMES.ANALYZE) private readonly queue: Queue) {}

  /**
   * Add an analysis job to the queue
   */
  async addJob(payload: AnalyzeJobPayload): Promise<void> {
    await this.queue.add('analyze', payload, {
      attempts: 3,
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
  }
}
