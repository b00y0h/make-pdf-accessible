/**
 * MongoDB schemas, types, and utilities for PDF accessibility processing
 */

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
  CollectionName
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
  type QueryHint
} from './indexes';

// Export constants
export { COLLECTIONS } from './types';

// JSON schema imports (for runtime validation if needed)
export const DOCUMENT_SCHEMA = require('./documents.json');
export const JOB_SCHEMA = require('./jobs.json');

// Utility functions for working with MongoDB documents
export const MongoUtils = {
  /**
   * Convert a MongoDB document to API response format
   */
  toApiDocument(doc: any): any {
    if (!doc) return null;
    
    const { _id, ...rest } = doc;
    return {
      ...rest,
      // Convert ObjectId to string for API responses
      id: _id?.toString(),
      // Ensure dates are ISO strings
      createdAt: rest.createdAt?.toISOString?.() || rest.createdAt,
      updatedAt: rest.updatedAt?.toISOString?.() || rest.updatedAt,
      completedAt: rest.completedAt?.toISOString?.() || rest.completedAt
    };
  },
  
  /**
   * Convert API input to MongoDB document format
   */
  fromApiDocument(input: any): any {
    const { id, ...rest } = input;
    return {
      ...rest,
      // Convert date strings to Date objects
      createdAt: rest.createdAt ? new Date(rest.createdAt) : new Date(),
      updatedAt: rest.updatedAt ? new Date(rest.updatedAt) : new Date(),
      completedAt: rest.completedAt ? new Date(rest.completedAt) : null
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
      ...data
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
        ...data.retryPolicy
      },
      timeout: {
        executionTimeoutSeconds: 900,
        heartbeatIntervalSeconds: 30,
        ...data.timeout
      },
      worker: null,
      logs: [],
      ...data
    };
  },
  
  /**
   * Build MongoDB filter from type-safe filter object
   */
  buildDocumentFilter(filter: DocumentFilter): any {
    const mongoFilter: any = {};
    
    if (filter.docId) mongoFilter.docId = filter.docId;
    if (filter.ownerId) mongoFilter.ownerId = filter.ownerId;
    
    if (filter.status) {
      mongoFilter.status = Array.isArray(filter.status) 
        ? { $in: filter.status }
        : filter.status;
    }
    
    if (filter.createdAfter || filter.createdBefore) {
      mongoFilter.createdAt = {};
      if (filter.createdAfter) mongoFilter.createdAt.$gte = filter.createdAfter;
      if (filter.createdBefore) mongoFilter.createdAt.$lte = filter.createdBefore;
    }
    
    if (filter.updatedAfter || filter.updatedBefore) {
      mongoFilter.updatedAt = {};
      if (filter.updatedAfter) mongoFilter.updatedAt.$gte = filter.updatedAfter;
      if (filter.updatedBefore) mongoFilter.updatedAt.$lte = filter.updatedBefore;
    }
    
    if (filter.hasErrors !== undefined) {
      mongoFilter.errorMessage = filter.hasErrors ? { $ne: null } : null;
    }
    
    return mongoFilter;
  },
  
  /**
   * Build MongoDB filter from job filter object
   */
  buildJobFilter(filter: JobFilter): any {
    const mongoFilter: any = {};
    
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
      mongoFilter.createdAt = {};
      if (filter.createdAfter) mongoFilter.createdAt.$gte = filter.createdAfter;
      if (filter.createdBefore) mongoFilter.createdAt.$lte = filter.createdBefore;
    }
    
    if (filter.attempts) {
      mongoFilter.attempts = {};
      if (filter.attempts.min !== undefined) mongoFilter.attempts.$gte = filter.attempts.min;
      if (filter.attempts.max !== undefined) mongoFilter.attempts.$lte = filter.attempts.max;
    }
    
    if (filter.hasErrors !== undefined) {
      mongoFilter.error = filter.hasErrors ? { $ne: null } : null;
    }
    
    return mongoFilter;
  }
};

// Re-export types from MongoDB driver that we commonly use
export type { ObjectId } from 'mongodb';