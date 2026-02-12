# System Architecture

## High-Level Overview

PDF accessibility processing system built as a microservices monorepo. The system processes PDF documents through a pipeline of specialized services to add accessibility features.

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Applications                      │
│              (Web UI, WordPress, LTI, HTML)                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway (8000)                        │
│              Authentication, Routing, Rate Limiting          │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    Redis     │     │  PostgreSQL  │     │   MongoDB    │
│  Queue/Cache │     │  User Data   │     │  Documents   │
└──────────────┘     └──────────────┘     └──────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│                 Processing Functions                         │
├──────────┬──────────┬──────────┬──────────┬────────────────┤
│ Router   │   OCR    │Structure │  Tagger  │   Exporter     │
│  8001    │   8002   │   8003   │   8004   │     8005       │
├──────────┴──────────┴──────────┴──────────┴────────────────┤
│              Validator (8006) │ Notifier (8007)            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      S3 Storage                              │
│        uploads / processed / reports buckets                 │
└─────────────────────────────────────────────────────────────┘
```

## Microservices Breakdown

### API Gateway (services/api/)
- Main entry point at port 8000
- Authentication and authorization
- Request routing and validation
- Rate limiting and quota enforcement
- User and document management APIs

### Processing Functions (services/functions/)

| Service   | Port | Responsibility |
|-----------|------|----------------|
| Router    | 8001 | Orchestrates processing pipeline, routes to appropriate services |
| OCR       | 8002 | Optical character recognition for scanned content |
| Structure | 8003 | Document structure analysis (headings, lists, tables) |
| Tagger    | 8004 | PDF tag tree generation for accessibility |
| Exporter  | 8005 | Final PDF export with accessibility features |
| Validator | 8006 | Accessibility compliance validation |
| Notifier  | 8007 | Webhook and notification delivery |

### Worker Service (services/worker/)
- Celery-based background processing
- Long-running task execution
- Timeout monitoring

### Web Application (web/)
- Next.js frontend at port 3000
- User interface for document upload and management
- Real-time processing status

## Data Flow

1. **Upload**: Client → API Gateway → S3 (uploads bucket)
2. **Queue**: API Gateway → SQS/Redis → Worker
3. **Process**: Worker → Router → [OCR → Structure → Tagger → Exporter]
4. **Validate**: Exporter → Validator → S3 (processed bucket)
5. **Notify**: Validator → Notifier → Client webhook

## Key Design Decisions

### Async-First Processing
- All PDF processing is async via Celery/SQS
- Webhooks for completion notification
- Supports both standard and priority queues

### Service Isolation
- Each function runs independently
- Docker containers with identical patterns
- Horizontal scaling per service

### LocalStack for Development
- Full AWS stack simulation locally
- S3, SQS, SNS, Step Functions
- Consistent dev/prod parity

### Shared Code Strategy
- `services/shared/` for common utilities
- `packages/schemas/` for cross-service types
- Consistent auth and persistence patterns
