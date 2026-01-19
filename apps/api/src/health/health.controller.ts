import { Controller, Get } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse } from '@nestjs/swagger';
import { prisma } from '@autodj/database';

import { Public } from '../common/decorators/public.decorator';

interface HealthStatus {
  status: 'healthy' | 'unhealthy';
  timestamp: string;
  services: {
    api: 'up' | 'down';
    database: 'up' | 'down';
  };
  version: string;
}

/**
 * Controller for health check endpoints
 */
@ApiTags('health')
@Controller('health')
export class HealthController {
  /**
   * Basic health check
   */
  @Public()
  @Get()
  @ApiOperation({ summary: 'Health check endpoint' })
  @ApiResponse({ status: 200, description: 'Service is healthy' })
  async check(): Promise<HealthStatus> {
    let databaseStatus: 'up' | 'down' = 'down';

    try {
      await prisma.$queryRaw`SELECT 1`;
      databaseStatus = 'up';
    } catch (error) {
      databaseStatus = 'down';
    }

    const isHealthy = databaseStatus === 'up';

    return {
      status: isHealthy ? 'healthy' : 'unhealthy',
      timestamp: new Date().toISOString(),
      services: {
        api: 'up',
        database: databaseStatus,
      },
      version: process.env.npm_package_version || '0.1.0',
    };
  }

  /**
   * Liveness probe for Kubernetes
   */
  @Public()
  @Get('live')
  @ApiOperation({ summary: 'Liveness probe' })
  @ApiResponse({ status: 200, description: 'Service is live' })
  live() {
    return { status: 'live' };
  }

  /**
   * Readiness probe for Kubernetes
   */
  @Public()
  @Get('ready')
  @ApiOperation({ summary: 'Readiness probe' })
  @ApiResponse({ status: 200, description: 'Service is ready' })
  async ready() {
    try {
      await prisma.$queryRaw`SELECT 1`;
      return { status: 'ready' };
    } catch {
      return { status: 'not ready', reason: 'Database connection failed' };
    }
  }
}
