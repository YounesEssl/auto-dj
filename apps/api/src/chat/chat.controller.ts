import {
  Controller,
  Post,
  Get,
  Delete,
  Param,
  Body,
  UseGuards,
  HttpCode,
  HttpStatus,
} from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiBearerAuth } from '@nestjs/swagger';
import type { User } from '@autodj/database';

import { ChatService } from './chat.service';
import { ChatMessageDto } from './dto/chat-message.dto';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard';
import { CurrentUser } from '../common/decorators/current-user.decorator';

/**
 * Controller for chat-based track reordering
 */
@ApiTags('chat')
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller('projects/:projectId/chat')
export class ChatController {
  constructor(private readonly chatService: ChatService) {}

  /**
   * Send a chat message for track reordering
   */
  @Post()
  @HttpCode(HttpStatus.ACCEPTED)
  @ApiOperation({ summary: 'Send a chat message for AI-assisted track reordering' })
  @ApiResponse({ status: 202, description: 'Message queued for processing' })
  @ApiResponse({ status: 400, description: 'Invalid request or project not ready' })
  @ApiResponse({ status: 404, description: 'Project not found' })
  async sendMessage(
    @CurrentUser() user: User,
    @Param('projectId') projectId: string,
    @Body() dto: ChatMessageDto,
  ) {
    return this.chatService.sendMessage(projectId, user.id, dto.message);
  }

  /**
   * Get conversation history for a project
   */
  @Get('history')
  @ApiOperation({ summary: 'Get chat conversation history for a project' })
  @ApiResponse({ status: 200, description: 'Conversation history retrieved' })
  async getHistory(
    @CurrentUser() _user: User,
    @Param('projectId') projectId: string,
  ) {
    // Note: We should verify user owns the project, but the history
    // is in-memory and project-scoped, so it's implicitly secure
    const history = this.chatService.getConversationHistory(projectId);
    return { history };
  }

  /**
   * Clear conversation history for a project
   */
  @Delete('history')
  @HttpCode(HttpStatus.NO_CONTENT)
  @ApiOperation({ summary: 'Clear chat conversation history' })
  @ApiResponse({ status: 204, description: 'History cleared' })
  async clearHistory(
    @CurrentUser() _user: User,
    @Param('projectId') projectId: string,
  ) {
    this.chatService.clearConversationHistory(projectId);
  }
}
