import { Module, Global } from '@nestjs/common';

import { StorageService } from './storage.service';

/**
 * Global module for file storage operations
 */
@Global()
@Module({
  providers: [StorageService],
  exports: [StorageService],
})
export class StorageModule {}
