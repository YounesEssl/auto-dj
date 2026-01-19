import { Module, Global } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import * as path from 'path';

import { configuration } from './configuration';
import { validationSchema } from './validation.schema';

/**
 * Global configuration module with environment validation
 */
@Global()
@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: [
        path.resolve(__dirname, '../../../../.env'),
        path.resolve(process.cwd(), '.env'),
        path.resolve(process.cwd(), '../../.env'),
      ],
      load: [configuration],
      validationSchema: validationSchema,
      validationOptions: {
        allowUnknown: true,
        abortEarly: false,
      },
    }),
  ],
  exports: [ConfigModule],
})
export class ConfigurationModule {}
