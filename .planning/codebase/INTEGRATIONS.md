# External Integrations

## WordPress Plugin

**Location**: `integrations/wordpress/`

- PHP plugin (accesspdf-plugin.php v1.0.0)
- Hooks into PDF uploads via `wp_handle_upload` filter
- Adds accessibility metadata to PDF attachments
- JavaScript client (accesspdf-client.js) for LLM discovery badges
- API key-based authentication
- WordPress cron for async PDF processing
- Safe frontend configuration (no API keys exposed)

## HTML Snippets Integration

**Location**: `integrations/html-snippets/`

- JavaScript snippet for generic website integration
- Class-based `AccessPDFIntegration` for configurable deployment
- REST API endpoint: `POST /v1/client/upload`
- Bearer token authentication
- Client metadata tracking (site_url, page_url)
- Automatic PDF link enhancement with visual badges

## LTI Integration

**Location**: `integrations/lti/`

- Learning Management System integration
- Tests directory exists, implementation pending

## Message Queue Patterns

### SQS Queues
- `pdf-accessibility-ingest` - Standard processing queue
- `pdf-accessibility-priority` - Priority processing
- `pdf-accessibility-callbacks` - Webhook callbacks

### Queue Message Format
```json
{
  "documentId": "uuid",
  "webhookUrl": "https://callback.url",
  "metadata": { ... }
}
```

### Priority Routing
- `services.py` routes to priority vs standard processing
- Webhook callbacks for async processing completion

## Microservice Communication

### Port Assignments
| Service   | Port |
|-----------|------|
| API Gateway | 8000 |
| Router    | 8001 |
| OCR       | 8002 |
| Structure | 8003 |
| Tagger    | 8004 |
| Exporter  | 8005 |
| Validator | 8006 |
| Notifier  | 8007 |
| Web       | 3000 |

### Communication Patterns
- HTTP endpoints for synchronous requests
- Redis/SQS for async task distribution
- Step Functions for workflow orchestration

## Database Connections

### PostgreSQL
- Connection via `DATABASE_URL`
- SQLAlchemy ORM
- BetterAuth user data

### MongoDB
- Connection via `MONGODB_URI`
- Replica set configuration (rs0)
- Document and job storage

### Redis
- Connection via `REDIS_URL`
- Celery task broker
- Caching layer

## AWS API Gateway (Production)

- HTTP API with Cognito JWT authorization
- CORS configured for:
  - localhost:3000-3001 (development)
  - makepdfaccessible.com (production)

## S3 Buckets

- `pdf-accessibility-uploads` - Original uploads
- `pdf-accessibility-processed` - Processed PDFs
- `pdf-accessibility-reports` - Accessibility reports

## Authentication

- JWT tokens with Bearer authorization
- HS256 algorithm
- Cognito for production auth
- BetterAuth for session management
