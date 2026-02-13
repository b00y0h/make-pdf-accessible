import { AxiosInstance } from 'axios';

// Types matching the API responses
export interface Document {
  doc_id: string;
  user_id: string;
  filename: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
  completed_at?: string;
  metadata?: {
    originalSize?: number;
    pageCount?: number;
    title?: string;
    author?: string;
    [key: string]: any;
  };
  artifacts?: {
    textract?: string;
    structure?: string;
    alt_text?: string;
    tagged_pdf?: string;
    [key: string]: string | undefined;
  };
  scores?: {
    overall?: number;
    structure?: number;
    alt_text?: number;
    color_contrast?: number;
    navigation?: number;
  };
  priority: boolean;
  webhook_url?: string;
  error_message?: string;
  // Legacy fields for compatibility
  wcagLevel?: 'A' | 'AA' | 'AAA';
  issues?: number;
}

export interface DocumentListResponse {
  documents: Document[];
  total: number;
  page: number;
  per_page: number;
}

export interface ReportsSummary {
  total_documents: number;
  completed_documents: number;
  processing_documents: number;
  failed_documents: number;
  pending_documents: number;
  completion_rate: number;
  avg_processing_time_hours: number;
  weekly_stats: Array<{
    week: string;
    total_documents: number;
    completed_documents: number;
    failed_documents: number;
    success_rate: number;
  }>;
}

export interface DownloadResponse {
  download_url: string;
  expires_at: string;
  content_type: string;
  filename: string;
}

export interface UserProfile {
  sub: string;
  username: string;
  email?: string;
  roles: string[];
  claims: Record<string, any>;
}

export interface ProcessingStep {
  step: number;
  title: string;
  description: string;
  estimated_duration?: string;
}

export interface ProcessingStepsResponse {
  steps: ProcessingStep[];
  total_estimated_time?: string;
  pipeline_version?: string;
}

export class ApiService {
  constructor(private apiClient: AxiosInstance) {}

  // Public method to access the client for advanced use cases
  public getClient(): AxiosInstance {
    return this.apiClient;
  }

  // Documents
  async getDocuments(params?: {
    page?: number;
    per_page?: number;
    status?: string;
  }): Promise<DocumentListResponse> {
    const response = await this.apiClient.get('/documents', { params });
    return response.data;
  }

  async getDocument(docId: string): Promise<Document> {
    const response = await this.apiClient.get(`/documents/${docId}`);
    return response.data;
  }

