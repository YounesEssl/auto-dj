import { Injectable } from '@nestjs/common';
import { prisma } from '@autodj/database';
import type { Plan } from '@autodj/database';

interface CreateUserInput {
  email: string;
  passwordHash: string;
  name?: string;
}

/**
 * Service for user data operations
 */
@Injectable()
export class UsersService {
  /**
   * Find a user by their ID
   */
  async findById(id: string) {
    return prisma.user.findUnique({
      where: { id },
    });
  }

  /**
   * Find a user by their email address
   */
  async findByEmail(email: string) {
    return prisma.user.findUnique({
      where: { email },
    });
  }

  /**
   * Create a new user
   */
  async create(data: CreateUserInput) {
    return prisma.user.create({
      data: {
        email: data.email,
        passwordHash: data.passwordHash,
        name: data.name,
        plan: 'FREE' as Plan,
      },
    });
  }

  /**
   * Update a user's profile
   */
  async update(id: string, data: { name?: string }) {
    return prisma.user.update({
      where: { id },
      data,
    });
  }

  /**
   * Update a user's plan
   */
  async updatePlan(id: string, plan: Plan) {
    return prisma.user.update({
      where: { id },
      data: { plan },
    });
  }
}
