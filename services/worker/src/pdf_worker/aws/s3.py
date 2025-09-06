"""S3 client utilities with comprehensive error handling and type hints."""

import json
from typing import Optional, Dict, Any, BinaryIO, Union, List, Tuple
from pathlib import Path
from datetime import datetime
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.metrics import MetricUnit

from pdf_worker.core.config import config
from pdf_worker.core.exceptions import S3Error, WorkerConfigError

logger = Logger()
tracer = Tracer()


class S3Client:
    """Enhanced S3 client with PDF accessibility processing optimizations."""
    
    def __init__(self, region_name: Optional[str] = None) -> None:
        """Initialize S3 client.
        
        Args:
            region_name: AWS region name. Defaults to config.aws_region.
        """
        try:
            self._client = boto3.client('s3', region_name=region_name or config.aws_region)
            self._resource = boto3.resource('s3', region_name=region_name or config.aws_region)
        except NoCredentialsError as e:
            raise WorkerConfigError(f"AWS credentials not configured: {e}")
        
        logger.info(f"Initialized S3 client for region: {region_name or config.aws_region}")
    
    @tracer.capture_method
    def upload_file(
        self,
        file_path: Union[str, Path],
        bucket: str,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """Upload a file to S3 with enhanced metadata.
        
        Args:
            file_path: Local file path to upload
            bucket: S3 bucket name
            key: S3 object key
            content_type: MIME type of the file
            metadata: Custom metadata to attach
            tags: Object tags to apply
            
        Returns:
            S3 URI of the uploaded object
            
        Raises:
            S3Error: If upload fails
        """
        try:
            extra_args = {}
            
            if content_type:
                extra_args['ContentType'] = content_type
                
            if metadata:
                extra_args['Metadata'] = metadata
                
            # Add default metadata
            default_metadata = {
                'uploaded_by': 'pdf-accessibility-worker',
                'upload_timestamp': datetime.utcnow().isoformat()
            }
            extra_args.setdefault('Metadata', {}).update(default_metadata)
            
            self._client.upload_file(str(file_path), bucket, key, ExtraArgs=extra_args)
            
            # Apply tags if provided
            if tags:
                self._apply_tags(bucket, key, tags)
            
            s3_uri = f"s3://{bucket}/{key}"
            logger.info(f"Successfully uploaded {file_path} to {s3_uri}")
            
            return s3_uri
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            raise S3Error(
                f"Failed to upload file to S3: {error_code}", 
                bucket=bucket, 
                key=key
            ) from e
    
    @tracer.capture_method
    def upload_bytes(
        self,
        data: bytes,
        bucket: str,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """Upload bytes data to S3.
        
        Args:
            data: Bytes data to upload
            bucket: S3 bucket name
            key: S3 object key
            content_type: MIME type of the content
            metadata: Custom metadata to attach
            tags: Object tags to apply
            
        Returns:
            S3 URI of the uploaded object
        """
        try:
            extra_args = {}
            
            if content_type:
                extra_args['ContentType'] = content_type
                
            if metadata:
                extra_args['Metadata'] = metadata
            
            # Add default metadata
            default_metadata = {
                'uploaded_by': 'pdf-accessibility-worker',
                'upload_timestamp': datetime.utcnow().isoformat(),
                'content_length': str(len(data))
            }
            extra_args.setdefault('Metadata', {}).update(default_metadata)
            
            self._client.put_object(
                Bucket=bucket,
                Key=key,
                Body=data,
                **extra_args
            )
            
            # Apply tags if provided
            if tags:
                self._apply_tags(bucket, key, tags)
            
            s3_uri = f"s3://{bucket}/{key}"
            logger.info(f"Successfully uploaded {len(data)} bytes to {s3_uri}")
            
            return s3_uri
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            raise S3Error(
                f"Failed to upload bytes to S3: {error_code}",
                bucket=bucket,
                key=key
            ) from e
    
    @tracer.capture_method
    def upload_json(
        self,
        data: Dict[str, Any],
        bucket: str,
        key: str,
        indent: int = 2,
        metadata: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """Upload JSON data to S3.
        
        Args:
            data: Dictionary to serialize as JSON
            bucket: S3 bucket name
            key: S3 object key
            indent: JSON indentation for pretty printing
            metadata: Custom metadata to attach
            tags: Object tags to apply
            
        Returns:
            S3 URI of the uploaded object
        """
        json_bytes = json.dumps(data, indent=indent, ensure_ascii=False).encode('utf-8')
        
        # Add JSON-specific metadata
        json_metadata = {
            'data_type': 'json',
            'records_count': str(len(data.get('elements', [])) if 'elements' in data else 0)
        }
        if metadata:
            json_metadata.update(metadata)
        
        return self.upload_bytes(
            data=json_bytes,
            bucket=bucket,
            key=key,
            content_type='application/json',
            metadata=json_metadata,
            tags=tags
        )
    
    @tracer.capture_method
    def download_file(
        self,
        bucket: str,
        key: str,
        local_path: Union[str, Path]
    ) -> Path:
        """Download S3 object to local file.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            local_path: Local file path to save to
            
        Returns:
            Path to the downloaded file
            
        Raises:
            S3Error: If download fails
        """
        try:
            local_file = Path(local_path)
            local_file.parent.mkdir(parents=True, exist_ok=True)
            
            self._client.download_file(bucket, key, str(local_file))
            
            logger.info(f"Successfully downloaded s3://{bucket}/{key} to {local_file}")
            return local_file
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'NoSuchKey':
                raise S3Error(f"Object not found: s3://{bucket}/{key}", bucket=bucket, key=key)
            
            raise S3Error(
                f"Failed to download from S3: {error_code}",
                bucket=bucket,
                key=key
            ) from e
    
    @tracer.capture_method
    def download_bytes(self, bucket: str, key: str) -> bytes:
        """Download S3 object as bytes.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            
        Returns:
            Object content as bytes
            
        Raises:
            S3Error: If download fails
        """
        try:
            response = self._client.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read()
            
            logger.info(f"Successfully downloaded {len(content)} bytes from s3://{bucket}/{key}")
            return content
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'NoSuchKey':
                raise S3Error(f"Object not found: s3://{bucket}/{key}", bucket=bucket, key=key)
            
            raise S3Error(
                f"Failed to download from S3: {error_code}",
                bucket=bucket,
                key=key
            ) from e
    
    @tracer.capture_method
    def download_json(self, bucket: str, key: str) -> Dict[str, Any]:
        """Download and parse JSON object from S3.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            
        Returns:
            Parsed JSON data as dictionary
            
        Raises:
            S3Error: If download or JSON parsing fails
        """
        try:
            content = self.download_bytes(bucket, key)
            return json.loads(content.decode('utf-8'))
            
        except json.JSONDecodeError as e:
            raise S3Error(
                f"Failed to parse JSON from S3 object: {e}",
                bucket=bucket,
                key=key
            ) from e
    
    @tracer.capture_method
    def object_exists(self, bucket: str, key: str) -> bool:
        """Check if S3 object exists.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            
        Returns:
            True if object exists, False otherwise
        """
        try:
            self._client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError as e:
            if e.response.get('Error', {}).get('Code') == '404':
                return False
            raise S3Error(
                f"Failed to check object existence: {e}",
                bucket=bucket,
                key=key
            ) from e
    
    @tracer.capture_method
    def get_object_metadata(self, bucket: str, key: str) -> Dict[str, Any]:
        """Get S3 object metadata.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            
        Returns:
            Object metadata including size, last modified, etc.
            
        Raises:
            S3Error: If metadata retrieval fails
        """
        try:
            response = self._client.head_object(Bucket=bucket, Key=key)
            
            return {
                'size': response.get('ContentLength', 0),
                'last_modified': response.get('LastModified'),
                'content_type': response.get('ContentType'),
                'etag': response.get('ETag', '').strip('"'),
                'metadata': response.get('Metadata', {}),
                'storage_class': response.get('StorageClass', 'STANDARD')
            }
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == '404':
                raise S3Error(f"Object not found: s3://{bucket}/{key}", bucket=bucket, key=key)
            
            raise S3Error(
                f"Failed to get object metadata: {error_code}",
                bucket=bucket,
                key=key
            ) from e
    
    @tracer.capture_method
    def copy_object(
        self,
        source_bucket: str,
        source_key: str,
        dest_bucket: str,
        dest_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """Copy S3 object to another location.
        
        Args:
            source_bucket: Source bucket name
            source_key: Source object key
            dest_bucket: Destination bucket name
            dest_key: Destination object key
            metadata: Additional metadata for destination object
            
        Returns:
            S3 URI of the copied object
        """
        try:
            copy_source = {'Bucket': source_bucket, 'Key': source_key}
            extra_args = {}
            
            if metadata:
                extra_args['Metadata'] = metadata
                extra_args['MetadataDirective'] = 'REPLACE'
            
            self._client.copy_object(
                CopySource=copy_source,
                Bucket=dest_bucket,
                Key=dest_key,
                **extra_args
            )
            
            dest_uri = f"s3://{dest_bucket}/{dest_key}"
            logger.info(f"Successfully copied s3://{source_bucket}/{source_key} to {dest_uri}")
            
            return dest_uri
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            raise S3Error(f"Failed to copy S3 object: {error_code}") from e
    
    @tracer.capture_method
    def delete_object(self, bucket: str, key: str) -> None:
        """Delete S3 object.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
        """
        try:
            self._client.delete_object(Bucket=bucket, Key=key)
            logger.info(f"Successfully deleted s3://{bucket}/{key}")
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            # Don't raise error if object doesn't exist
            if error_code != 'NoSuchKey':
                raise S3Error(
                    f"Failed to delete S3 object: {error_code}",
                    bucket=bucket,
                    key=key
                ) from e
    
    @tracer.capture_method
    def list_objects(
        self,
        bucket: str,
        prefix: str = "",
        max_keys: int = 1000
    ) -> List[Dict[str, Any]]:
        """List objects in S3 bucket with prefix.
        
        Args:
            bucket: S3 bucket name
            prefix: Object key prefix to filter by
            max_keys: Maximum number of keys to return
            
        Returns:
            List of object information dictionaries
        """
        try:
            response = self._client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            objects = []
            for obj in response.get('Contents', []):
                objects.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj['ETag'].strip('"'),
                    'storage_class': obj.get('StorageClass', 'STANDARD')
                })
            
            logger.info(f"Listed {len(objects)} objects from s3://{bucket}/{prefix}")
            return objects
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            raise S3Error(
                f"Failed to list S3 objects: {error_code}",
                bucket=bucket,
                key=prefix
            ) from e
    
    def _apply_tags(self, bucket: str, key: str, tags: Dict[str, str]) -> None:
        """Apply tags to S3 object."""
        try:
            tag_set = [{'Key': k, 'Value': v} for k, v in tags.items()]
            self._client.put_object_tagging(
                Bucket=bucket,
                Key=key,
                Tagging={'TagSet': tag_set}
            )
            logger.debug(f"Applied {len(tags)} tags to s3://{bucket}/{key}")
            
        except ClientError as e:
            # Log warning but don't fail the operation
            logger.warning(f"Failed to apply tags to s3://{bucket}/{key}: {e}")
    
    def generate_presigned_url(
        self,
        bucket: str,
        key: str,
        expiration: int = 3600,
        method: str = 'get_object'
    ) -> str:
        """Generate presigned URL for S3 object.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            expiration: URL expiration time in seconds
            method: S3 operation method
            
        Returns:
            Presigned URL string
        """
        try:
            url = self._client.generate_presigned_url(
                method,
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expiration
            )
            logger.debug(f"Generated presigned URL for s3://{bucket}/{key}")
            return url
            
        except ClientError as e:
            raise S3Error(f"Failed to generate presigned URL: {e}") from e