/**
 * MongoDB schemas, types, and utilities for PDF accessibility processing
 */

import type { Filter, FilterOperators } from 'mongodb';

import documentSchema from './documents.json';
import jobSchema from './jobs.json';
import type {
  DocumentFilter,
  JobFilter,
  MongoDocument,
  MongoJob,
} from './types';

// Export all types
export type {
  // Core document types
  MongoDocument,
  MongoJob,
  DocumentStatus,
  JobStatus,
  ProcessingStep,
  ValidationLevel,
  WcagLevel,
  StepStatus,
  LogLevel,

  // Document interfaces
  DocumentMetadata,
  DocumentArtifacts,
  DocumentScores,
  ValidationIssue,
  StepResult,
  AIManifest,
  DocumentAI,

  // Job interfaces
  JobInput,
  JobMetrics,
  JobOutput,
  JobError,
  RetryPolicy,
  JobTimeout,
  WorkerInfo,
  JobLogEntry,

  // Filter and query types
  DocumentFilter,
  JobFilter,
  PaginationOptions,
  PaginatedResult,

  // Update types
  DocumentUpdate,
  JobUpdate,

  // Index types
  IndexDefinition,

  // Result types
  CreateResult,
  UpdateResult,
  DeleteResult,

  // Statistics types
  DocumentStats,
  JobStats,

  // Configuration types
  PersistenceProvider,
  FeatureFlags,
  MongoConfig,
  CollectionName,
} from './types';

// Export index definitions
export {
  DOCUMENT_INDEXES,
  JOB_INDEXES,
  ANALYTICS_INDEXES,
  ALL_INDEXES,
  getCollectionIndexes,
  validateIndexDefinition,
  QUERY_HINTS,
  type IndexCreationResult,
  type QueryHint,
} from './indexes';

// Export constants
export { COLLECTIONS } from './types';

// JSON schemas (for runtime validation if needed)
export const DOCUMENT_SCHEMA = documentSchema;
export const JOB_SCHEMA = jobSchema;

/** A timestamp as stored: a Date from the driver, or a string already */
type StoredTimestamp = { toISOString(): string } | string | null | undefined;

/** A stored record; fields other than these pass through toApiDocument */
export interface StoredRecord {
  _id?: { toString(): string } | null;
  createdAt?: StoredTimestamp;
  updatedAt?: StoredTimestamp;
  completedAt?: StoredTimestamp;
}

/** A record in API form: a string id, and Dates as ISO strings */
export interface ApiDocument {
  id: string | undefined;
  createdAt: StoredTimestamp;
  updatedAt: StoredTimestamp;
  completedAt: StoredTimestamp;
  [field: string]: unknown;
}

/** A record from the API; fields other than these pass through */
export interface ApiRecord {
  id?: string;
  // Anything `new Date()` accepts
  createdAt?: string | number | Date | null;
  updatedAt?: string | number | Date | null;
  completedAt?: string | number | Date | null;
  [field: string]: unknown;
}

/** An API record ready to store: no id, and timestamps as Dates */
export interface StorableRecord {
  createdAt: Date;
  updatedAt: Date;
  completedAt: Date | null;
  [field: string]: unknown;
}

// Dates become ISO strings; strings and missing values pass through as-is
const toIsoString = (value: StoredTimestamp) =>
  (typeof value === 'object' && value?.toISOString?.()) || value;

