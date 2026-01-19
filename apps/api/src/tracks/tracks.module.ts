import { Module, forwardRef } from '@nestjs/common';

import { TracksController } from './tracks.controller';
import { TracksService } from './tracks.service';
import { StorageModule } from '../storage/storage.module';
import { QueueModule } from '../queue/queue.module';
import { ProjectsModule } from '../projects/projects.module';

/**
 * Module for track management and upload
 */
@Module({
  imports: [StorageModule, QueueModule, forwardRef(() => ProjectsModule)],
  controllers: [TracksController],
  providers: [TracksService],
  exports: [TracksService],
})
export class TracksModule {}
