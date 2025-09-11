/**
 * AccessPDF HTML Integration
 * Simple JavaScript snippet for any website to enable LLM discovery
 * 
 * Usage: Add this script to your website and configure your API key
 */

class AccessPDFIntegration {
    constructor(config = {}) {
        this.config = {
            apiBase: 'https://api.accesspdf.com',
            apiKey: config.apiKey || '',
            clientDomain: window.location.hostname,
            autoEnhance: config.autoEnhance !== false,
            showBadges: config.showBadges !== false,
            ...config
        };
        
        if (this.config.autoEnhance) {
            this.init();
        }
    }
    
    init() {
        // Wait for DOM ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.enhanceExistingPDFs());
        } else {
            this.enhanceExistingPDFs();
        }
    }
    
    /**
     * Enhance existing PDF links on the page
     */
    enhanceExistingPDFs() {
        const pdfLinks = document.querySelectorAll('a[href$=".pdf"]');
        
        pdfLinks.forEach(link => {
            const accesspdfId = link.dataset.accesspdfId;
            if (accesspdfId) {
                this.enhancePDFLink(link, accesspdfId);
            }
        });
        
        this.addPageMetadata();
        
        console.log(`AccessPDF: Enhanced ${pdfLinks.length} PDF links`);
    }
    
    /**
     * Process a new PDF upload and get AccessPDF ID
     */
    async processNewPDF(fileUrl, filename, metadata = {}) {
        if (!this.config.apiKey) {
            throw new Error('AccessPDF API key not configured');
        }
        
        try {
            const response = await fetch(`${this.config.apiBase}/v1/client/upload`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.config.apiKey}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    file_url: fileUrl,
                    filename: filename,
                    client_metadata: {
                        site_url: window.location.origin,
                        site_name: document.title,
                        page_url: window.location.href,
                        ...metadata
                    },
                    public_discovery: true
                })
            });
            
            if (!response.ok) {
                throw new Error(`API request failed: ${response.status}`);
            }
            
            const result = await response.json();
            return result.accesspdf_id;
            
        } catch (error) {
            console.error('AccessPDF processing failed:', error);
            throw error;
        }
    }
    
    /**
     * Enhance a PDF link with accessibility features
     */
    enhancePDFLink(link, accesspdfId) {
        // Add data attributes for LLM discovery
        link.dataset.accesspdfId = accesspdfId;
        link.dataset.accessibilityApi = this.config.apiBase;
        link.dataset.accessibleFormats = 'html,text,embeddings';
        
        // Add visual badge if enabled
        if (this.config.showBadges && !link.querySelector('.accesspdf-badge')) {
            const badge = document.createElement('span');
            badge.className = 'accesspdf-badge';
            badge.innerHTML = '🤖 AI Searchable';
            badge.style.cssText = `
                font-size: 0.75em;
                background: linear-gradient(45deg, #10b981, #059669);
                color: white;
                padding: 2px 8px;
                border-radius: 12px;
                margin-left: 8px;
                display: inline-flex;
                align-items: center;
                font-weight: 500;
            `;
            badge.title = 'This PDF is accessible and searchable by AI assistants';
            
            link.appendChild(badge);
        }
        
        // Add structured data for search engines
        this.addStructuredData(link, accesspdfId);
    }
    
    /**
     * Add structured data for a specific document
     */
    addStructuredData(link, accesspdfId) {
        const filename = link.textContent.trim();
        
        const structuredData = {
            '@context': 'https://schema.org',
            '@type': 'Document',
            'name': filename,
            'url': link.href,
            'encodingFormat': 'application/pdf',
            'accessibilityFeature': [
                'structuralNavigation',
                'alternativeText', 
                'highContrastDisplay'
            ],
            'accessibilityHazard': 'none',
            'accessMode': ['textual', 'visual'],
            'accessModeSufficient': 'textual',
            'accessibilityAPI': `${this.config.apiBase}/public/embeddings/documents/${accesspdfId}`,
            'provider': {
                '@type': 'Organization',
                'name': 'AccessPDF',
                'url': 'https://accesspdf.com'
            }
        };
        
        // Add to page
        const script = document.createElement('script');
        script.type = 'application/ld+json';
        script.textContent = JSON.stringify(structuredData);
        document.head.appendChild(script);
    }
    
    /**
     * Add page-level metadata for LLM crawlers
     */
    addPageMetadata() {
        const pdfCount = document.querySelectorAll('a[data-accesspdf-id]').length;
        
        if (pdfCount === 0) return;
        
        // Add meta tags
        const metaTags = [
            { name: 'accesspdf-api', content: `${this.config.apiBase}/public/embeddings/search` },
            { name: 'accessible-documents-count', content: pdfCount.toString() },
            { name: 'accessibility-compliance', content: 'wcag-aa,pdf-ua,section-508' }
        ];
        
        metaTags.forEach(tag => {
            if (!document.querySelector(`meta[name="${tag.name}"]`)) {
                const meta = document.createElement('meta');
                meta.name = tag.name;
                meta.content = tag.content;
                document.head.appendChild(meta);
            }
        });
        
        // Add discovery link for LLM crawlers
        const link = document.createElement('link');
        link.rel = 'accessibility-api';
        link.href = `${this.config.apiBase}/public/embeddings/documents?client_domain=${encodeURIComponent(this.config.clientDomain)}`;
        link.type = 'application/json';
        document.head.appendChild(link);
    }
    
    /**
     * Get status of AccessPDF processing
     */
    async getDocumentStatus(accesspdfId) {
        try {
            const response = await fetch(`${this.config.apiBase}/v1/client/status/${accesspdfId}`, {
                headers: {
                    'Authorization': `Bearer ${this.config.apiKey}`
                }
            });
            
            return await response.json();
            
        } catch (error) {
            console.error('Failed to get document status:', error);
            return null;
        }
    }
}

// Auto-initialize if config is provided
if (window.accesspdf_config) {
    window.AccessPDF = new AccessPDFIntegration(window.accesspdf_config);
}

// Export for manual initialization
window.AccessPDFIntegration = AccessPDFIntegration;

/**
 * Simple usage examples:
 */

// Example 1: Auto-enhance existing PDFs
window.accesspdf_config = {
    apiKey: 'your_api_key_here',
    showBadges: true
};

// Example 2: Process new PDF upload
// const accesspdf = new AccessPDFIntegration({apiKey: 'your_key'});
// const accesspdfId = await accesspdf.processNewPDF('https://mysite.com/document.pdf', 'document.pdf');
// accesspdf.enhancePDFLink(document.querySelector('#my-pdf-link'), accesspdfId);