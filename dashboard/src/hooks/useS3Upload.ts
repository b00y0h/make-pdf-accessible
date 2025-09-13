import { useState, useCallback } from 'react';
import { useApiService } from './useApi';

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

export interface UploadResult {
  docId: string;
  s3Key: string;
}

export interface S3UploadOptions {
  onProgress?: (progress: UploadProgress) => void;
  onSuccess?: (result: UploadResult) => void;
  onError?: (error: Error) => void;
}

export interface PreSignedUploadResponse {
  upload_url: string;
  fields: Record<string, string>;
  expires_at: string;
  s3_key: string;
  doc_id: string;
}

export function useS3Upload() {
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState<UploadProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const apiService = useApiService();

  const uploadToS3 = useCallback(
    async (
      file: File,
      options: S3UploadOptions = {}
    ): Promise<UploadResult> => {
      if (!apiService) {
        throw new Error('API service not available');
      }

      setIsUploading(true);
      setError(null);
      setProgress(null);

      try {
        // Step 1: Get pre-signed upload URL
        const uploadData = {
          filename: file.name,
          content_type: file.type,
          file_size: file.size,
        };

        console.log('Uploading file:', uploadData);
        console.log('File details:', {
          name: file.name,
          type: file.type,
          size: file.size,
          lastModified: file.lastModified,
        });

        const preSignedResponse = await apiService
          .getClient()
          .post('/documents/upload/presigned', uploadData);

        const preSignedData: PreSignedUploadResponse = preSignedResponse.data;

        // Step 2: Upload directly to S3
        const formData = new FormData();

        // Add all required fields first
        Object.entries(preSignedData.fields).forEach(([key, value]) => {
          formData.append(key, value);
        });

        // Add file last
        formData.append('file', file);

        // Upload with progress tracking
        const uploadResult = await new Promise<void>((resolve, reject) => {
          const xhr = new XMLHttpRequest();

          xhr.upload.onprogress = (event) => {
            if (event.lengthComputable) {
              const progressData: UploadProgress = {
                loaded: event.loaded,
                total: event.total,
                percentage: Math.round((event.loaded / event.total) * 100),
              };
              setProgress(progressData);
              options.onProgress?.(progressData);
            }
          };

          xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
              resolve();
            } else {
              reject(new Error(`Upload failed with status: ${xhr.status}`));
            }
          };

          xhr.onerror = () =>
            reject(new Error('Upload failed due to network error'));
          xhr.ontimeout = () => reject(new Error('Upload timed out'));

          xhr.timeout = 300000; // 5 minutes
          xhr.open('POST', preSignedData.upload_url);
          xhr.send(formData);
        });

        // Step 3: Create document record in API
        const createResponse = await apiService
          .getClient()
          .post('/documents/create', {
            doc_id: preSignedData.doc_id,
            s3_key: preSignedData.s3_key,
            filename: file.name,
            content_type: file.type,
            file_size: file.size,
            source: 'upload',
          });

        const result: UploadResult = {
          docId: preSignedData.doc_id,
          s3Key: preSignedData.s3_key,
        };

        options.onSuccess?.(result);
        return result;
      } catch (err: any) {
        console.error('Upload error details:', {
          message: err.message,
          response: err.response?.data,
          status: err.response?.status,
          headers: err.response?.headers,
          config: err.config?.data,
        });
        console.error('Full error response:', err.response);
        const error = err instanceof Error ? err : new Error('Upload failed');
        setError(error.message);
        options.onError?.(error);
        throw error;
      } finally {
        setIsUploading(false);
      }
    },
    [apiService]
  );

  const uploadMultiple = useCallback(
    async (
      files: File[],
      options: Omit<S3UploadOptions, 'onProgress'> & {
        onProgress?: (fileIndex: number, progress: UploadProgress) => void;
        onFileComplete?: (fileIndex: number, result: UploadResult) => void;
        onFileError?: (fileIndex: number, error: Error) => void;
      } = {}
    ): Promise<UploadResult[]> => {
      const results: UploadResult[] = [];

      for (let i = 0; i < files.length; i++) {
        const file = files[i];

        try {
          const result = await uploadToS3(file, {
            onProgress: (progress) => options.onProgress?.(i, progress),
            onSuccess: (result) => {
              results.push(result);
              options.onFileComplete?.(i, result);
            },
            onError: (error) => options.onFileError?.(i, error),
          });
        } catch (error) {
          // Continue with remaining files even if one fails
          console.error(`Failed to upload file ${i + 1}:`, error);
        }
      }

      return results;
    },
    [uploadToS3]
  );

  const reset = useCallback(() => {
    setProgress(null);
    setError(null);
    setIsUploading(false);
  }, []);

  return {
    uploadToS3,
    uploadMultiple,
    isUploading,
    progress,
    error,
    reset,
  };
}
