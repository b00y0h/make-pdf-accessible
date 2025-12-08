/**
 * AccessPDF CDN Integration Script
 * https://cdn.accesspdf.com/integration.js
 *
 * This script enables any website to make their PDFs AI-discoverable
 * No API keys exposed - uses secure domain-based authentication
 */

(function () {
  'use strict';

  // Configuration
  const AccessPDF = {
    version: '1.0.0',
    apiBase: 'https://api.accesspdf.com',
    cdnBase: 'https://cdn.accesspdf.com',

    // Default configuration
    config: {
      integrationId: null, // Set by website owner
      domain: window.location.hostname,
      autoEnhance: true, // Automatically enhance PDF links
      showBadges: true, // Show "AI Searchable" badges
      trackAnalytics: true, // Track usage for improvements
      debugMode: false, // Enable console logging
    },

    // Initialize the integration
    init: function (userConfig = {}) {
      // Merge user config
      this.config = { ...this.config, ...userConfig };

      // Validate required config
      if (!this.config.integrationId) {
        console.warn(
          'AccessPDF: integrationId not provided. Some features may not work.'
        );
      }

      if (this.config.debugMode) {
        console.log('AccessPDF: Initializing with config', this.config);
      }

      // Start enhancement
      if (this.config.autoEnhance) {
        this.enhanceExistingPDFs();
      }

      // Add page metadata for LLM discovery
      this.addDiscoveryMetadata();

      // Setup mutation observer for dynamically added PDFs
      this.observeNewPDFs();

      return this;
    },

    // Enhance existing PDF links on the page
    enhanceExistingPDFs: function () {
      const pdfLinks = document.querySelectorAll(
        'a[href$=".pdf"], a[href*=".pdf?"], a[href*=".pdf#"]'
      );
      let enhancedCount = 0;

      pdfLinks.forEach((link) => {
        if (this.enhancePDFLink(link)) {
          enhancedCount++;
        }
      });

      if (this.config.debugMode) {
        console.log(`AccessPDF: Enhanced ${enhancedCount} PDF links`);
      }

      return enhancedCount;
    },

    // Enhance individual PDF link
    enhancePDFLink: function (link) {
      // Skip if already enhanced
      if (link.dataset.accesspdfEnhanced) {
        return false;
      }

      // Mark as enhanced
      link.dataset.accesspdfEnhanced = 'true';

      // Add discovery metadata
      const accesspdfId = link.dataset.accesspdfId;
      if (accesspdfId) {
        this.addLLMDiscoveryMetadata(link, accesspdfId);
      } else if (this.config.integrationId) {
        // Generate potential AccessPDF ID from URL
        const potentialId = this.generatePotentialId(link.href);
        this.addLLMDiscoveryMetadata(link, potentialId);
      }

      // Add visual enhancement
      if (this.config.showBadges) {
        this.addAccessibilityBadge(link);
      }

      // Add event listeners
      this.addInteractionHandlers(link);

      return true;
    },

    // Add LLM discovery metadata to link
    addLLMDiscoveryMetadata: function (link, accesspdfId) {
      // Core discovery attributes
      link.dataset.accesspdfId = accesspdfId;
      link.dataset.accessibilityApi = this.apiBase;
      link.dataset.accessibleFormats = 'html,text,embeddings';

      // Add structured data for this specific document
      this.addDocumentStructuredData(link, accesspdfId);
    },

    // Add visual accessibility badge
    addAccessibilityBadge: function (link) {
      if (link.querySelector('.accesspdf-badge')) {
        return; // Already has badge
      }

      const badge = document.createElement('span');
      badge.className = 'accesspdf-badge';
      badge.innerHTML = '🤖&nbsp;AI&nbsp;Searchable';
      badge.style.cssText = `
                font-size: 0.7em;
                background: linear-gradient(45deg, #059669, #10b981);
                color: white;
                padding: 3px 8px;
                border-radius: 12px;
                margin-left: 6px;
                display: inline-flex;
                align-items: center;
                font-weight: 500;
                box-shadow: 0 1px 3px rgba(0,0,0,0.3);
                cursor: help;
                transition: all 0.2s ease;
            `;
      badge.title =
        'This PDF has been processed for accessibility and is searchable by AI assistants like ChatGPT, Claude, and Gemini';

      // Hover effect
      badge.onmouseenter = () => {
        badge.style.transform = 'scale(1.05)';
        badge.style.boxShadow = '0 2px 6px rgba(0,0,0,0.4)';
      };
      badge.onmouseleave = () => {
        badge.style.transform = 'scale(1)';
        badge.style.boxShadow = '0 1px 3px rgba(0,0,0,0.3)';
      };

      // Add click handler for more info
      badge.onclick = (e) => {
        e.preventDefault();
        this.showAccessibilityInfo(link);
      };

      link.appendChild(badge);
    },

    // Add page-level metadata for LLM crawlers
    addDiscoveryMetadata: function () {
      const pdfCount = document.querySelectorAll('a[data-accesspdf-id]').length;

      // Add meta tags for LLM discovery
      const metaTags = [
        { name: 'accesspdf-integration-version', content: this.version },
        {
          name: 'accesspdf-api-endpoint',
          content: `${this.apiBase}/public/embeddings/search`,
        },
        { name: 'accessible-documents-count', content: pdfCount.toString() },
        {
          name: 'accessibility-compliance',
          content: 'wcag-2.1-aa,pdf-ua-1,section-508',
        },
        { name: 'ai-search-enabled', content: 'true' },
      ];

      metaTags.forEach(({ name, content }) => {
        if (!document.querySelector(`meta[name="${name}"]`)) {
          const meta = document.createElement('meta');
          meta.name = name;
          meta.content = content;
          document.head.appendChild(meta);
        }
      });

      // Add discovery link rel
      if (this.config.integrationId) {
        const discoveryLink = document.createElement('link');
        discoveryLink.rel = 'accessibility-api';
        discoveryLink.href = `${this.apiBase}/public/embeddings/documents?client_domain=${encodeURIComponent(this.config.domain)}`;
        discoveryLink.type = 'application/json';
        document.head.appendChild(discoveryLink);
      }
    },

    // Add structured data for individual document
    addDocumentStructuredData: function (link, accesspdfId) {
      const filename = this.extractFilename(link);

      const structuredData = {
        '@context': 'https://schema.org',
        '@type': 'Document',
        name: filename,
        url: link.href,
        encodingFormat: 'application/pdf',
        accessibilityFeature: [
          'structuralNavigation',
          'alternativeText',
          'highContrastDisplay',
          'readingOrder',
        ],
        accessibilityHazard: 'none',
        accessMode: ['textual', 'visual'],
        accessModeSufficient: 'textual',
        accessibilityAPI: `${this.apiBase}/public/embeddings/documents/${accesspdfId}`,
        provider: {
          '@type': 'Organization',
          name: 'AccessPDF',
          url: 'https://accesspdf.com',
        },
        dateModified: new Date().toISOString(),
        inLanguage: document.documentElement.lang || 'en',
      };

      // Add to page (only once per document)
      const existingScript = document.querySelector(
        `script[data-accesspdf-id="${accesspdfId}"]`
      );
      if (!existingScript) {
        const script = document.createElement('script');
        script.type = 'application/ld+json';
        script.dataset.accesspdfId = accesspdfId;
        script.textContent = JSON.stringify(structuredData, null, 2);
        document.head.appendChild(script);
      }
    },

    // Add interaction handlers
    addInteractionHandlers: function (link) {
      // Right-click context menu for accessibility options
      link.addEventListener('contextmenu', (e) => {
        if (e.altKey) {
          // Alt + right-click
          e.preventDefault();
          this.showAccessibilityMenu(e, link);
        }
      });

      // Keyboard shortcut (Alt + A when focused)
      link.addEventListener('keydown', (e) => {
        if (e.altKey && e.key.toLowerCase() === 'a') {
          e.preventDefault();
          this.showAccessibilityInfo(link);
        }
      });
    },

    // Show accessibility information modal
    showAccessibilityInfo: function (link) {
      const accesspdfId = link.dataset.accesspdfId;

      // Create info modal
      const modal = document.createElement('div');
      modal.style.cssText = `
                position: fixed;
                top: 0; left: 0; right: 0; bottom: 0;
                background: rgba(0,0,0,0.7);
                z-index: 10000;
                display: flex;
                align-items: center;
                justify-content: center;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            `;

      modal.innerHTML = `
                <div style="background: white; padding: 24px; border-radius: 12px; max-width: 500px; margin: 20px;">
                    <div style="display: flex; align-items: center; margin-bottom: 16px;">
                        <span style="font-size: 24px; margin-right: 8px;">🤖</span>
                        <h2 style="margin: 0; font-size: 18px; font-weight: 600;">AI-Enhanced Accessible Document</h2>
                    </div>
                    
                    <div style="margin-bottom: 20px; line-height: 1.5; color: #555;">
                        <p style="margin: 0 0 12px 0;">This PDF has been processed by <strong>AccessPDF</strong> for:</p>
                        <ul style="margin: 0; padding-left: 20px;">
                            <li>Screen reader compatibility</li>
                            <li>WCAG 2.1 AA compliance</li>
                            <li>AI assistant searchability</li>
                            <li>Alternative text for images</li>
                            <li>Proper document structure</li>
                        </ul>
                    </div>
                    
                    <div style="margin-bottom: 20px;">
                        <p style="margin: 0 0 8px 0; font-weight: 500;">Available formats:</p>
                        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                            <button onclick="window.open('${this.apiBase}/public/embeddings/documents/${accesspdfId}/download?format=pdf')" 
                                    style="padding: 6px 12px; border: 1px solid #ddd; border-radius: 6px; background: white; cursor: pointer;">
                                📄 Accessible PDF
                            </button>
                            <button onclick="window.open('${this.apiBase}/public/embeddings/documents/${accesspdfId}/download?format=html')" 
                                    style="padding: 6px 12px; border: 1px solid #ddd; border-radius: 6px; background: white; cursor: pointer;">
                                🌐 HTML Version
                            </button>
                            <button onclick="window.open('${this.apiBase}/public/embeddings/documents/${accesspdfId}/download?format=text')" 
                                    style="padding: 6px 12px; border: 1px solid #ddd; border-radius: 6px; background: white; cursor: pointer;">
                                📝 Text Version
                            </button>
                        </div>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <small style="color: #666;">
                            Powered by <a href="https://accesspdf.com" target="_blank" style="color: #10b981; text-decoration: none;">AccessPDF</a>
                        </small>
                        <button onclick="this.parentElement.parentElement.parentElement.remove()" 
                                style="padding: 8px 16px; background: #10b981; color: white; border: none; border-radius: 6px; cursor: pointer;">
                            Close
                        </button>
                    </div>
                </div>
            `;

      // Close modal on background click
      modal.onclick = (e) => {
        if (e.target === modal) {
          modal.remove();
        }
      };

      document.body.appendChild(modal);
    },

    // Observe for dynamically added PDFs
    observeNewPDFs: function () {
      if (!window.MutationObserver) return;

      const observer = new MutationObserver((mutations) => {
        let foundNew = false;

        mutations.forEach((mutation) => {
          mutation.addedNodes.forEach((node) => {
            if (node.nodeType === 1) {
              // Element node
              // Check if the node itself is a PDF link
              if (this.isPDFLink(node)) {
                this.enhancePDFLink(node);
                foundNew = true;
              }

              // Check for PDF links in added subtree
              const pdfLinks =
                node.querySelectorAll &&
                node.querySelectorAll(
                  'a[href$=".pdf"], a[href*=".pdf?"], a[href*=".pdf#"]'
                );
              if (pdfLinks) {
                pdfLinks.forEach((link) => {
                  if (this.enhancePDFLink(link)) {
                    foundNew = true;
                  }
                });
              }
            }
          });
        });

        if (foundNew && this.config.debugMode) {
          console.log('AccessPDF: Enhanced newly added PDF links');
        }
      });

      observer.observe(document.body, {
        childList: true,
        subtree: true,
      });
    },

    // Helper functions
    isPDFLink: function (element) {
      return (
        element.tagName === 'A' &&
        element.href &&
        (element.href.endsWith('.pdf') ||
          element.href.includes('.pdf?') ||
          element.href.includes('.pdf#'))
      );
    },

    extractFilename: function (link) {
      const url = new URL(link.href);
      const pathname = url.pathname;
      const filename = pathname.split('/').pop() || 'document.pdf';
      return filename.replace(/\.[^/.]+$/, ''); // Remove extension
    },

    generatePotentialId: function (pdfUrl) {
      // Generate a consistent ID based on URL
      // This would be resolved to actual AccessPDF ID via your service
      const url = new URL(pdfUrl);
      const path = url.pathname;
      return btoa(this.config.domain + ':' + path)
        .replace(/[^a-zA-Z0-9]/g, '')
        .substring(0, 16);
    },

    // Track analytics (privacy-friendly)
    trackEvent: function (event, data = {}) {
      if (!this.config.trackAnalytics) return;

      // Send anonymous usage data to improve service
      if (navigator.sendBeacon) {
        const payload = JSON.stringify({
          event: event,
          domain: this.config.domain,
          timestamp: Date.now(),
          version: this.version,
          ...data,
        });

        navigator.sendBeacon(`${this.apiBase}/public/analytics`, payload);
      }
    },
  };

  // Auto-initialize if config is provided
  if (window.accesspdf_config) {
    // Wait for DOM ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => {
        AccessPDF.init(window.accesspdf_config);
      });
    } else {
      AccessPDF.init(window.accesspdf_config);
    }
  }

  // Expose globally
  window.AccessPDF = AccessPDF;

  // Track script load
  AccessPDF.trackEvent('script_loaded', {
    referrer: document.referrer,
    page_title: document.title,
  });

  console.log(
    'AccessPDF Integration v' + AccessPDF.version + ' loaded successfully'
  );
})();

// Usage examples for website owners:

/*
// EXAMPLE 1: Basic integration (no exposed API keys!)
<script>
window.accesspdf_config = {
    integrationId: 'agency_public_id_123',  // Safe to expose
    domain: 'agency.gov',                    // Public domain
    showBadges: true
};
</script>
<script src="https://cdn.accesspdf.com/integration.js"></script>

// EXAMPLE 2: Manual enhancement
<script src="https://cdn.accesspdf.com/integration.js"></script>
<script>
// For specific PDFs
document.querySelector('#my-pdf-link').dataset.accesspdfId = 'abc-123-def';
AccessPDF.enhancePDFLink(document.querySelector('#my-pdf-link'));
</script>

// EXAMPLE 3: Dynamic content
<script>
// For SPAs or dynamic content
AccessPDF.init({
    integrationId: 'spa_integration_456',
    autoEnhance: true,
    showBadges: true,
    debugMode: true  // For development
});
</script>
*/
