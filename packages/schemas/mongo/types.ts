/**
 * MongoDB document types for PDF accessibility processing
 * Generated from JSON schemas with additional TypeScript enhancements
 */

import { ObjectId } from 'mongodb';

// Base types and enums
export type DocumentStatus =
  | 'pending'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'validation_failed'
  | 'notification_failed';

export type JobStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'retry'
  | 'timeout';

export type ProcessingStep =
  | 'structure'
  | 'ocr'
  | 'tagger'
  | 'validator'
  | 'exporter'
  | 'notifier';

export type ValidationLevel = 'error' | 'warning' | 'info';

export type WcagLevel = 'A' | 'AA' | 'AAA';

export type StepStatus = 'started' | 'processing' | 'completed' | 'failed';

export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

// Document-related interfaces
export interface DocumentMetadata {
  priority?: boolean;
  webhookUrl?: string | null;
  originalSize?: number | null;
  pageCount?: number | null;
  language?: string | null;
}

export interface DocumentArtifacts {
  original?: string | null;
  structure?: string | null;
  altText?: string | null;
  tagged?: string | null;
  html?: string | null;
  epub?: string | null;
  csvZip?: string | null;
}

export interface DocumentScores {
  validationScore?: number | null;
  pdfUaCompliant?: boolean | null;
  wcagLevel?: WcagLevel | null;
  structureScore?: number | null;
  altTextCoverage?: number | null;
}

export interface ValidationIssue {
  type: string;
  level: ValidationLevel;
  message: string;
  location?: string | null;
  rule?: string | null;
  count?: number | null;
}

export interface StepResult {
  status: StepStatus;
  startedAt?: Date | null;
  completedAt?: Date | null;
  processingTimeSeconds?: number | null;
  errorMessage?: string | null;
  // Step-specific metrics
  elementsProcessed?: number | null; // structure
  figuresProcessed?: number | null; // alt text
  tagsApplied?: number | null; // tagging
  issuesFound?: number | null; // validation
  exportsGenerated?: number | null; // exports
}

export interface AIManifest {
  structureExtraction?: StepResult | null;
  altTextGeneration?: StepResult | null;
  pdfTagging?: StepResult | null;
  validation?: StepResult | null;
  exports?: StepResult | null;
}

export interface DocumentAI {
  manifest?: AIManifest;
  totalProcessingTimeSeconds?: number | null;
}

export interface MongoDocument {
  _id?: ObjectId;
  docId: string;
  ownerId: string;
  status: DocumentStatus;
  filename?: string | null;
  createdAt: Date;
  updatedAt: Date;
  completedAt?: Date | null;
  metadata?: DocumentMetadata;
  artifacts?: DocumentArtifacts;
  scores?: DocumentScores;
  issues?: ValidationIssue[];
  ai?: DocumentAI;
  errorMessage?: string | null;
}

// Job-related interfaces
export interface JobInput {
  userId?: string;
  s3Keys?: {
    original?: string | null;
    structure?: string | null;
    altText?: string | null;
    tagged?: string | null;
    html?: string | null;
    [key: string]: string | null | undefined;
  };
  configuration?: Record<string, any>;
}

export interface JobMetrics {
  itemsProcessed?: number | null;
  bytesProcessed?: number | null;
  qualityScore?: number | null;
}

export interface JobOutput {
  s3Keys?: Record<string, string>;
  metrics?: JobMetrics;
  data?: Record<string, any>;
}

export interface JobError {
  code: string;
  message: string;
  details?: Record<string, any>;
  stack?: string | null;
  timestamp: Date;
}

export interface RetryPolicy {
  enabled?: boolean;
  backoffMultiplier?: number;
  initialDelaySeconds?: number;
  maxDelaySeconds?: number;
}

export interface JobTimeout {
  executionTimeoutSeconds?: number;
  heartbeatIntervalSeconds?: number;
}

export interface WorkerInfo {
  instanceId: string;
  version: string;
  region: string;
  startedAt: Date;
}

export interface JobLogEntry {
  timestamp: Date;
  level: LogLevel;
  message: string;
  context?: Record<string, any>;
}

