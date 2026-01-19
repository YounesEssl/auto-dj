import { Module, forwardRef } from '@nestjs/common';

import { ProjectsController } from './projects.controller';
import { ProjectsService } from './projects.service';
import { TracksModule } from '../tracks/tracks.module';
import { QueueModule } from '../queue/queue.module';
import { OrderingModule } from '../ordering/ordering.module';

/**
 * Module for mix project management
 */
@Module({
  imports: [forwardRef(() => TracksModule), QueueModule, OrderingModule],
  controllers: [ProjectsController],
  providers: [ProjectsService],
  exports: [ProjectsService],
})
export class ProjectsModule {}
