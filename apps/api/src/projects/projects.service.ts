import { Injectable, NotFoundException, ForbiddenException } from '@nestjs/common';
import { prisma, ProjectStatus } from '@autodj/database';

import { CreateProjectDto } from './dto/create-project.dto';
import { UpdateProjectDto } from './dto/update-project.dto';

/**
 * Service for project data operations
 */
@Injectable()
export class ProjectsService {
  /**
   * Find all projects for a user
   */
  async findAllByUser(userId: string) {
    return prisma.project.findMany({
      where: { userId },
      include: {
        tracks: {
          select: {
            id: true,
            originalName: true,
            duration: true,
          },
        },
        _count: {
          select: { tracks: true },
        },
      },
      orderBy: { createdAt: 'desc' },
    });
  }

  /**
   * Find a project by ID
   */
  async findById(id: string) {
    const project = await prisma.project.findUnique({
      where: { id },
      include: {
        tracks: {
          include: {
            analysis: true,
          },
          orderBy: { createdAt: 'asc' },
        },
        transitions: {
          orderBy: { position: 'asc' },
        },
      },
    });

    if (!project) {
      throw new NotFoundException('Project not found');
    }

    return project;
  }

  /**
   * Find a project by ID and verify ownership
   */
  async findByIdAndUser(id: string, userId: string) {
    const project = await this.findById(id);

    if (project.userId !== userId) {
      throw new ForbiddenException('Access denied');
    }

    return project;
  }

  /**
   * Create a new project
   */
  async create(userId: string, dto: CreateProjectDto) {
    return prisma.project.create({
      data: {
        name: dto.name,
        userId,
        status: 'CREATED' as ProjectStatus,
      },
    });
  }

  /**
   * Update a project
   */
  async update(id: string, userId: string, dto: UpdateProjectDto) {
    await this.findByIdAndUser(id, userId);

    return prisma.project.update({
      where: { id },
      data: dto,
    });
  }

  /**
   * Update project status
   */
  async updateStatus(id: string, status: ProjectStatus, errorMessage?: string) {
    return prisma.project.update({
      where: { id },
      data: {
        status,
        errorMessage,
      },
    });
  }

  /**
   * Set the ordered track IDs after optimization
   */
  async setOrderedTracks(id: string, orderedTrackIds: string[]) {
    return prisma.project.update({
      where: { id },
      data: {
        orderedTracks: orderedTrackIds,
      },
    });
  }

  /**
   * Set the output file path after mix generation
   */
  async setOutputFile(id: string, outputFile: string) {
    return prisma.project.update({
      where: { id },
      data: {
        outputFile,
        status: 'COMPLETED' as ProjectStatus,
      },
    });
  }

  /**
   * Delete a project and all associated data
   */
  async delete(id: string, userId: string) {
    await this.findByIdAndUser(id, userId);

    // Cascade delete will handle tracks and analyses
    return prisma.project.delete({
      where: { id },
    });
  }
}
