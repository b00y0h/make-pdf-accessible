/**
 * MongoDB index definitions for optimal query performance
 */

import type { IndexDefinition } from './types';

// Document collection indexes
export const DOCUMENT_INDEXES: IndexDefinition[] = [
  // Primary unique index on docId
  {
    name: 'docId_unique',
    keys: { docId: 1 },
    options: { unique: true, background: true },
  },

  // Owner and creation time for user document lists
  {
    name: 'owner_createdAt',
    keys: { ownerId: 1, createdAt: -1 },
    options: { background: true },
  },

  // Status and update time for processing queues
  {
    name: 'status_updatedAt',
    keys: { status: 1, updatedAt: -1 },
    options: { background: true },
  },

  // Owner and status for filtered user queries
  {
    name: 'owner_status',
    keys: { ownerId: 1, status: 1 },
    options: { background: true },
  },

  // Created time for temporal queries and cleanup
  {
    name: 'createdAt',
    keys: { createdAt: -1 },
    options: { background: true },
  },

  // Updated time for change tracking and sync
  {
    name: 'updatedAt',
    keys: { updatedAt: -1 },
    options: { background: true },
  },

  // Completed time for analytics and reporting
  {
    name: 'completedAt',
    keys: { completedAt: -1 },
    options: { background: true, sparse: true },
  },

  // Priority processing (metadata.priority = true)
  {
    name: 'priority_status',
    keys: { 'metadata.priority': -1, status: 1, createdAt: 1 },
    options: {
      background: true,
      sparse: true,
      partialFilterExpression: { 'metadata.priority': true },
    },
  },

  // Full-text search on filename
  {
    name: 'filename_text',
    keys: { filename: 'text' },
    options: { background: true, sparse: true },
  },
];

// Job collection indexes
export const JOB_INDEXES: IndexDefinition[] = [
  // Primary unique index on jobId
  {
    name: 'jobId_unique',
    keys: { jobId: 1 },
    options: { unique: true, background: true },
  },

  // Document jobs lookup
  {
    name: 'docId_updatedAt',
    keys: { docId: 1, updatedAt: -1 },
    options: { background: true },
  },

  // Job queue processing by status and priority
  {
    name: 'status_priority_createdAt',
    keys: { status: 1, priority: -1, createdAt: 1 },
    options: { background: true },
  },

  // Step-specific job queries
  {
    name: 'step_status',
    keys: { step: 1, status: 1 },
    options: { background: true },
  },

  // Document and step combination for workflow tracking
  {
    name: 'docId_step',
    keys: { docId: 1, step: 1 },
    options: { background: true },
  },

  // Created time for temporal queries
  {
    name: 'createdAt',
    keys: { createdAt: -1 },
    options: { background: true },
  },

  // Updated time for change tracking
  {
    name: 'updatedAt',
    keys: { updatedAt: -1 },
    options: { background: true },
  },

  // Started time for execution tracking
  {
    name: 'startedAt',
    keys: { startedAt: -1 },
    options: { background: true, sparse: true },
  },

  // Completed time for analytics
  {
    name: 'completedAt',
    keys: { completedAt: -1 },
    options: { background: true, sparse: true },
  },

  // Failed jobs for retry processing
  {
    name: 'failed_attempts',
    keys: { status: 1, attempts: 1, updatedAt: 1 },
    options: {
      background: true,
      partialFilterExpression: { status: { $in: ['failed', 'retry'] } },
    },
  },

  // Active jobs for monitoring and heartbeat
  {
    name: 'active_worker',
    keys: { status: 1, 'worker.instanceId': 1, startedAt: -1 },
    options: {
      background: true,
      sparse: true,
      partialFilterExpression: { status: 'running' },
    },
  },

  // Job cleanup - TTL index for completed jobs (30 days)
  {
    name: 'completed_ttl',
    keys: { completedAt: 1 },
    options: {
      background: true,
      sparse: true,
      expireAfterSeconds: 30 * 24 * 60 * 60, // 30 days
      partialFilterExpression: { status: 'completed' },
    },
  },
];

// Compound indexes for common query patterns
export const ANALYTICS_INDEXES: IndexDefinition[] = [
  // Document analytics by owner and time range
  {
    name: 'analytics_owner_time',
    keys: { ownerId: 1, status: 1, createdAt: -1, completedAt: -1 },
    options: { background: true },
  },

  // Job analytics by step and time range
  {
    name: 'analytics_step_time',
    keys: { step: 1, status: 1, createdAt: -1, executionTimeSeconds: -1 },
    options: { background: true },
  },

  // Processing pipeline performance tracking
  {
    name: 'pipeline_performance',
    keys: { docId: 1, step: 1, status: 1, startedAt: 1, completedAt: 1 },
    options: { background: true },
  },
];

// All indexes combined
export const ALL_INDEXES = {
  documents: [
    ...DOCUMENT_INDEXES,
    ...ANALYTICS_INDEXES.filter(
      (idx) =>
        idx.keys.hasOwnProperty('ownerId') || idx.keys.hasOwnProperty('docId')
    ),
  ],
  jobs: [
    ...JOB_INDEXES,
    ...ANALYTICS_INDEXES.filter(
      (idx) =>
        idx.keys.hasOwnProperty('step') || idx.keys.hasOwnProperty('docId')
    ),
  ],
};

/**
 * Get indexes for a specific collection
 */
export function getCollectionIndexes(
  collectionName: 'documents' | 'jobs'
): IndexDefinition[] {
  return ALL_INDEXES[collectionName] || [];
}

/**
 * Index creation utility with error handling
 */
export interface IndexCreationResult {
  name: string;
  success: boolean;
  error?: string;
  existing?: boolean;
}

/**
 * Validate index definition
 */
export function validateIndexDefinition(index: IndexDefinition): string[] {
  const errors: string[] = [];

  if (!index.name) {
    errors.push('Index name is required');
  }

  if (!index.keys || Object.keys(index.keys).length === 0) {
    errors.push('Index keys are required');
  }

  // Check for valid sort directions
  for (const [key, direction] of Object.entries(index.keys)) {
    if (direction !== 1 && direction !== -1 && direction !== 'text') {
      errors.push(`Invalid sort direction for key "${key}": ${direction}`);
    }
  }

  // Validate TTL options
  if (index.options?.expireAfterSeconds !== undefined) {
    if (index.options.expireAfterSeconds < 0) {
      errors.push('TTL expireAfterSeconds must be non-negative');
    }

    // TTL indexes should have exactly one key
    const keyCount = Object.keys(index.keys).length;
    if (keyCount !== 1) {
      errors.push('TTL indexes must have exactly one key');
    }
  }

  return errors;
}

/**
 * Get recommended query hints for common operations
 */
export const QUERY_HINTS = {
  documents: {
    // Find documents by owner, sorted by creation date
    findByOwner: { ownerId: 1, createdAt: -1 },

    // Find documents by status
    findByStatus: { status: 1, updatedAt: -1 },

    // Find document by ID
    findById: { docId: 1 },

    // Find priority documents
    findPriority: { 'metadata.priority': -1, status: 1, createdAt: 1 },
  },

  jobs: {
    // Find jobs for document
    findByDocument: { docId: 1, updatedAt: -1 },

    // Find jobs by status for processing
    findByStatus: { status: 1, priority: -1, createdAt: 1 },

    // Find job by ID
    findById: { jobId: 1 },

    // Find failed jobs for retry
    findFailedForRetry: { status: 1, attempts: 1, updatedAt: 1 },
  },
} as const;

export type QueryHint = typeof QUERY_HINTS;
