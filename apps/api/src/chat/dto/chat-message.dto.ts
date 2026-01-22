import { IsString, IsNotEmpty, MaxLength, MinLength } from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';

/**
 * DTO for sending a chat message
 */
export class ChatMessageDto {
  @ApiProperty({
    description: 'The user message for the AI assistant',
    example: 'Je veux que les morceaux énergiques soient au milieu du set',
    minLength: 3,
    maxLength: 2000,
  })
  @IsString()
  @IsNotEmpty()
  @MinLength(3)
  @MaxLength(2000)
  message!: string;
}
