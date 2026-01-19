import { Injectable, UnauthorizedException } from '@nestjs/common';
import { PassportStrategy } from '@nestjs/passport';
import { ExtractJwt, Strategy } from 'passport-jwt';
import { ConfigService } from '@nestjs/config';
import type { Request } from 'express';
import type { JwtPayload } from '@autodj/shared-types';

import { AuthService } from '../auth.service';

/**
 * Extract JWT from query parameter (for audio streaming)
 */
function fromQueryParam(paramName: string) {
  return (request: Request): string | null => {
    const token = request.query[paramName];
    if (typeof token === 'string' && token.length > 0) {
      return token;
    }
    return null;
  };
}

/**
 * JWT Passport strategy for validating JWT tokens
 */
@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  constructor(
    configService: ConfigService,
    private readonly authService: AuthService
  ) {
    super({
      // Try Authorization header first, then query param (for audio elements)
      jwtFromRequest: ExtractJwt.fromExtractors([
        ExtractJwt.fromAuthHeaderAsBearerToken(),
        fromQueryParam('token'),
      ]),
      ignoreExpiration: false,
      secretOrKey: configService.get<string>('JWT_SECRET'),
    });
  }

  /**
   * Validate the JWT payload and return the user
   */
  async validate(payload: JwtPayload) {
    const user = await this.authService.validateUser(payload.sub);
    if (!user) {
      throw new UnauthorizedException('User not found');
    }
    return user;
  }
}
