import { Module, Global } from '@nestjs/common';

import { WebsocketGateway } from './websocket.gateway';

/**
 * Global module for WebSocket communication
 */
@Global()
@Module({
  providers: [WebsocketGateway],
  exports: [WebsocketGateway],
})
export class WebsocketModule {}
