'use client';

import { useState, useCallback } from 'react';
import axios, { AxiosProgressEvent } from 'axios';

export interface UploadProgress {
  fileId: string;
  progress: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
}

export interface PreSignedUploadResponse {
  upload_url: string;
  fields: { [key: string]: string };
  expires_at: string;
  s3_key: string;
  doc_id: string;
}

export interface DocumentCreateRequest {
  doc_id: string;
  s3_key: string;
  source: string;
  metadata?: { [key: string]: any };
  priority?: boolean;
  webhook_url?: string;
}

export interface DocumentResponse {
  doc_id: string;
  status: string;
  filename?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  user_id: string;
  metadata: { [key: string]: any };
  artifacts: { [key: string]: string };
  error_message?: string;
}

export function useS3Upload(apiBaseUrl: string = '/api') {
  const [uploadProgress, setUploadProgress] = useState<{
    [fileId: string]: UploadProgress;
  }>({});
  const [isUploading, setIsUploading] = useState(false);

  const updateProgress = useCallback(
    (fileId: string, update: Partial<UploadProgress>) => {
      setUploadProgress((prev) => ({
        ...prev,
        [fileId]: { ...prev[fileId], ...update },
      }));
    },
    []
  );

  const getPresignedUploadUrl = async (
    filename: string,
    contentType: string,
    fileSize: number
  ): Promise<PreSignedUploadResponse> => {
    const response = await axios.post(
      `${apiBaseUrl}/documents/upload/presigned`,
      {
        filename,
        content_type: contentType,
        file_size: fileSize,
      }
    );
    return response.data;
  };

  const uploadToS3 = async (
    file: File,
    uploadData: PreSignedUploadResponse,
    onProgress?: (progress: number) => void
  ): Promise<void> => {
    const formData = new FormData();

    // Add all the required fields from the pre-signed URL
    Object.entries(uploadData.fields).forEach(([key, value]) => {
      formData.append(key, value);
    });

    // Add the file last (S3 requirement)
    formData.append('file', file);

    await axios.post(uploadData.upload_url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent: AxiosProgressEvent) => {
        if (progressEvent.total) {
          const progress = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress?.(progress);
        }
      },
    });
  };

  const createDocument = async (
    request: DocumentCreateRequest
  ): Promise<DocumentResponse> => {
    const response = await axios.post(
      `${apiBaseUrl}/documents/create`,
      request
    );
    return response.data;
  };

  const uploadFiles = useCallback(
    async (
      files: File[],
      options: {
        priority?: boolean;
        webhookUrl?: string;
        metadata?: { [key: string]: any };
      } = {}
    ): Promise<DocumentResponse[]> => {
      setIsUploading(true);
      const results: DocumentResponse[] = [];
      const errors: string[] = [];

      try {
        // Initialize progress tracking for all files
        files.forEach((file) => {
          const fileId = `${file.name}-${file.size}-${Date.now()}`;
          updateProgress(fileId, {
            fileId,
            progress: 0,
            status: 'pending',
          });
        });

        // Upload files sequentially to avoid overwhelming the server
        for (let i = 0; i < files.length; i++) {
          const file = files[i];
          const fileId = `${file.name}-${file.size}-${Date.now()}-${i}`;

          try {
            // Step 1: Get pre-signed upload URL
            updateProgress(fileId, { status: 'uploading', progress: 0 });

            const uploadData = await getPresignedUploadUrl(
              file.name,
              file.type || 'application/octet-stream',
              file.size
            );

            // Step 2: Upload to S3 with progress tracking
            await uploadToS3(file, uploadData, (progress) => {
              updateProgress(fileId, { progress });
            });

            updateProgress(fileId, { progress: 95, status: 'uploading' });

            // Step 3: Create document record
            const documentRequest: DocumentCreateRequest = {
              doc_id: uploadData.doc_id,
              s3_key: uploadData.s3_key,
              source: 'upload',
              metadata: {
                ...options.metadata,
                originalFilename: file.name,
                fileSize: file.size,
                contentType: file.type,
              },
              priority: options.priority || false,
              webhook_url: options.webhookUrl,
            };

            const document = await createDocument(documentRequest);

            updateProgress(fileId, {
              progress: 100,
              status: 'success',
            });

            results.push(document);
          } catch (error) {
            console.error(`Failed to upload ${file.name}:`, error);

            let errorMessage = 'Upload failed';
            if (axios.isAxiosError(error)) {
              if (error.response?.status === 413) {
                errorMessage = 'File too large';
              } else if (error.response?.status === 400) {
                errorMessage = 'Invalid file type or format';
              } else if (error.response?.data?.message) {
                errorMessage = error.response.data.message;
              }
            }

            updateProgress(fileId, {
              status: 'error',
              error: errorMessage,
            });

            errors.push(`${file.name}: ${errorMessage}`);
          }
        }

        return results;
      } catch (error) {
        console.error('Upload process failed:', error);
        throw error;
      } finally {
        setIsUploading(false);
      }
    },
    [updateProgress]
  );

  const resetProgress = useCallback(() => {
    setUploadProgress({});
  }, []);

  return {
    uploadFiles,
    uploadProgress,
    isUploading,
    resetProgress,
    updateProgress,
  };
}
