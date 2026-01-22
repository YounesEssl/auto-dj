import { Injectable, Logger, OnModuleInit } from '@nestjs/common';
import { InjectQueue } from '@nestjs/bullmq';
import { Queue } from 'bullmq';
import type { AnalyzeJobPayload } from '@autodj/shared-types';
import Redis from 'ioredis';

import { QUEUE_NAMES } from '../queue.constants';

/**
 * Producer for analysis jobs
 */
@Injectable()
export class AnalyzeProducer implements OnModuleInit {
  private readonly logger = new Logger(AnalyzeProducer.name);
  private directRedis: Redis;

  constructor(@InjectQueue(QUEUE_NAMES.ANALYZE) private readonly queue: Queue) {
    this.logger.log(`AnalyzeProducer initialized with queue: ${QUEUE_NAMES.ANALYZE}`);

    // Create direct Redis connection for testing
    this.directRedis = new Redis({
      host: process.env.REDIS_HOST || 'localhost',
      port: parseInt(process.env.REDIS_PORT || '6379'),
    });
  }

  async onModuleInit() {
    // Test direct Redis connection
    try {
      const pong = await this.directRedis.ping();
      this.logger.log(`Direct Redis PING: ${pong}`);

      const queueId = await this.directRedis.get('bull:audio-analyze:id');
      this.logger.log(`Direct Redis - current queue ID: ${queueId}`);
    } catch (error) {
      this.logger.error(`Direct Redis test failed: ${error}`);
    }
  }

  /**
   * Add an analysis job to the queue
   */
  async addJob(payload: AnalyzeJobPayload): Promise<void> {
    this.logger.log(`Adding analyze job for track: ${payload.trackId}, file: ${payload.filePath}`);

    // Check queue status before adding
    const jobCounts = await this.queue.getJobCounts();
    this.logger.log(`Queue status before add - waiting: ${jobCounts.waiting}, active: ${jobCounts.active}`);

    try {
      const job = await this.queue.add('analyze', payload, {
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
      this.logger.log(`Job added successfully with ID: ${job.id}`);

      // Verify job was added
      const jobCountsAfter = await this.queue.getJobCounts();
      this.logger.log(`Queue status after add - waiting: ${jobCountsAfter.waiting}, active: ${jobCountsAfter.active}`);

      // DIRECT REDIS CHECK - verify job actually exists
      const directQueueId = await this.directRedis.get('bull:audio-analyze:id');
      const directWaitLen = await this.directRedis.llen('bull:audio-analyze:wait');
      this.logger.log(`DIRECT REDIS CHECK - queue ID: ${directQueueId}, wait length: ${directWaitLen}`);

      // Check if job exists
      const jobExists = await this.directRedis.exists(`bull:audio-analyze:${job.id}`);
      this.logger.log(`DIRECT REDIS CHECK - job ${job.id} exists: ${jobExists}`);
    } catch (error) {
      this.logger.error(`Failed to add job: ${error}`);
      throw error;
    }
  }
}