  async uploadDocument(data: {
    file?: File;
    source_url?: string;
    filename?: string;
    priority?: boolean;
    webhook_url?: string;
    metadata?: Record<string, any>;
  }): Promise<Document> {
    const formData = new FormData();

    if (data.file) {
      formData.append('file', data.file);
    }
    if (data.source_url) {
      formData.append('source_url', data.source_url);
    }
    if (data.filename) {
      formData.append('filename', data.filename);
    }
    if (data.priority !== undefined) {
      formData.append('priority', data.priority.toString());
    }
    if (data.webhook_url) {
      formData.append('webhook_url', data.webhook_url);
    }
    if (data.metadata) {
      formData.append('metadata', JSON.stringify(data.metadata));
    }

    const response = await this.apiClient.post('/documents', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  async getDownloadUrl(
    docId: string,
    type: string,
    expiresIn?: number
  ): Promise<DownloadResponse> {
    const response = await this.apiClient.get(`/documents/${docId}/downloads`, {
      params: { document_type: type, expires_in: expiresIn },
    });
    return response.data;
  }

  async updateAltText(
    docId: string,
    altText: Record<string, any>
  ): Promise<void> {
    await this.apiClient.patch(`/documents/${docId}/alt-text`, altText);
  }

  // Alt-text review endpoints
  async getDocumentAltText(docId: string, statusFilter?: string): Promise<any> {
    const params = statusFilter ? { status_filter: statusFilter } : {};
    const response = await this.apiClient.get(`/documents/${docId}/alt-text`, {
      params,
    });
    return response.data;
  }

  async editFigureAltText(
    docId: string,
    figureId: string,
    text: string,
    comment?: string
  ): Promise<any> {
    const response = await this.apiClient.patch(
      `/documents/${docId}/alt-text`,
      {
        figure_id: figureId,
        text,
        comment,
      }
    );
    return response.data;
  }

  async updateFigureStatus(
    docId: string,
    figureIds: string[],
    status: string,
    comment?: string
  ): Promise<any> {
    const response = await this.apiClient.patch(
      `/documents/${docId}/alt-text/status`,
      {
        figure_ids: figureIds,
        status,
        comment,
      }
    );
    return response.data;
  }

  async getFigureHistory(docId: string, figureId: string): Promise<any> {
    const response = await this.apiClient.get(
      `/documents/${docId}/alt-text/${figureId}/history`
    );
    return response.data;
  }

  async revertFigureToVersion(
    docId: string,
    figureId: string,
    version: number
  ): Promise<any> {
    const response = await this.apiClient.post(
      `/documents/${docId}/alt-text/${figureId}/revert/${version}`
    );
    return response.data;
  }

  // Pre-signed upload endpoints
  async getPreSignedUploadUrl(
    filename: string,
    contentType: string,
    fileSize: number
  ): Promise<any> {
    const response = await this.apiClient.post('/documents/upload/presigned', {
      filename,
      content_type: contentType,
      file_size: fileSize,
    });
    return response.data;
  }

  async createDocumentFromUpload(
    docId: string,
    s3Key: string,
    source: string,
    metadata?: Record<string, any>
  ): Promise<Document> {
    const response = await this.apiClient.post('/documents/create', {
      doc_id: docId,
      s3_key: s3Key,
      source,
      metadata,
    });
    return response.data;
  }

  // Reports
  async getReportsSummary(): Promise<ReportsSummary> {
    const response = await this.apiClient.get('/reports/summary');
    return response.data;
  }

  async exportDocumentsCSV(params?: {
    start_date?: string;
    end_date?: string;
    owner_filter?: string;
    status_filter?: string;
  }): Promise<Blob> {
    const response = await this.apiClient.get('/reports/export.csv', {
      params,
      responseType: 'blob',
    });
    return response.data;
  }

  // Auth
  async getUserProfile(): Promise<UserProfile> {
    const response = await this.apiClient.get('/auth/me');
    return response.data;
  }

  // Admin
  async getUsers(params: {
    page: number;
    pageSize: number;
    sortBy: string;
    sortOrder: string;
    search?: string;
    role?: string;
  }): Promise<{ success: boolean; data: any; error?: string }> {
    const queryParams = new URLSearchParams();
    queryParams.append('page', params.page.toString());
    queryParams.append('pageSize', params.pageSize.toString());
    queryParams.append('sortBy', params.sortBy);
    queryParams.append('sortOrder', params.sortOrder);

    if (params.search) {
      queryParams.append('search', params.search);
    }
    if (params.role) {
      queryParams.append('role', params.role);
    }

    // Use dashboard's admin API instead of main API service
    const dashboardUrl =
      typeof window !== 'undefined'
        ? window.location.origin
        : 'http://localhost:3001';
    const response = await fetch(
      `${dashboardUrl}/api/admin/users?${queryParams.toString()}`,
      {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  async updateUserRole(
    userId: string,
    role: 'admin' | 'user'
  ): Promise<{ success: boolean; error?: string }> {
    const dashboardUrl =
      typeof window !== 'undefined'
        ? window.location.origin
        : 'http://localhost:3001';
    const response = await fetch(
      `${dashboardUrl}/api/admin/users/${userId}/role`,
      {
        method: 'PATCH',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ role }),
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  async deleteUser(
    userId: string
  ): Promise<{ success: boolean; error?: string }> {
    const dashboardUrl =
      typeof window !== 'undefined'
        ? window.location.origin
        : 'http://localhost:3001';
    const response = await fetch(`${dashboardUrl}/api/admin/users/${userId}`, {
      method: 'DELETE',
      credentials: 'include',
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  // Processing steps
  async getProcessingSteps(): Promise<ProcessingStepsResponse> {
    const response = await this.apiClient.get('/documents/processing-steps');
    return response.data;
  }

  // Health check
  async healthCheck(): Promise<{ status: string; version: string }> {
    const response = await this.apiClient.get('/health');
    return response.data;
  }
}

// Hook to get API service instance
export function useApiService() {
  // This will be used in components that need the API service
  return null as any; // Will be implemented with context
}
