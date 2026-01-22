import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { LoggerModule } from 'nestjs-pino';

import { ConfigurationModule } from './config/config.module';
import { AuthModule } from './auth/auth.module';
import { UsersModule } from './users/users.module';
import { ProjectsModule } from './projects/projects.module';
import { TracksModule } from './tracks/tracks.module';
import { QueueModule } from './queue/queue.module';
import { StorageModule } from './storage/storage.module';
import { WebsocketModule } from './websocket/websocket.module';
import { HealthModule } from './health/health.module';
import { DraftsModule } from './drafts/drafts.module';
import { ChatModule } from './chat/chat.module';

/**
 * Root application module that imports all feature modules
 */
@Module({
  imports: [
    // Configuration
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: ['.env.local', '.env'],
    }),

    // Logging
    LoggerModule.forRoot({
      pinoHttp: {
        transport:
          process.env.NODE_ENV !== 'production'
            ? {
                target: 'pino-pretty',
                options: {
                  colorize: true,
                  singleLine: true,
                },
              }
            : undefined,
        level: process.env.LOG_LEVEL || 'info',
      },
    }),

    // Custom config module with validation
    ConfigurationModule,

    // Feature modules
    AuthModule,
    UsersModule,
    ProjectsModule,
    TracksModule,
    DraftsModule,
    ChatModule,
    QueueModule,
    StorageModule,
    WebsocketModule,
    HealthModule,
  ],
})
export class AppModule {}
