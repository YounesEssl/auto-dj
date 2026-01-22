import { Injectable, Logger } from '@nestjs/common';
import { parseFile } from 'music-metadata';
import * as fs from 'fs';
import * as path from 'path';
import { v4 as uuidv4 } from 'uuid';

export interface ExtractedMetadata {
  title?: string;
  artist?: string;
  album?: string;
  genre?: string;
  year?: number;
  duration?: number;
  coverPath?: string;
}

/**
 * Service for extracting metadata from audio files
 */
@Injectable()
export class MetadataService {
  private readonly logger = new Logger(MetadataService.name);
  private readonly storagePath: string;

  constructor() {
    this.storagePath = process.env.STORAGE_PATH || '/app/storage';
  }

  /**
   * Extract metadata from an audio file
   */
  async extractMetadata(filePath: string, projectId: string): Promise<ExtractedMetadata> {
    try {
      const metadata = await parseFile(filePath);
      const result: ExtractedMetadata = {};

      // Extract common metadata
      if (metadata.common.title) {
        result.title = metadata.common.title;
      }

      if (metadata.common.artist) {
        result.artist = metadata.common.artist;
      } else if (metadata.common.artists?.length) {
        result.artist = metadata.common.artists.join(', ');
      }

      if (metadata.common.album) {
        result.album = metadata.common.album;
      }

      if (metadata.common.genre?.length) {
        result.genre = metadata.common.genre[0];
      }

      if (metadata.common.year) {
        result.year = metadata.common.year;
      }

      if (metadata.format.duration) {
        result.duration = metadata.format.duration;
      }

      // Extract cover art
      const picture = metadata.common.picture?.[0];
      if (picture) {
        result.coverPath = await this.saveCoverArt(picture, projectId);
      }

      this.logger.log(`Extracted metadata for ${filePath}: ${JSON.stringify(result)}`);
      return result;
    } catch (error) {
      this.logger.warn(`Failed to extract metadata from ${filePath}: ${error}`);
      return {};
    }
  }

  /**
   * Save cover art to storage and return the path
   */
  private async saveCoverArt(
    picture: { format: string; data: Uint8Array },
    projectId: string
  ): Promise<string | undefined> {
    try {
      // Determine file extension from MIME type
      const ext = this.getExtensionFromMime(picture.format);
      const filename = `${uuidv4()}.${ext}`;
      const relativePath = `projects/${projectId}/covers/${filename}`;
      const absolutePath = path.join(this.storagePath, relativePath);

      // Ensure directory exists
      const dir = path.dirname(absolutePath);
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }

      // Write cover file (convert Uint8Array to Buffer)
      fs.writeFileSync(absolutePath, Buffer.from(picture.data));

      this.logger.log(`Saved cover art to ${relativePath}`);
      return relativePath;
    } catch (error) {
      this.logger.warn(`Failed to save cover art: ${error}`);
      return undefined;
    }
  }

  /**
   * Get file extension from MIME type
   */
  private getExtensionFromMime(mime: string): string {
    const mimeMap: Record<string, string> = {
      'image/jpeg': 'jpg',
      'image/jpg': 'jpg',
      'image/png': 'png',
      'image/gif': 'gif',
      'image/webp': 'webp',
    };
    return mimeMap[mime] || 'jpg';
  }
}
