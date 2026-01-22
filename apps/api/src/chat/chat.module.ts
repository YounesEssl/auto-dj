import { Module } from '@nestjs/common';

import { ChatController } from './chat.controller';
import { ChatService } from './chat.service';
import { OrderingModule } from '../ordering/ordering.module';

/**
 * Module for chat-based track reordering
 */
@Module({
  imports: [OrderingModule],
  controllers: [ChatController],
  providers: [ChatService],
  exports: [ChatService],
})
export class ChatModule {}
