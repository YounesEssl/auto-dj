-- CreateEnum
CREATE TYPE "Plan" AS ENUM ('FREE', 'PRO', 'ENTERPRISE');

-- CreateEnum
CREATE TYPE "ProjectStatus" AS ENUM ('CREATED', 'UPLOADING', 'ANALYZING', 'ORDERING', 'READY', 'MIXING', 'COMPLETED', 'FAILED');

-- CreateEnum
CREATE TYPE "HarmonicCompatibility" AS ENUM ('PERFECT_MATCH', 'ADJACENT', 'RELATIVE', 'DIAGONAL_ADJACENT', 'ENERGY_BOOST', 'COMPATIBLE', 'RISKY');

-- CreateEnum
CREATE TYPE "TransitionAudioStatus" AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'ERROR');

-- CreateEnum
CREATE TYPE "MixSegmentType" AS ENUM ('SOLO', 'TRANSITION');

-- CreateEnum
CREATE TYPE "MixSegmentStatus" AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'ERROR');

-- CreateEnum
CREATE TYPE "JobType" AS ENUM ('ANALYZE', 'ORDER', 'TRANSITION_AUDIO', 'MIX');

-- CreateEnum
CREATE TYPE "JobStatus" AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED');

-- CreateEnum
CREATE TYPE "DraftStatus" AS ENUM ('CREATED', 'UPLOADING', 'ANALYZING', 'READY', 'GENERATING', 'COMPLETED', 'FAILED');

-- CreateEnum
CREATE TYPE "DraftTransitionStatus" AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'ERROR');

-- CreateEnum
CREATE TYPE "TransitionMode" AS ENUM ('STEMS', 'STEM_BLEND', 'CROSSFADE', 'HARD_CUT', 'FILTER_SWEEP', 'ECHO_OUT');