// Utility functions for working with MongoDB documents
export const MongoUtils = {
  /**
   * Convert a MongoDB document to API response format
   */
  toApiDocument(doc: StoredRecord | null | undefined): ApiDocument | null {
    if (!doc) return null;

    const { _id, ...rest } = doc;
    return {
      ...rest,
      // Convert ObjectId to string for API responses
      id: _id?.toString(),
      // Ensure dates are ISO strings
      createdAt: toIsoString(rest.createdAt),
      updatedAt: toIsoString(rest.updatedAt),
      completedAt: toIsoString(rest.completedAt),
    };
  },

  /**
   * Convert API input to MongoDB document format
   */
  fromApiDocument(input: ApiRecord): StorableRecord {
    // Keep every field except the API's id
    const { ...rest } = input;
    delete rest.id;
    return {
      ...rest,
      // Convert date strings to Date objects
      createdAt: rest.createdAt ? new Date(rest.createdAt) : new Date(),
      updatedAt: rest.updatedAt ? new Date(rest.updatedAt) : new Date(),
      completedAt: rest.completedAt ? new Date(rest.completedAt) : null,
    };
  },

  /**
   * Generate a new document with required fields
   */
  createDocument(data: Partial<MongoDocument>): Omit<MongoDocument, '_id'> {
    const now = new Date();
    return {
      docId: data.docId || crypto.randomUUID(),
      ownerId: data.ownerId || '',
      status: data.status || 'pending',
      filename: data.filename || null,
      createdAt: now,
      updatedAt: now,
      completedAt: null,
      metadata: data.metadata || {},
      artifacts: data.artifacts || {},
      scores: data.scores || {},
      issues: data.issues || [],
      ai: data.ai || {},
      errorMessage: data.errorMessage || null,
      ...data,
    };
  },

  /**
   * Generate a new job with required fields
   */
  createJob(data: Partial<MongoJob>): Omit<MongoJob, '_id'> {
    const now = new Date();
    return {
      jobId: data.jobId || crypto.randomUUID(),
      docId: data.docId || '',
      step: data.step || 'structure',
      status: data.status || 'pending',
      priority: data.priority || 5,
      createdAt: now,
      updatedAt: now,
      startedAt: null,
      completedAt: null,
      attempts: 0,
      maxAttempts: 3,
      executionTimeSeconds: null,
      input: data.input || {},
      output: null,
      error: null,
      retryPolicy: {
        enabled: true,
        backoffMultiplier: 2.0,
        initialDelaySeconds: 30,
        maxDelaySeconds: 1800,
        ...data.retryPolicy,
      },
      timeout: {
        executionTimeoutSeconds: 900,
        heartbeatIntervalSeconds: 30,
        ...data.timeout,
      },
      worker: null,
      logs: [],
      ...data,
    };
  },

  /**
   * Build MongoDB filter from type-safe filter object
   */
  buildDocumentFilter(filter: DocumentFilter): Filter<MongoDocument> {
    const mongoFilter: Filter<MongoDocument> = {};

    if (filter.docId) mongoFilter.docId = filter.docId;
    if (filter.ownerId) mongoFilter.ownerId = filter.ownerId;

    if (filter.status) {
      mongoFilter.status = Array.isArray(filter.status)
        ? { $in: filter.status }
        : filter.status;
    }

    if (filter.createdAfter || filter.createdBefore) {
      const createdAt: FilterOperators<Date> = {};
      if (filter.createdAfter) createdAt.$gte = filter.createdAfter;
      if (filter.createdBefore) createdAt.$lte = filter.createdBefore;
      mongoFilter.createdAt = createdAt;
    }

    if (filter.updatedAfter || filter.updatedBefore) {
      const updatedAt: FilterOperators<Date> = {};
      if (filter.updatedAfter) updatedAt.$gte = filter.updatedAfter;
      if (filter.updatedBefore) updatedAt.$lte = filter.updatedBefore;
      mongoFilter.updatedAt = updatedAt;
    }

    if (filter.hasErrors !== undefined) {
      mongoFilter.errorMessage = filter.hasErrors ? { $ne: null } : null;
    }

    return mongoFilter;
  },

  /**
   * Build MongoDB filter from job filter object
   */
  buildJobFilter(filter: JobFilter): Filter<MongoJob> {
    const mongoFilter: Filter<MongoJob> = {};

    if (filter.jobId) mongoFilter.jobId = filter.jobId;
    if (filter.docId) mongoFilter.docId = filter.docId;

    if (filter.step) {
      mongoFilter.step = Array.isArray(filter.step)
        ? { $in: filter.step }
        : filter.step;
    }

    if (filter.status) {
      mongoFilter.status = Array.isArray(filter.status)
        ? { $in: filter.status }
        : filter.status;
    }

    if (filter.priority) mongoFilter.priority = filter.priority;

    if (filter.createdAfter || filter.createdBefore) {
      const createdAt: FilterOperators<Date> = {};
      if (filter.createdAfter) createdAt.$gte = filter.createdAfter;
      if (filter.createdBefore) createdAt.$lte = filter.createdBefore;
      mongoFilter.createdAt = createdAt;
    }

    if (filter.attempts) {
      const attempts: FilterOperators<number> = {};
      if (filter.attempts.min !== undefined)
        attempts.$gte = filter.attempts.min;
      if (filter.attempts.max !== undefined)
        attempts.$lte = filter.attempts.max;
      mongoFilter.attempts = attempts;
    }

    if (filter.hasErrors !== undefined) {
      mongoFilter.error = filter.hasErrors ? { $ne: null } : null;
    }

    return mongoFilter;
  },
};

// Re-export types from MongoDB driver that we commonly use
export type { ObjectId } from 'mongodb';
