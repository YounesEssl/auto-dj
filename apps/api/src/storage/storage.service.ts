import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import * as fs from 'fs/promises';
import * as path from 'path';

/**
 * Service for file storage operations.
 * Currently supports local storage, designed to be extended for S3.
 */
@Injectable()
export class StorageService {
  private readonly logger = new Logger(StorageService.name);
  private readonly storageType: string;
  private readonly storagePath: string;

  constructor(private readonly configService: ConfigService) {
    this.storageType = process.env.STORAGE_TYPE || this.configService.get<string>('STORAGE_TYPE', 'local');
    const configuredPath = process.env.STORAGE_PATH || this.configService.get<string>('STORAGE_PATH', './storage');
    // Always resolve to absolute path so workers can access files regardless of their cwd
    this.storagePath = path.resolve(configuredPath);
    this.logger.log(`Storage configured: type=${this.storageType}, path=${this.storagePath}`);
  }

  /**
   * Save a file to storage
   * @param buffer File contents
   * @param relativePath Relative path within storage (e.g., "projects/123/file.mp3")
   * @returns Full path to the saved file
   */
  async saveFile(buffer: Buffer, relativePath: string): Promise<string> {
    if (this.storageType === 'local') {
      return this.saveFileLocally(buffer, relativePath);
    }

    // TODO: Implement S3 storage
    throw new Error('S3 storage not yet implemented');
  }

  /**
   * Read a file from storage
   */
  async readFile(relativePath: string): Promise<Buffer> {
    if (this.storageType === 'local') {
      const fullPath = this.getFullPath(relativePath);
      return fs.readFile(fullPath);
    }

    // TODO: Implement S3 storage
    throw new Error('S3 storage not yet implemented');
  }

  /**
   * Delete a file from storage
   * Accepts both relative (storage/...) and absolute paths
   */
  async deleteFile(filePath: string): Promise<void> {
    if (this.storageType === 'local') {
      try {
        // Convert relative path to absolute if needed
        const absolutePath = filePath.startsWith('storage/')
          ? this.getFullPath(filePath.replace(/^storage\//, ''))
          : filePath;
        await fs.unlink(absolutePath);
        this.logger.log(`Deleted file: ${absolutePath}`);
      } catch (error) {
        this.logger.warn(`Failed to delete file: ${filePath}`, error);
      }
      return;
    }

    // TODO: Implement S3 storage
    throw new Error('S3 storage not yet implemented');
  }

  /**
   * Check if a file exists
   */
  async fileExists(relativePath: string): Promise<boolean> {
    if (this.storageType === 'local') {
      const fullPath = this.getFullPath(relativePath);
      try {
        await fs.access(fullPath);
        return true;
      } catch {
        return false;
      }
    }

    // TODO: Implement S3 storage
    throw new Error('S3 storage not yet implemented');
  }

  /**
   * Get the full path for a relative path
   */
  getFullPath(relativePath: string): string {
    return path.join(this.storagePath, relativePath);
  }

  /**
   * Get absolute path from a storage-relative path
   * Alias for getFullPath for clearer semantics
   */
  getAbsolutePath(relativePath: string): string {
    return this.getFullPath(relativePath);
  }

  /**
   * Save a file locally
   * Returns relative path (storage/...) for portability between API and workers
   */
  private async saveFileLocally(buffer: Buffer, relativePath: string): Promise<string> {
    const fullPath = this.getFullPath(relativePath);
    const directory = path.dirname(fullPath);

    // Ensure directory exists with open permissions for worker access
    await fs.mkdir(directory, { recursive: true, mode: 0o777 });
    // Explicitly chmod to override umask restrictions
    await fs.chmod(directory, 0o777);

    // Write file
    await fs.writeFile(fullPath, buffer);

    this.logger.log(`Saved file: ${fullPath}`);
    // Return relative path with storage/ prefix for workers to resolve
    return `storage/${relativePath}`;
  }

  /**
   * Ensure the base storage directory exists
   */
  async ensureStorageDirectory(): Promise<void> {
    await fs.mkdir(this.storagePath, { recursive: true, mode: 0o777 });
  }
}
