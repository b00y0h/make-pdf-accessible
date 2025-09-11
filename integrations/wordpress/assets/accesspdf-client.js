/**
 * AccessPDF Client JavaScript
 * Enhances PDF links for LLM discovery and provides accessibility indicators
 */

(function() {
    'use strict';
    
    // Configuration from WordPress
    const config = window.accesspdf_config || {
        api_base: 'https://api.accesspdf.com',
        client_domain: window.location.hostname
    };
    
    /**
     * Initialize AccessPDF enhancements when DOM is ready
     */
    function initAccessPDF() {
        // Find all PDF links with AccessPDF IDs
        const pdfLinks = document.querySelectorAll('a[data-accesspdf-id]');
        
        pdfLinks.forEach(enhancePDFLink);
        
        // Add accessibility discovery metadata to page
        addPageMetadata();
        
        console.log(`AccessPDF: Enhanced ${pdfLinks.length} PDF links for LLM discovery`);
    }
    
    /**
     * Enhance individual PDF link with accessibility features
     */
    function enhancePDFLink(link) {
        const accesspdfId = link.dataset.accesspdfId;
        if (!accesspdfId) return;
        
        // Add visual accessibility indicator
        if (!link.querySelector('.accesspdf-badge')) {
            const badge = document.createElement('span');
            badge.className = 'accesspdf-badge';
            badge.style.cssText = `
                font-size: 0.75em;
                background: linear-gradient(45deg, #10b981, #059669);
                color: white;
                padding: 2px 8px;
                border-radius: 12px;
                margin-left: 8px;
                display: inline-flex;
                align-items: center;
                gap: 4px;
                font-weight: 500;
                box-shadow: 0 1px 3px rgba(0,0,0,0.2);
            `;
            badge.innerHTML = '🤖 AI Searchable';
            badge.title = 'This document is accessible and searchable by AI assistants';
            
            link.appendChild(badge);
        }
        
        // Add accessibility context menu
        link.addEventListener('contextmenu', function(e) {
            showAccessibilityMenu(e, accesspdfId);
        });
        
        // Add keyboard accessibility
        link.addEventListener('keydown', function(e) {
            if (e.key === 'a' && e.altKey) {
                e.preventDefault();
                showAccessibilityOptions(accesspdfId);
            }
        });
    }
    
    /**
     * Add page-level metadata for LLM discovery
     */
    function addPageMetadata() {
        // Check if page has AccessPDF documents
        const pdfLinks = document.querySelectorAll('a[data-accesspdf-id]');
        if (pdfLinks.length === 0) return;
        
        // Add meta tags for LLM crawlers
        const metaTags = [
            { name: 'accesspdf-api', content: config.api_base + '/public/embeddings/search' },
            { name: 'accessible-documents-count', content: pdfLinks.length.toString() },
            { name: 'accessibility-features', content: 'pdf-ua,wcag-aa,embeddings,alt-text' }
        ];
        
        metaTags.forEach(tag => {
            if (!document.querySelector(`meta[name="${tag.name}"]`)) {
                const meta = document.createElement('meta');
                meta.name = tag.name;
                meta.content = tag.content;
                document.head.appendChild(meta);
            }
        });
        
        // Add well-known accessibility API link
        const linkElement = document.createElement('link');
        linkElement.rel = 'accessibility-api';
        linkElement.href = `${config.api_base}/public/embeddings/documents?client_domain=${encodeURIComponent(config.client_domain)}`;
        linkElement.type = 'application/json';
        document.head.appendChild(linkElement);
    }
    
    /**
     * Show accessibility context menu
     */
    function showAccessibilityMenu(e, accesspdfId) {
        e.preventDefault();
        
        const menu = document.createElement('div');
        menu.className = 'accesspdf-context-menu';
        menu.style.cssText = `
            position: fixed;
            top: ${e.clientY}px;
            left: ${e.clientX}px;
            background: white;
            border: 1px solid #ccc;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10000;
            padding: 8px 0;
            min-width: 200px;
        `;
        
        const options = [
            { label: '📄 View Accessible HTML', action: () => openAccessibleVersion(accesspdfId, 'html') },
            { label: '📝 View Text Version', action: () => openAccessibleVersion(accesspdfId, 'text') },
            { label: '🔍 Search Document', action: () => openDocumentSearch(accesspdfId) },
            { label: '📊 Accessibility Report', action: () => openAccessibilityReport(accesspdfId) }
        ];
        
        options.forEach(option => {
            const item = document.createElement('div');
            item.style.cssText = `
                padding: 8px 16px;
                cursor: pointer;
                font-size: 14px;
                border-bottom: 1px solid #f0f0f0;
            `;
            item.textContent = option.label;
            item.onclick = option.action;
            
            item.onmouseenter = () => item.style.background = '#f5f5f5';
            item.onmouseleave = () => item.style.background = 'white';
            
            menu.appendChild(item);
        });
        
        document.body.appendChild(menu);
        
        // Remove menu when clicking elsewhere
        setTimeout(() => {
            document.addEventListener('click', function removeMenu() {
                if (menu.parentNode) {
                    menu.parentNode.removeChild(menu);
                }
                document.removeEventListener('click', removeMenu);
            });
        }, 100);
    }
    
    /**
     * Open accessible version of document
     */
    function openAccessibleVersion(accesspdfId, format) {
        const url = `${config.api_base}/public/embeddings/documents/${accesspdfId}/download?format=${format}`;
        window.open(url, '_blank');
    }
    
    /**
     * Open document in AccessPDF search interface
     */
    function openDocumentSearch(accesspdfId) {
        const url = `${config.api_base.replace('api.', 'search.')}/documents/${accesspdfId}`;
        window.open(url, '_blank');
    }
    
    /**
     * Open accessibility report
     */
    function openAccessibilityReport(accesspdfId) {
        const url = `${config.api_base}/public/embeddings/documents/${accesspdfId}`;
        window.open(url, '_blank');
    }
    
    /**
     * Show accessibility options modal
     */
    function showAccessibilityOptions(accesspdfId) {
        // Create and show modal with accessibility options
        console.log('Accessibility options for document:', accesspdfId);
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAccessPDF);
    } else {
        initAccessPDF();
    }
    
    // Expose function for WordPress admin
    window.accesspdf_process_now = function(postId) {
        if (confirm('Process this PDF with AccessPDF now?')) {
            // Trigger immediate processing
            fetch(window.location.origin + '/wp-admin/admin-ajax.php', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `action=accesspdf_process_now&post_id=${postId}`
            }).then(response => {
                if (response.ok) {
                    alert('PDF processing started! Check back in a few minutes.');
                    location.reload();
                } else {
                    alert('Failed to start processing. Please check your API key.');
                }
            });
        }
    };
    
})();