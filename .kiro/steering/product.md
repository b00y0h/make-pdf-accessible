# Product Overview

Make PDF Accessible is a comprehensive platform that transforms PDF documents into accessible formats, ensuring WCAG compliance and improving document usability for users with disabilities.

## Core Functionality

- **PDF Processing**: Extract text, images, and structure from PDF documents
- **Accessibility Analysis**: Validate documents against WCAG guidelines
- **Format Conversion**: Export to accessible formats (HTML, EPUB, etc.)
- **Content Enhancement**: Add semantic structure, alt text, and metadata
- **Integration Support**: WordPress plugins and LTI integration for learning management systems

## Key Services

- **OCR Processing**: Extract text from scanned documents and images
- **Structure Analysis**: Identify headings, lists, tables, and document hierarchy
- **Content Tagging**: Classify and categorize document content
- **Accessibility Validation**: Check compliance with accessibility standards
- **Export Engine**: Convert to multiple accessible formats
- **Notification System**: Alert users about processing status and results

## AI-Ready Document Optimization

Beyond accessibility, Make PDF Accessible transforms PDFs into structured, machine-readable formats designed for **large language models (LLMs)** and AI agents. This ensures that institutional knowledge is not only compliant, but also **discoverable, retrievable, and cite-ready** for AI use cases.

### Features

- **Semantic JSON & Markdown Exports**  
  Generate structured JSON and clean Markdown versions of each document, preserving headings, tables, figures, and equations.

- **RAG-Optimized Chunking**  
  Documents are split into stable, citation-ready text chunks (`chunks.jsonl`) with metadata (page spans, citations, table links) for reliable retrieval.

- **Table, Equation, and Image Handling**  
  Tables exported to CSV, equations preserved in LaTeX, and images paired with concise alt text for multimodal understanding.

- **Embeddings & Search**  
  Integrate with vector search (OpenSearch, pgvector) using Bedrock embeddings, enabling hybrid BM25 + semantic search out-of-the-box.

- **AI Access Endpoints**  
  `/ai/search` and `/documents/{id}/ai` APIs return structured chunks, making integration with chatbots, knowledge assistants, or academic discovery portals straightforward.

### Consumption Options

- **One-off Uploads**  
  Users download an accessible PDF/UA, an HTML embed, and AI-ready JSON/Markdown exports.
- **API Integration**  
  Developers automate remediation and ingest AI-optimized artifacts directly into their systems.
- **CMS & LMS Plugins**  
  WordPress, Drupal, and Canvas plugins swap links automatically and expose AI-ready manifests via `<link rel="alternate">`.
- **LLM Integration**  
  AI assistants can crawl published manifests (`manifest.json`, `document.md`, `chunks.jsonl`) or call the `/ai/search` API to ground responses in authoritative sources.

## Target Users

- Content creators and publishers
- Educational institutions
- Government agencies
- Organizations requiring accessibility compliance
- Developers integrating accessibility tools
