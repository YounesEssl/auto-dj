import { createParamDecorator, ExecutionContext } from '@nestjs/common';
import type { User } from '@autodj/database';

/**
 * Parameter decorator to extract the current authenticated user from the request
 *
 * @example
 * ```typescript
 * @Get('me')
 * getProfile(@CurrentUser() user: User) {
 *   return user;
 * }
 * ```
 */
export const CurrentUser = createParamDecorator(
  (data: keyof User | undefined, ctx: ExecutionContext) => {
    const request = ctx.switchToHttp().getRequest();
    const user = request.user as User;

    return data ? user?.[data] : user;
  }
);