export interface MongoJob {
  _id?: ObjectId;
  jobId: string;
  docId: string;
  step: ProcessingStep;
  status: JobStatus;
  priority?: number;
  createdAt: Date;
  updatedAt: Date;
  startedAt?: Date | null;
  completedAt?: Date | null;
  attempts?: number;
  maxAttempts?: number;
  executionTimeSeconds?: number | null;
  input?: JobInput;
  output?: JobOutput | null;
  error?: JobError | null;
  retryPolicy?: RetryPolicy;
  timeout?: JobTimeout;
  worker?: WorkerInfo | null;
  logs?: JobLogEntry[];
}

// Repository interfaces for type-safe operations
export interface DocumentFilter {
  docId?: string;
  ownerId?: string;
  status?: DocumentStatus | DocumentStatus[];
  createdAfter?: Date;
  createdBefore?: Date;
  updatedAfter?: Date;
  updatedBefore?: Date;
  hasErrors?: boolean;
}

export interface JobFilter {
  jobId?: string;
  docId?: string;
  step?: ProcessingStep | ProcessingStep[];
  status?: JobStatus | JobStatus[];
  priority?: number;
  createdAfter?: Date;
  createdBefore?: Date;
  attempts?: { min?: number; max?: number };
  hasErrors?: boolean;
}

export interface PaginationOptions {
  page: number;
  limit: number;
  sort?: Record<string, 1 | -1>;
}

export interface PaginatedResult<T> {
  documents: T[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
}

// Update operation types
export interface DocumentUpdate {
  status?: DocumentStatus;
  filename?: string | null;
  updatedAt: Date;
  completedAt?: Date | null;
  metadata?: Partial<DocumentMetadata>;
  artifacts?: Partial<DocumentArtifacts>;
  scores?: Partial<DocumentScores>;
  issues?: ValidationIssue[];
  ai?: Partial<DocumentAI>;
  errorMessage?: string | null;
}

export interface JobUpdate {
  status?: JobStatus;
  updatedAt: Date;
  startedAt?: Date | null;
  completedAt?: Date | null;
  attempts?: number;
  executionTimeSeconds?: number | null;
  output?: JobOutput | null;
  error?: JobError | null;
  worker?: WorkerInfo | null;
}

// Index definitions for MongoDB
export interface IndexDefinition {
  name: string;
  keys: Record<string, 1 | -1 | 'text'>;
  options?: {
    unique?: boolean;
    sparse?: boolean;
    background?: boolean;
    expireAfterSeconds?: number;
    partialFilterExpression?: Record<string, any>;
  };
}

// Repository method result types
export interface CreateResult<T> {
  acknowledged: boolean;
  insertedId: ObjectId;
  document: T;
}

export interface UpdateResult {
  acknowledged: boolean;
  modifiedCount: number;
  matchedCount: number;
}

export interface DeleteResult {
  acknowledged: boolean;
  deletedCount: number;
}

// Aggregation pipeline types
export interface DocumentStats {
  totalDocuments: number;
  documentsByStatus: Record<DocumentStatus, number>;
  averageProcessingTime: number | null;
  successRate: number;
  completedDocuments: number;
  failedDocuments: number;
  processingDocuments: number;
  pendingDocuments: number;
}

export interface JobStats {
  totalJobs: number;
  jobsByStatus: Record<JobStatus, number>;
  jobsByStep: Record<ProcessingStep, number>;
  averageExecutionTime: number | null;
  retryRate: number;
}

// Feature flag types
export type PersistenceProvider = 'mongo' | 'dynamo';

export interface FeatureFlags {
  persistenceProvider: PersistenceProvider;
  enableQueryLogging?: boolean;
  enablePerformanceMetrics?: boolean;
  enableDistributedTracing?: boolean;
}

// Connection and configuration types
export interface MongoConfig {
  connectionString: string;
  databaseName: string;
  collections: {
    documents: string;
    jobs: string;
  };
  options?: {
    maxPoolSize?: number;
    minPoolSize?: number;
    maxIdleTimeMS?: number;
    serverSelectionTimeoutMS?: number;
    socketTimeoutMS?: number;
    heartbeatFrequencyMS?: number;
    retryWrites?: boolean;
    retryReads?: boolean;
  };
}

// Export collections configuration
export const COLLECTIONS = {
  documents: 'documents',
  jobs: 'jobs',
} as const;

export type CollectionName = keyof typeof COLLECTIONS;
