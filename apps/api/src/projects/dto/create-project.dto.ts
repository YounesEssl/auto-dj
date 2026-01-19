import { IsString, MinLength, MaxLength } from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';

/**
 * DTO for creating a new project
 */
export class CreateProjectDto {
  @ApiProperty({
    example: 'Summer House Mix 2024',
    description: 'Name of the mix project',
    minLength: 1,
    maxLength: 200,
  })
  @IsString()
  @MinLength(1, { message: 'Project name is required' })
  @MaxLength(200, { message: 'Project name must not exceed 200 characters' })
  name!: string;
}
