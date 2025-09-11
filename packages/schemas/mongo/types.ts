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
  // Enhanced metadata from Textract queries
  title?: string | null;
  author?: string | null;
  subject?: string | null;
  creator?: string | null;
  producer?: string | null;
  creationDate?: string | null;
  modificationDate?: string | null;
  keyTopics?: string | null;
  hasFormFields?: boolean | null;
  hasJavaScript?: boolean | null;
  isEncrypted?: boolean | null;
  pdfVersion?: string | null;
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

export interface AIConfidenceScores {
  structureExtraction?: number; // 0-1 confidence in structure analysis
  altTextGeneration?: number; // 0-1 average confidence across all figures
  headingLevels?: number; // 0-1 confidence in heading hierarchy
  tableStructure?: number; // 0-1 confidence in table parsing
  contentClassification?: number; // 0-1 confidence in content type detection
  metadataExtraction?: number; // 0-1 confidence in document metadata
  readingOrder?: number; // 0-1 confidence in reading order detection
  overall?: number; // 0-1 overall processing confidence
}

export interface AIManifest {
  structureExtraction?: StepResult | null;
  altTextGeneration?: StepResult | null;
  pdfTagging?: StepResult | null;
  validation?: StepResult | null;
  exports?: StepResult | null;
  confidenceScores?: AIConfidenceScores;
}

export interface DocumentAI {
  manifest?: AIManifest;
  totalProcessingTimeSeconds?: number | null;
  needsHumanReview?: boolean; // True if any confidence score is below threshold
  reviewPriority?: 'low' | 'medium' | 'high'; // Based on confidence scores
  confidenceThreshold?: number; // Minimum confidence for auto-approval (default 0.8)
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

// LLM Corpus Preparation Types
export type ChunkType = 'text' | 'table' | 'figure' | 'heading' | 'list' | 'caption';

export interface BoundingBox {
  left: number;
  top: number;
  width: number;
  height: number;
}

export interface TextChunk {
  id: string;
  docId: string;
  chunkIndex: number;
  type: ChunkType;
  content: string;
  cleanedContent: string; // Processed for LLM consumption
  
  // Positional context
  page: number;
  boundingBox?: BoundingBox;
  sectionPath: string[]; // e.g., ["Introduction", "Methods", "Results"]
  hierarchyLevel?: number; // Heading level, table depth, etc.
  
  // Content metadata
  characterCount: number;
  wordCount: number;
  hasCode?: boolean;
  hasMath?: boolean;
  hasLinks?: boolean;
  
  // Associated media/figures
  altText?: string;
  caption?: string;
  figureType?: string; // chart, diagram, image, etc.
  
  // Table-specific metadata
  tableStructure?: {
    rows: number;
    columns: number;
    hasHeaders: boolean;
    markdownRepresentation?: string;
    jsonRepresentation?: Record<string, any>;
  };
  
  // Relationships
  parentChunkId?: string;
  childChunkIds: string[];
  siblingChunkIds: string[];
  
  // Quality scores
  readabilityScore?: number;
  structuralIntegrity?: number;
  accessibilityScore?: number;
  
  // Processing metadata
  extractionMethod: 'textract' | 'pypdf2' | 'pdfplumber';
  extractionConfidence?: number;
  createdAt: Date;
  updatedAt: Date;
}

export interface EmbeddingVector {
  id: string;
  chunkId: string;
  docId: string;
  
  // Vector data
  vector: number[];
  model: string; // e.g., "amazon.titan-embed-text-v1"
  dimensions: number;
  
  // Content preview for debugging
  contentPreview: string; // First 100 chars
  
  // Embedding metadata
  createdAt: Date;
  modelVersion?: string;
}

export interface DocumentCorpus {
  docId: string;
  totalChunks: number;
  chunks: TextChunk[];
  embeddings?: EmbeddingVector[];
  
  // Corpus-level metadata
  totalCharacters: number;
  totalWords: number;
  averageChunkSize: number;
  chunkSizeDistribution: {
    min: number;
    max: number;
    median: number;
    p95: number;
  };
  
  // Content analysis
  topicSummary?: string;
  keyEntities?: string[];
  contentTypes: Record<ChunkType, number>;
  
  // Quality metrics
  overallReadability?: number;
  structuralCompleteness?: number;
  
  // Processing info
  processedAt: Date;
  processingVersion: string;
}

// Search and retrieval types
export interface SearchQuery {
  text: string;
  filters?: {
    docIds?: string[];
    chunkTypes?: ChunkType[];
    dateRange?: {
      start: Date;
      end: Date;
    };
    authorFilters?: string[];
  };
  options?: {
    limit?: number;
    minScore?: number;
    includeContent?: boolean;
    includeContext?: boolean; // Include surrounding chunks
    hybrid?: boolean; // Combine semantic + keyword search
  };
}

export interface SearchResult {
  chunkId: string;
  docId: string;
  score: number;
  content: string;
  metadata: {
    type: ChunkType;
    page: number;
    sectionPath: string[];
    boundingBox?: BoundingBox;
  };
  context?: {
    before?: TextChunk[];
    after?: TextChunk[];
  };
  highlights?: string[]; // Highlighted matching text
}

export interface CitationContext {
  docId: string;
  chunkId: string;
  title: string;
  author?: string;
  page: number;
  sectionPath: string[];
  boundingBox?: BoundingBox;
  excerpt: string; // Relevant text excerpt
  confidence: number;
}

// Query and Answer types for RAG
export interface RAGQuery {
  id: string;
  question: string;
  userId: string;
  
  // Search context
  retrievalResults: SearchResult[];
  selectedChunks: string[]; // Chunk IDs used for answer
  
  // Answer generation
  answer: string;
  citations: CitationContext[];
  confidence: number;
  
  // Processing metadata
  processingTimeMs: number;
  modelUsed: string;
  tokensUsed?: number;
  
  createdAt: Date;
}

// Enhanced DocumentArtifacts for LLM corpus
export interface EnhancedDocumentArtifacts extends DocumentArtifacts {
  corpus?: string; // S3 key for processed corpus JSON
  embeddings?: string; // S3 key for embeddings data
  searchIndex?: string; // OpenSearch index ID
}
