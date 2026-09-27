# LLM Integration Guide - AccessPDF Discovery System

> **Status: disabled.** The `/public/embeddings/*` endpoints described below are no longer mounted in the API (`services/api/app/main.py`). They had no authentication and the rate limiter allowed every request, so any caller could trigger paid Bedrock calls. The code remains in `services/api/app/routes/embeddings.py`. The WordPress plugin and HTML snippets still reference these URLs and will get 404s until they are updated.

This guide explains how Large Language Models (LLMs) like ChatGPT, Claude, and Gemini can discover and search accessible documents processed by AccessPDF.

## 🎯 Architecture Overview

**Client Sites** → Add simple metadata tags  
**LLMs Crawl** → Discover AccessPDF documents via metadata  
**LLMs Query** → Your centralized API for search/content  
**Clients Get** → Zero infrastructure, maximum discoverability  

## 🏛️ Government Agency Flow

### 1. Agency Uploads PDF
```bash
curl -X POST "https://api.accesspdf.com/v1/client/upload" \
  -H "Authorization: Bearer agency_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "file_url": "https://agency.gov/reports/annual-report.pdf",
    "filename": "annual-report-2024.pdf",
    "client_metadata": {
      "site_url": "https://agency.gov",
      "site_name": "Department of Education",
      "department": "Accessibility Office",
      "contact": "accessibility@agency.gov"
    },
    "callback_url": "https://agency.gov/webhook/accesspdf",
    "public_discovery": true
  }'
```

**Response:**
```json
{
  "accesspdf_id": "abc-123-def",
  "status": "processing",
  "estimated_completion": "2-5 minutes",
  "discovery_endpoints": {
    "search_api": "/public/embeddings/search?doc_ids=abc-123-def",
    "direct_access": "/public/embeddings/documents/abc-123-def"
  }
}
```

### 2. Agency Updates Their Website
```html
<!-- On agency.gov/reports/annual-report -->
<a href="/annual-report.pdf" 
   data-accesspdf-id="abc-123-def"
   data-accessibility-api="https://api.accesspdf.com">
   Annual Report 2024 (PDF)
</a>

<!-- Structured data for LLM discovery -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "GovernmentDocument",
  "name": "Annual Accessibility Report 2024",
  "publisher": "Department of Education",
  "encodingFormat": "application/pdf",
  "accessibilityFeature": ["structuralNavigation", "alternativeText"],
  "accessibilityAPI": "https://api.accesspdf.com/public/embeddings/documents/abc-123-def"
}
</script>
```

## 🎓 University WordPress Integration

### 1. Install Plugin
```bash
# Upload accesspdf-plugin.php to /wp-content/plugins/
# Activate in WordPress admin
# Configure API key in Settings → AccessPDF
```

### 2. Plugin Auto-Processing
```php
// When university uploads PDF to WordPress:
1. Plugin detects PDF upload
2. Sends to AccessPDF API automatically
3. Gets back AccessPDF ID (abc-123-def)
4. Adds metadata to WordPress attachment
5. Enhances all PDF links automatically
```

### 3. Enhanced PDF Links
```html
<!-- WordPress automatically generates -->
<a href="/wp-content/uploads/research-paper.pdf"
   data-accesspdf-id="abc-123-def"
   data-accessibility-api="https://api.accesspdf.com"
   data-accessible-formats="html,text,embeddings">
   Research Paper PDF
   <span class="accesspdf-badge">🤖 AI Searchable</span>
</a>
```

## 🤖 LLM Discovery Process

### 1. LLM Crawls Client Site
```
ChatGPT crawls → university.edu/research-papers
Finds → <a data-accesspdf-id="abc-123-def" ...>
Extracts → AccessPDF ID and API endpoint
```

### 2. LLM Queries Your API
```bash
# LLM makes request to YOUR service
GET https://api.accesspdf.com/public/embeddings/documents/abc-123-def
Authorization: Bearer chatgpt_api_key

# Your API responds with document info
{
  "document_info": {
    "title": "Climate Research Paper 2024",
    "author": "Dr. Jane Smith", 
    "total_chunks": 247,
    "content_types": {"text": 180, "table": 15, "figure": 12}
  },
  "search_capabilities": {
    "semantic_search_available": true,
    "search_endpoint": "/public/embeddings/search?doc_ids=abc-123-def"
  },
  "client_info": {
    "organization": "State University",
    "website": "university.edu"
  }
}
```

### 3. LLM Searches Document
```bash
# LLM searches specific document content
POST https://api.accesspdf.com/public/embeddings/search
Authorization: Bearer chatgpt_api_key

{
  "query": "climate change impact on agriculture",
  "doc_ids": ["abc-123-def"],
  "limit": 5
}

# Gets semantic search results with citations
{
  "results": [
    {
      "content": "Agricultural impacts of climate change include...",
      "similarity_score": 0.89,
      "citation_info": {
        "source": "Climate Research Paper 2024",
        "author": "Dr. Jane Smith",
        "url": "https://university.edu/research/climate-paper.pdf"
      }
    }
  ]
}
```

## 🔍 Discovery Mechanisms for LLMs

### Option 1: HTML Metadata (Primary)
```html
<meta name="accesspdf-api" content="https://api.accesspdf.com/public/embeddings/search">
<meta name="accessible-documents" content="5">
<link rel="accessibility-api" href="https://api.accesspdf.com/public/embeddings/documents?client_domain=university.edu">
```

### Option 2: robots.txt Enhancement
```txt
# university.edu/robots.txt
User-agent: *
Sitemap: https://university.edu/sitemap.xml

# LLM discovery
Accessibility-API: https://api.accesspdf.com/public/embeddings/search
Documents-Endpoint: https://api.accesspdf.com/public/embeddings/documents?client_domain=university.edu
```

### Option 3: Well-Known Endpoint
```javascript
// university.edu/.well-known/accessibility-api
{
  "service_provider": "AccessPDF",
  "api_version": "1.0",
  "search_endpoint": "https://api.accesspdf.com/public/embeddings/search",
  "discovery_endpoint": "https://api.accesspdf.com/public/embeddings/documents?client_domain=university.edu",
  "supported_features": ["semantic_search", "pdf_ua_compliance", "wcag_aa"],
  "document_count": 47
}
```

## 🌐 Cross-Client Search (Advanced)

LLMs can also search across multiple client sites:

```bash
# Search all government documents
GET /public/embeddings/search?query=accessibility+compliance&client_type=government

# Search all university research
GET /public/embeddings/search?query=climate+change&client_type=education

# Search specific organization
GET /public/embeddings/search?query=policy&client_domain=agency.gov
```

## 📊 Benefits Summary

### For Clients (Universities, Agencies):
✅ **Zero Infrastructure** - Just add metadata tags  
✅ **Automatic Processing** - Plugin handles everything  
✅ **Maximum Discoverability** - LLMs find their content  
✅ **Compliance Ready** - WCAG/508/PDF-UA automatic  

### For LLMs:
✅ **Centralized API** - Single endpoint for all accessible documents  
✅ **Rich Metadata** - Full context and citations  
✅ **Semantic Search** - Vector embeddings for better results  
✅ **Structured Discovery** - Clear metadata standards  

### For You (AccessPDF):
✅ **Central Hub** - All LLM traffic flows through your API  
✅ **Rich Data** - Usage analytics across all clients  
✅ **Simple Architecture** - Clients just add metadata tags  
✅ **Scalable Business Model** - API usage-based revenue  

This approach makes YOUR service the central accessibility hub that LLMs discover and query, while keeping client integration dead simple! 🎯