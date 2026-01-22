import { IsString, MinLength, MaxLength, IsOptional, IsArray } from 'class-validator';
import { ApiPropertyOptional } from '@nestjs/swagger';

/**
 * DTO for updating a project
 */
export class UpdateProjectDto {
  @ApiPropertyOptional({
    example: 'Summer House Mix 2024 - Updated',
    description: 'Name of the mix project',
    minLength: 1,
    maxLength: 200,
  })
  @IsOptional()
  @IsString()
  @MinLength(1, { message: 'Project name cannot be empty' })
  @MaxLength(200, { message: 'Project name must not exceed 200 characters' })
  name?: string;

  @ApiPropertyOptional({
    example: ['track-uuid-1', 'track-uuid-2', 'track-uuid-3'],
    description: 'Ordered array of track IDs for manual arrangement',
    type: [String],
  })
  @IsOptional()
  @IsArray()
  @IsString({ each: true, message: 'Each track ID must be a string' })
  orderedTracks?: string[];
}
