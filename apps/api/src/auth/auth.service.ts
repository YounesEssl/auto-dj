import { Injectable, UnauthorizedException, ConflictException } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { ConfigService } from '@nestjs/config';
import * as bcrypt from 'bcrypt';
import type { AuthResponse, JwtPayload } from '@autodj/shared-types';

import { UsersService } from '../users/users.service';
import { LoginDto } from './dto/login.dto';
import { RegisterDto } from './dto/register.dto';

/**
 * Service handling authentication operations
 */
@Injectable()
export class AuthService {
  private readonly saltRounds = 10;

  constructor(
    private readonly usersService: UsersService,
    private readonly jwtService: JwtService,
    private readonly configService: ConfigService
  ) {}

  /**
   * Register a new user
   */
  async register(dto: RegisterDto): Promise<AuthResponse> {
    // Check if user already exists
    const existingUser = await this.usersService.findByEmail(dto.email);
    if (existingUser) {
      throw new ConflictException('Email already registered');
    }

    // Hash password
    const passwordHash = await bcrypt.hash(dto.password, this.saltRounds);

    // Create user
    const user = await this.usersService.create({
      email: dto.email,
      passwordHash,
      name: dto.name,
    });

    // Generate tokens
    return this.generateAuthResponse(user);
  }

  /**
   * Authenticate a user with email and password
   */
  async login(dto: LoginDto): Promise<AuthResponse> {
    const user = await this.usersService.findByEmail(dto.email);
    if (!user) {
      throw new UnauthorizedException('Invalid credentials');
    }

    const isPasswordValid = await bcrypt.compare(dto.password, user.passwordHash);
    if (!isPasswordValid) {
      throw new UnauthorizedException('Invalid credentials');
    }

    return this.generateAuthResponse(user);
  }

  /**
   * Validate a user by ID (used by JWT strategy)
   */
  async validateUser(userId: string) {
    const user = await this.usersService.findById(userId);
    if (!user) {
      throw new UnauthorizedException('User not found');
    }
    return user;
  }

  /**
   * Generate JWT token and auth response
   */
  private generateAuthResponse(user: {
    id: string;
    email: string;
    name: string | null;
    plan: string;
    createdAt: Date;
    updatedAt: Date;
  }): AuthResponse {
    const payload: Omit<JwtPayload, 'iat' | 'exp'> = {
      sub: user.id,
      email: user.email,
    };

    const accessToken = this.jwtService.sign(payload);
    const expiresIn = this.getExpirationSeconds();

    return {
      accessToken,
      tokenType: 'Bearer',
      expiresIn,
      user: {
        id: user.id,
        email: user.email,
        name: user.name ?? undefined,
        plan: user.plan as 'FREE' | 'PRO' | 'ENTERPRISE',
        createdAt: user.createdAt,
        updatedAt: user.updatedAt,
      },
    };
  }

  /**
   * Get token expiration in seconds
   */
  private getExpirationSeconds(): number {
    const expiration = this.configService.get<string>('JWT_EXPIRATION', '7d');
    const match = expiration.match(/^(\d+)([dhms])$/);
    if (!match) return 604800; // Default 7 days

    const value = parseInt(match[1]!, 10);
    const unit = match[2]!;

    switch (unit) {
      case 'd':
        return value * 24 * 60 * 60;
      case 'h':
        return value * 60 * 60;
      case 'm':
        return value * 60;
      case 's':
        return value;
      default:
        return 604800;
    }
  }
}
