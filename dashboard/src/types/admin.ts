import { ObjectId } from 'mongodb';

// User types
export type UserRole = 'user' | 'admin';

export interface User {
  _id?: ObjectId;
  id?: string; // For compatibility with existing code
  email: string;
  name?: string;
  username?: string; // For local admin login
  password?: string; // Hashed password for local admin
  role: UserRole;
  sub?: string; // Cognito subject ID
  cognitoGroups?: string[]; // Cognito groups
  cognitoUsername?: string; // Cognito username
  createdAt: Date;
  updatedAt: Date;
}

// Document types - matches existing schema
export type DocumentStatus =
  | 'pending'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'validation_failed'
  | 'notification_failed';

export interface Document {
  _id?: ObjectId;
  docId: string; // UUID v4
  ownerId: string; // User ID or sub
  status: DocumentStatus;
  filename?: string;
  sourceUrl?: string;
  metadata?: Record<string, any>;
  artifacts?: Record<string, any>;
  createdAt: Date;
  updatedAt: Date;
  completedAt?: Date;
}

// Admin-specific types
export interface UserSummary extends User {
  documentCount: number;
  documentsCompleted: number;
  documentsPending: number;
  documentsProcessing: number;
  documentsFailed: number;
  lastActivity?: Date;
}

export interface UserListParams {
  page: number;
  pageSize: number;
  search?: string;
  sortBy: 'email' | 'name' | 'createdAt' | 'documentCount' | 'lastActivity';
  sortOrder: 'asc' | 'desc';
  role?: UserRole;
}

export interface UserListResponse {
  users: UserSummary[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// Audit log types
export interface AuditLog {
  _id?: ObjectId;
  actorUserId: string;
  action: string; // e.g., "admin.delete_user", "user.login", etc.
  targetUserId?: string; // User being acted upon
  meta?: Record<string, any>; // Additional context
  createdAt: Date;
}

// Deletion job types
export type DeletionStatus = 'pending' | 'running' | 'done' | 'failed';

export interface DeletionJob {
  _id?: ObjectId;
  targetUserId: string;
  status: DeletionStatus;
  startedAt?: Date;
  finishedAt?: Date;
  error?: string;
  meta?: {
    deletedDocuments?: number;
    deletedStorageKeys?: string[];
    storageErrors?: string[];
  };
  createdAt: Date;
  updatedAt: Date;
}

export interface DeleteUserResult {
  success: boolean;
  jobId?: string;
  message: string;
  deletedDocuments?: number;
  error?: string;
}
