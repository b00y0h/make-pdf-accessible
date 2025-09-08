"""DynamoDB repository pattern with type hints and comprehensive error handling."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Generic, TypeVar

import boto3
from aws_lambda_powertools import Logger, Tracer
from botocore.exceptions import ClientError

from pdf_worker.core.config import config
from pdf_worker.core.exceptions import DynamoDBError, WorkerConfigError

logger = Logger()
tracer = Tracer()

T = TypeVar('T')


class DynamoDBRepository(Generic[T]):
    """Generic DynamoDB repository with CRUD operations and query support."""

    def __init__(
        self,
        table_name: str,
        region_name: str | None = None,
        primary_key: str = 'id'
    ) -> None:
        """Initialize DynamoDB repository.
        
        Args:
            table_name: DynamoDB table name
            region_name: AWS region name. Defaults to config.aws_region
            primary_key: Primary key attribute name
        """
        try:
            self.table_name = table_name
            self.primary_key = primary_key

            self._dynamodb = boto3.resource(
                'dynamodb',
                region_name=region_name or config.aws_region
            )
            self._table = self._dynamodb.Table(table_name)

        except Exception as e:
            raise WorkerConfigError(f"Failed to initialize DynamoDB client: {e}")

        logger.info(f"Initialized DynamoDB repository for table: {table_name}")

    @tracer.capture_method
    def get_item(self, key: str | dict[str, Any]) -> dict[str, Any] | None:
        """Get item by primary key.
        
        Args:
            key: Primary key value or composite key dictionary
            
        Returns:
            Item data if found, None otherwise
            
        Raises:
            DynamoDBError: If get operation fails
        """
        try:
            # Handle simple or composite keys
            if isinstance(key, str):
                key_dict = {self.primary_key: key}
            else:
                key_dict = key

            response = self._table.get_item(Key=key_dict)
            item = response.get('Item')

            if item:
                logger.debug(f"Retrieved item with key {key_dict} from {self.table_name}")
                return self._deserialize_item(item)

            return None

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            raise DynamoDBError(
                f"Failed to get item from DynamoDB: {error_code}",
                table=self.table_name,
                operation="get_item"
            ) from e

    @tracer.capture_method
    def put_item(
        self,
        item: dict[str, Any],
        condition_expression: str | None = None
    ) -> dict[str, Any]:
        """Put item into table.
        
        Args:
            item: Item data to store
            condition_expression: Optional condition for put operation
            
        Returns:
            The stored item data
            
        Raises:
            DynamoDBError: If put operation fails
        """
        try:
            # Add timestamp metadata
            now = datetime.utcnow().isoformat()
            item_with_metadata = {
                **item,
                'updatedAt': now
            }

            # Add createdAt if not exists
            if 'createdAt' not in item_with_metadata:
                item_with_metadata['createdAt'] = now

            # Serialize the item
            serialized_item = self._serialize_item(item_with_metadata)

            put_kwargs = {'Item': serialized_item}
            if condition_expression:
                put_kwargs['ConditionExpression'] = condition_expression

            self._table.put_item(**put_kwargs)

            logger.info(f"Successfully put item to {self.table_name}")
            return item_with_metadata

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')

            # Handle conditional check failures
            if error_code == 'ConditionalCheckFailedException':
                raise DynamoDBError(
                    "Conditional check failed for put operation",
                    table=self.table_name,
                    operation="put_item"
                ) from e

            raise DynamoDBError(
                f"Failed to put item to DynamoDB: {error_code}",
                table=self.table_name,
                operation="put_item"
            ) from e

    @tracer.capture_method
    def update_item(
        self,
        key: str | dict[str, Any],
        update_expression: str,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        condition_expression: str | None = None
    ) -> dict[str, Any]:
        """Update item in table.
        
        Args:
            key: Primary key value or composite key dictionary
            update_expression: DynamoDB update expression
            expression_attribute_names: Attribute name mappings
            expression_attribute_values: Attribute value mappings
            condition_expression: Optional condition for update
            
        Returns:
            Updated item attributes
            
        Raises:
            DynamoDBError: If update operation fails
        """
        try:
            # Handle simple or composite keys
            if isinstance(key, str):
                key_dict = {self.primary_key: key}
            else:
                key_dict = key

            update_kwargs = {
                'Key': key_dict,
                'UpdateExpression': update_expression,
                'ReturnValues': 'ALL_NEW'
            }

            if expression_attribute_names:
                update_kwargs['ExpressionAttributeNames'] = expression_attribute_names

            if expression_attribute_values:
                # Serialize values
                update_kwargs['ExpressionAttributeValues'] = self._serialize_item(
                    expression_attribute_values
                )

            if condition_expression:
                update_kwargs['ConditionExpression'] = condition_expression

            response = self._table.update_item(**update_kwargs)

            updated_item = self._deserialize_item(response['Attributes'])
            logger.info(f"Successfully updated item in {self.table_name}")

            return updated_item

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')

            if error_code == 'ConditionalCheckFailedException':
                raise DynamoDBError(
                    "Conditional check failed for update operation",
                    table=self.table_name,
                    operation="update_item"
                ) from e

            raise DynamoDBError(
                f"Failed to update item in DynamoDB: {error_code}",
                table=self.table_name,
                operation="update_item"
            ) from e

    @tracer.capture_method
    def delete_item(
        self,
        key: str | dict[str, Any],
        condition_expression: str | None = None
    ) -> dict[str, Any] | None:
        """Delete item from table.
        
        Args:
            key: Primary key value or composite key dictionary
            condition_expression: Optional condition for delete
            
        Returns:
            Deleted item attributes if ReturnValues was set
            
        Raises:
            DynamoDBError: If delete operation fails
        """
        try:
            # Handle simple or composite keys
            if isinstance(key, str):
                key_dict = {self.primary_key: key}
            else:
                key_dict = key

            delete_kwargs = {
                'Key': key_dict,
                'ReturnValues': 'ALL_OLD'
            }

            if condition_expression:
                delete_kwargs['ConditionExpression'] = condition_expression

            response = self._table.delete_item(**delete_kwargs)

            deleted_item = response.get('Attributes')
            if deleted_item:
                deleted_item = self._deserialize_item(deleted_item)
                logger.info(f"Successfully deleted item from {self.table_name}")

            return deleted_item

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')

            if error_code == 'ConditionalCheckFailedException':
                raise DynamoDBError(
                    "Conditional check failed for delete operation",
                    table=self.table_name,
                    operation="delete_item"
                ) from e

            raise DynamoDBError(
                f"Failed to delete item from DynamoDB: {error_code}",
                table=self.table_name,
                operation="delete_item"
            ) from e

    @tracer.capture_method
    def query(
        self,
        key_condition_expression: str,
        filter_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        index_name: str | None = None,
        limit: int | None = None,
        scan_index_forward: bool = True
    ) -> list[dict[str, Any]]:
        """Query items from table.
        
        Args:
            key_condition_expression: Key condition for query
            filter_expression: Optional filter expression
            expression_attribute_names: Attribute name mappings
            expression_attribute_values: Attribute value mappings
            index_name: Global secondary index name
            limit: Maximum number of items to return
            scan_index_forward: Sort order for results
            
        Returns:
            List of matching items
            
        Raises:
            DynamoDBError: If query operation fails
        """
        try:
            query_kwargs = {
                'KeyConditionExpression': key_condition_expression,
                'ScanIndexForward': scan_index_forward
            }

            if filter_expression:
                query_kwargs['FilterExpression'] = filter_expression

            if expression_attribute_names:
                query_kwargs['ExpressionAttributeNames'] = expression_attribute_names

            if expression_attribute_values:
                query_kwargs['ExpressionAttributeValues'] = self._serialize_item(
                    expression_attribute_values
                )

            if index_name:
                query_kwargs['IndexName'] = index_name

            if limit:
                query_kwargs['Limit'] = limit

            response = self._table.query(**query_kwargs)

            items = [self._deserialize_item(item) for item in response.get('Items', [])]
            logger.info(f"Query returned {len(items)} items from {self.table_name}")

            return items

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            raise DynamoDBError(
                f"Failed to query DynamoDB table: {error_code}",
                table=self.table_name,
                operation="query"
            ) from e

    @tracer.capture_method
    def scan(
        self,
        filter_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        index_name: str | None = None,
        limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Scan all items from table.
        
        Args:
            filter_expression: Optional filter expression
            expression_attribute_names: Attribute name mappings
            expression_attribute_values: Attribute value mappings
            index_name: Global secondary index name
            limit: Maximum number of items to return
            
        Returns:
            List of matching items
            
        Raises:
            DynamoDBError: If scan operation fails
        """
        try:
            scan_kwargs = {}

            if filter_expression:
                scan_kwargs['FilterExpression'] = filter_expression

            if expression_attribute_names:
                scan_kwargs['ExpressionAttributeNames'] = expression_attribute_names

            if expression_attribute_values:
                scan_kwargs['ExpressionAttributeValues'] = self._serialize_item(
                    expression_attribute_values
                )

            if index_name:
                scan_kwargs['IndexName'] = index_name

            if limit:
                scan_kwargs['Limit'] = limit

            response = self._table.scan(**scan_kwargs)

            items = [self._deserialize_item(item) for item in response.get('Items', [])]
            logger.info(f"Scan returned {len(items)} items from {self.table_name}")

            return items

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            raise DynamoDBError(
                f"Failed to scan DynamoDB table: {error_code}",
                table=self.table_name,
                operation="scan"
            ) from e

    @tracer.capture_method
    def batch_get_items(self, keys: list[str | dict[str, Any]]) -> list[dict[str, Any]]:
        """Get multiple items by keys.
        
        Args:
            keys: List of primary keys or composite key dictionaries
            
        Returns:
            List of retrieved items
            
        Raises:
            DynamoDBError: If batch get operation fails
        """
        try:
            # Convert keys to proper format
            key_dicts = []
            for key in keys:
                if isinstance(key, str):
                    key_dicts.append({self.primary_key: key})
                else:
                    key_dicts.append(key)

            response = self._dynamodb.batch_get_item(
                RequestItems={
                    self.table_name: {
                        'Keys': key_dicts
                    }
                }
            )

            items = response.get('Responses', {}).get(self.table_name, [])
            deserialized_items = [self._deserialize_item(item) for item in items]

            logger.info(f"Batch get returned {len(deserialized_items)} items from {self.table_name}")
            return deserialized_items

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            raise DynamoDBError(
                f"Failed to batch get items from DynamoDB: {error_code}",
                table=self.table_name,
                operation="batch_get_item"
            ) from e

    def _serialize_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """Serialize Python types to DynamoDB-compatible types."""
        serialized = {}

        for key, value in item.items():
            if isinstance(value, float):
                # Convert float to Decimal for DynamoDB
                serialized[key] = Decimal(str(value))
            elif isinstance(value, dict):
                # Recursively serialize nested dictionaries
                serialized[key] = self._serialize_item(value)
            elif isinstance(value, list):
                # Serialize list items
                serialized[key] = [
                    self._serialize_item(v) if isinstance(v, dict) else
                    Decimal(str(v)) if isinstance(v, float) else v
                    for v in value
                ]
            else:
                serialized[key] = value

        return serialized

    def _deserialize_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """Deserialize DynamoDB types to Python types."""
        deserialized = {}

        for key, value in item.items():
            if isinstance(value, Decimal):
                # Convert Decimal back to float/int
                if value % 1 == 0:
                    deserialized[key] = int(value)
                else:
                    deserialized[key] = float(value)
            elif isinstance(value, dict):
                # Recursively deserialize nested dictionaries
                deserialized[key] = self._deserialize_item(value)
            elif isinstance(value, list):
                # Deserialize list items
                deserialized[key] = [
                    self._deserialize_item(v) if isinstance(v, dict) else
                    int(v) if isinstance(v, Decimal) and v % 1 == 0 else
                    float(v) if isinstance(v, Decimal) else v
                    for v in value
                ]
            else:
                deserialized[key] = value

        return deserialized


