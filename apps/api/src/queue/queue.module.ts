import { Module, Global } from '@nestjs/common';
import { BullModule } from '@nestjs/bullmq';
import { ConfigModule, ConfigService } from '@nestjs/config';

import { QUEUE_NAMES } from './queue.constants';
import { QueueService } from './queue.service';
import { AnalyzeProducer } from './producers/analyze.producer';
import { TransitionsProducer } from './producers/transitions.producer';
import { MixProducer } from './producers/mix.producer';
import { DraftTransitionProducer } from './producers/draft-transition.producer';
import { ChatReorderProducer } from './producers/chat-reorder.producer';
import { ResultConsumer } from './consumers/result.consumer';
import { OrderingModule } from '../ordering/ordering.module';
import { ChatModule } from '../chat/chat.module';

// Re-export for convenience
export { QUEUE_NAMES } from './queue.constants';

/**
 * Global module for job queue operations
 */
@Global()
@Module({
  imports: [
    BullModule.forRootAsync({
      imports: [ConfigModule],
      useFactory: (configService: ConfigService) => ({
        connection: {
          host: configService.get<string>('REDIS_HOST', 'localhost'),
          port: configService.get<number>('REDIS_PORT', 6379),
          password: configService.get<string>('REDIS_PASSWORD') || undefined,
        },
      }),
      inject: [ConfigService],
    }),
    BullModule.registerQueue(
      { name: QUEUE_NAMES.ANALYZE },
      { name: QUEUE_NAMES.TRANSITIONS },
      { name: QUEUE_NAMES.MIX },
      { name: QUEUE_NAMES.RESULTS },
      { name: QUEUE_NAMES.DRAFT_TRANSITION },
      { name: QUEUE_NAMES.CHAT_REORDER }
    ),
    OrderingModule,
    ChatModule,
  ],
  providers: [QueueService, AnalyzeProducer, TransitionsProducer, MixProducer, DraftTransitionProducer, ChatReorderProducer, ResultConsumer],
  exports: [QueueService, TransitionsProducer, DraftTransitionProducer, ChatReorderProducer],
})
export class QueueModule {}
