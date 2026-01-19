import { Module } from '@nestjs/common';

import { DraftsController } from './drafts.controller';
import { DraftsService } from './drafts.service';
import { QueueModule } from '../queue/queue.module';
import { StorageModule } from '../storage/storage.module';

/**
 * Module for draft management (2-track transitions)
 */
@Module({
  imports: [QueueModule, StorageModule],
  controllers: [DraftsController],
  providers: [DraftsService],
  exports: [DraftsService],
})
export class DraftsModule {}