class DocumentRepository(DynamoDBRepository[dict[str, Any]]):
    """Specialized repository for document records."""

    def __init__(self) -> None:
        if not config.documents_table:
            raise WorkerConfigError("DOCUMENTS_TABLE environment variable not set")

        super().__init__(
            table_name=config.documents_table,
            primary_key='docId'
        )

    def get_document(self, doc_id: str) -> dict[str, Any] | None:
        """Get document by ID."""
        return self.get_item(doc_id)

    def create_document(self, doc_data: dict[str, Any]) -> dict[str, Any]:
        """Create new document record."""
        return self.put_item(doc_data)

    def update_document_status(
        self,
        doc_id: str,
        status: str,
        additional_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Update document status and optional additional data."""
        update_expression = "SET #status = :status, #updatedAt = :updatedAt"
        expression_attribute_names = {
            '#status': 'status',
            '#updatedAt': 'updatedAt'
        }
        expression_attribute_values = {
            ':status': status,
            ':updatedAt': datetime.utcnow().isoformat()
        }

        if additional_data:
            for i, (key, value) in enumerate(additional_data.items()):
                attr_name = f'#attr{i}'
                attr_value = f':val{i}'
                update_expression += f", {attr_name} = {attr_value}"
                expression_attribute_names[attr_name] = key
                expression_attribute_values[attr_value] = value

        return self.update_item(
            key=doc_id,
            update_expression=update_expression,
            expression_attribute_names=expression_attribute_names,
            expression_attribute_values=expression_attribute_values
        )


class JobRepository(DynamoDBRepository[dict[str, Any]]):
    """Specialized repository for job records."""

    def __init__(self) -> None:
        if not config.jobs_table:
            raise WorkerConfigError("JOBS_TABLE environment variable not set")

        super().__init__(
            table_name=config.jobs_table,
            primary_key='jobId'
        )

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Get job by ID."""
        return self.get_item(job_id)

    def create_job(self, job_data: dict[str, Any]) -> dict[str, Any]:
        """Create new job record."""
        return self.put_item(job_data)

    def get_jobs_by_doc_id(self, doc_id: str) -> list[dict[str, Any]]:
        """Get all jobs for a document."""
        return self.query(
            key_condition_expression='docId = :doc_id',
            expression_attribute_values={':doc_id': doc_id},
            index_name='docId-index'  # Assumes GSI exists
        )
