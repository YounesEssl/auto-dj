import { IsString, MinLength, MaxLength, IsOptional } from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';

/**
 * DTO for creating a new draft
 */
export class CreateDraftDto {
  @ApiProperty({
    example: 'My Transition Test',
    description: 'Name for this draft transition (optional)',
    minLength: 1,
    maxLength: 200,
    required: false,
  })
  @IsOptional()
  @IsString()
  @MinLength(1, { message: 'Draft name cannot be empty' })
  @MaxLength(200, { message: 'Draft name must not exceed 200 characters' })
  name?: string;
}