-- CreateTable
CREATE TABLE "users" (
    "id" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "password_hash" TEXT NOT NULL,
    "name" TEXT,
    "plan" "Plan" NOT NULL DEFAULT 'FREE',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "projects" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "status" "ProjectStatus" NOT NULL DEFAULT 'CREATED',
    "user_id" TEXT NOT NULL,
    "ordered_tracks" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "average_mix_score" DOUBLE PRECISION,
    "last_ordered_at" TIMESTAMP(3),
    "output_file" TEXT,
    "error_message" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "projects_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "tracks" (
    "id" TEXT NOT NULL,
    "project_id" TEXT,
    "filename" TEXT NOT NULL,
    "original_name" TEXT NOT NULL,
    "file_path" TEXT NOT NULL,
    "duration" DOUBLE PRECISION,
    "file_size" INTEGER NOT NULL,
    "mime_type" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "tracks_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "track_analyses" (
    "id" TEXT NOT NULL,
    "track_id" TEXT NOT NULL,
    "bpm" DOUBLE PRECISION NOT NULL,
    "bpm_confidence" DOUBLE PRECISION NOT NULL,
    "key" TEXT NOT NULL,
    "key_confidence" DOUBLE PRECISION NOT NULL,
    "camelot" TEXT NOT NULL,
    "energy" DOUBLE PRECISION NOT NULL,
    "danceability" DOUBLE PRECISION NOT NULL,
    "loudness" DOUBLE PRECISION NOT NULL,
    "beats" JSONB,
    "intro_start" DOUBLE PRECISION,
    "intro_end" DOUBLE PRECISION,
    "outro_start" DOUBLE PRECISION,
    "outro_end" DOUBLE PRECISION,
    "structure_json" JSONB,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "track_analyses_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "transitions" (
    "id" TEXT NOT NULL,
    "project_id" TEXT NOT NULL,
    "from_track_id" TEXT NOT NULL,
    "to_track_id" TEXT NOT NULL,
    "position" INTEGER NOT NULL,
    "score" INTEGER NOT NULL,
    "harmonic_score" INTEGER NOT NULL,
    "bpm_score" INTEGER NOT NULL,
    "energy_score" INTEGER NOT NULL,
    "compatibility_type" "HarmonicCompatibility" NOT NULL,
    "bpm_difference" DOUBLE PRECISION NOT NULL,
    "energy_difference" DOUBLE PRECISION NOT NULL,
    "audio_status" "TransitionAudioStatus" NOT NULL DEFAULT 'PENDING',
    "audio_file_path" TEXT,
    "audio_duration_ms" INTEGER,
    "track_a_cut_ms" INTEGER,
    "track_b_start_ms" INTEGER,
    "audio_error" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "transitions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "mix_segments" (
    "id" TEXT NOT NULL,
    "project_id" TEXT NOT NULL,
    "position" INTEGER NOT NULL,
    "type" "MixSegmentType" NOT NULL,
    "track_id" TEXT,
    "transition_id" TEXT,
    "start_ms" INTEGER NOT NULL,
    "end_ms" INTEGER NOT NULL,
    "duration_ms" INTEGER NOT NULL,
    "audio_file_path" TEXT,
    "audio_status" "MixSegmentStatus" NOT NULL DEFAULT 'PENDING',
    "audio_error" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "mix_segments_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "jobs" (
    "id" TEXT NOT NULL,
    "project_id" TEXT NOT NULL,
    "type" "JobType" NOT NULL,
    "status" "JobStatus" NOT NULL DEFAULT 'PENDING',
    "payload" JSONB NOT NULL,
    "result" JSONB,
    "error" TEXT,
    "progress" INTEGER NOT NULL DEFAULT 0,
    "started_at" TIMESTAMP(3),
    "completed_at" TIMESTAMP(3),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "jobs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "drafts" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "status" "DraftStatus" NOT NULL DEFAULT 'CREATED',
    "user_id" TEXT NOT NULL,
    "track_a_id" TEXT,
    "track_b_id" TEXT,
    "compatibility_score" INTEGER,
    "harmonic_score" INTEGER,
    "bpm_score" INTEGER,
    "energy_score" INTEGER,
    "bpm_difference" DOUBLE PRECISION,
    "transition_status" "DraftTransitionStatus" NOT NULL DEFAULT 'PENDING',
    "transition_file_path" TEXT,
    "transition_duration_ms" INTEGER,
    "transition_mode" "TransitionMode" NOT NULL DEFAULT 'STEMS',
    "track_a_outro_ms" INTEGER,
    "track_b_intro_ms" INTEGER,
    "transition_error" TEXT,
    "error_message" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "drafts_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "users_email_key" ON "users"("email");

-- CreateIndex
CREATE INDEX "projects_user_id_idx" ON "projects"("user_id");

-- CreateIndex
CREATE INDEX "projects_status_idx" ON "projects"("status");

-- CreateIndex
CREATE INDEX "tracks_project_id_idx" ON "tracks"("project_id");

-- CreateIndex
CREATE UNIQUE INDEX "track_analyses_track_id_key" ON "track_analyses"("track_id");

-- CreateIndex
CREATE INDEX "transitions_project_id_idx" ON "transitions"("project_id");

-- CreateIndex
CREATE UNIQUE INDEX "transitions_project_id_position_key" ON "transitions"("project_id", "position");

-- CreateIndex
CREATE INDEX "mix_segments_project_id_idx" ON "mix_segments"("project_id");

-- CreateIndex
CREATE UNIQUE INDEX "mix_segments_project_id_position_key" ON "mix_segments"("project_id", "position");

-- CreateIndex
CREATE INDEX "jobs_project_id_idx" ON "jobs"("project_id");

-- CreateIndex
CREATE INDEX "jobs_status_idx" ON "jobs"("status");

-- CreateIndex
CREATE INDEX "jobs_type_idx" ON "jobs"("type");

-- CreateIndex
CREATE UNIQUE INDEX "drafts_track_a_id_key" ON "drafts"("track_a_id");

-- CreateIndex
CREATE UNIQUE INDEX "drafts_track_b_id_key" ON "drafts"("track_b_id");

-- CreateIndex
CREATE INDEX "drafts_user_id_idx" ON "drafts"("user_id");

-- CreateIndex
CREATE INDEX "drafts_status_idx" ON "drafts"("status");

-- AddForeignKey
ALTER TABLE "projects" ADD CONSTRAINT "projects_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "tracks" ADD CONSTRAINT "tracks_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "projects"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "track_analyses" ADD CONSTRAINT "track_analyses_track_id_fkey" FOREIGN KEY ("track_id") REFERENCES "tracks"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "transitions" ADD CONSTRAINT "transitions_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "projects"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "mix_segments" ADD CONSTRAINT "mix_segments_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "projects"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "jobs" ADD CONSTRAINT "jobs_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "projects"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "drafts" ADD CONSTRAINT "drafts_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "drafts" ADD CONSTRAINT "drafts_track_a_id_fkey" FOREIGN KEY ("track_a_id") REFERENCES "tracks"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "drafts" ADD CONSTRAINT "drafts_track_b_id_fkey" FOREIGN KEY ("track_b_id") REFERENCES "tracks"("id") ON DELETE SET NULL ON UPDATE CASCADE;
