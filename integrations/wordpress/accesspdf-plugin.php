<?php
/**
 * Plugin Name: AccessPDF Integration
 * Plugin URI: https://accesspdf.com/wordpress
 * Description: Automatically makes uploaded PDFs accessible and discoverable by AI/LLMs
 * Version: 1.0.0
 * Author: AccessPDF
 * License: GPL v2 or later
 * License URI: https://www.gnu.org/licenses/gpl-2.0.html
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

class AccessPDFPlugin {
    private $api_base = 'https://api.accesspdf.com';
    private $api_key;
    private $client_domain;
    
    public function __construct() {
        $this->api_key = get_option('accesspdf_api_key', '');
        $this->client_domain = parse_url(home_url(), PHP_URL_HOST);
        
        add_action('init', [$this, 'init']);
        add_action('wp_enqueue_scripts', [$this, 'enqueue_scripts']);
        add_action('admin_menu', [$this, 'add_admin_menu']);
        
        // Hook into PDF uploads
        add_filter('wp_handle_upload', [$this, 'handle_pdf_upload']);
        add_filter('attachment_fields_to_edit', [$this, 'add_accessibility_fields'], 10, 2);
        add_filter('attachment_fields_to_save', [$this, 'save_accessibility_fields'], 10, 2);
        
        // Add accessibility metadata to PDF links
        add_filter('wp_get_attachment_link', [$this, 'enhance_pdf_links'], 10, 6);
    }
    
    public function init() {
        // Register settings
        add_option('accesspdf_api_key', '');
        add_option('accesspdf_auto_process', true);
        add_option('accesspdf_public_discovery', true);
    }
    
    public function enqueue_scripts() {
        // Load the public CDN script
        wp_enqueue_script(
            'accesspdf-integration',
            'https://cdn.accesspdf.com/integration.js',
            [],
            '1.0.0',
            true
        );
        
        // Get integration ID from settings (safe to expose)
        $integration_id = get_option('accesspdf_integration_id', '');
        
        // Pass ONLY safe configuration to frontend (no API keys!)
        wp_localize_script('accesspdf-integration', 'accesspdf_config', [
            'integrationId' => $integration_id,  // Safe to expose
            'domain' => $this->client_domain,     // Public domain
            'showBadges' => get_option('accesspdf_show_badges', true),
            'debugMode' => defined('WP_DEBUG') && WP_DEBUG,
        ]);
    }
    
    public function add_admin_menu() {
        add_options_page(
            'AccessPDF Settings',
            'AccessPDF',
            'manage_options',
            'accesspdf-settings',
            [$this, 'settings_page']
        );
    }
    
    public function handle_pdf_upload($upload) {
        // Only process PDFs
        if (strpos($upload['type'], 'application/pdf') !== 0) {
            return $upload;
        }
        
        // Skip if auto-processing is disabled
        if (!get_option('accesspdf_auto_process', true)) {
            return $upload;
        }
        
        // Skip if no API key configured
        if (empty($this->api_key)) {
            error_log('AccessPDF: No API key configured, skipping PDF processing');
            return $upload;
        }
        
        // Schedule processing via WordPress cron
        wp_schedule_single_event(time() + 30, 'accesspdf_process_pdf', [
            'file_path' => $upload['file'],
            'file_url' => $upload['url'],
            'filename' => basename($upload['file']),
            'client_metadata' => [
                'site_url' => home_url(),
                'site_name' => get_bloginfo('name'),
                'upload_date' => current_time('mysql'),
            ]
        ]);
        
        return $upload;
    }
    
    public function add_accessibility_fields($form_fields, $post) {
        if (strpos($post->post_mime_type, 'application/pdf') !== 0) {
            return $form_fields;
        }
        
        $accesspdf_id = get_post_meta($post->ID, '_accesspdf_id', true);
        $processing_status = get_post_meta($post->ID, '_accesspdf_status', true);
        $accessibility_score = get_post_meta($post->ID, '_accesspdf_score', true);
        
        $form_fields['accesspdf_info'] = [
            'label' => 'AccessPDF Status',
            'input' => 'html',
            'html' => $this->render_accessibility_status($accesspdf_id, $processing_status, $accessibility_score),
            'show_in_edit' => true,
        ];
        
        return $form_fields;
    }
    
    public function save_accessibility_fields($post, $attachment) {
        // This function handles saving any manual accessibility overrides
        return $post;
    }
    
    public function enhance_pdf_links($link, $id, $size, $permalink, $icon, $text) {
        $post = get_post($id);
        
        // Only enhance PDF links
        if (strpos($post->post_mime_type, 'application/pdf') !== 0) {
            return $link;
        }
        
        $accesspdf_id = get_post_meta($id, '_accesspdf_id', true);
        
        if (empty($accesspdf_id)) {
            return $link;
        }
        
        // Add accessibility metadata for LLM discovery
        $enhanced_attributes = [
            'data-accesspdf-id="' . esc_attr($accesspdf_id) . '"',
            'data-accessibility-api="' . esc_attr($this->api_base) . '"',
            'data-accessible-formats="html,text,embeddings"',
        ];
        
        // Add structured data for search engines
        $structured_data = [
            '@context' => 'https://schema.org',
            '@type' => 'Document',
            'name' => $post->post_title,
            'encodingFormat' => 'application/pdf',
            'accessibilityFeature' => ['structuralNavigation', 'alternativeText', 'highContrastDisplay'],
            'accessibilityHazard' => 'none',
            'accessMode' => ['textual', 'visual'],
            'accessModeSufficient' => 'textual',
            'accessibilityAPI' => $this->api_base . '/public/embeddings/documents/' . $accesspdf_id,
        ];
        
        // Inject structured data
        add_action('wp_footer', function() use ($structured_data) {
            echo '<script type="application/ld+json">' . wp_json_encode($structured_data) . '</script>';
        });
        
        // Add attributes to the link
        $enhanced_link = str_replace('<a ', '<a ' . implode(' ', $enhanced_attributes) . ' ', $link);
        
        // Add accessibility indicator
        $accessibility_badge = '<span class="accesspdf-badge" style="font-size: 0.75em; background: #10b981; color: white; padding: 2px 6px; border-radius: 3px; margin-left: 5px;">🔍 AI Searchable</span>';
        
        return $enhanced_link . $accessibility_badge;
    }
    
    private function render_accessibility_status($accesspdf_id, $status, $score) {
        ob_start();
        ?>
        <div class="accesspdf-status">
            <?php if ($accesspdf_id): ?>
                <div style="padding: 10px; border: 1px solid #ddd; border-radius: 4px; background: #f9f9f9;">
                    <p><strong>AccessPDF ID:</strong> <?php echo esc_html($accesspdf_id); ?></p>
                    <p><strong>Status:</strong> 
                        <span class="status-<?php echo esc_attr($status); ?>" style="
                            padding: 2px 8px; 
                            border-radius: 12px; 
                            font-size: 12px;
                            background: <?php echo $status === 'completed' ? '#dcfce7' : ($status === 'processing' ? '#fef3c7' : '#fee2e2'); ?>;
                            color: <?php echo $status === 'completed' ? '#166534' : ($status === 'processing' ? '#92400e' : '#991b1b'); ?>;
                        ">
                            <?php echo ucfirst($status ?: 'pending'); ?>
                        </span>
                    </p>
                    <?php if ($score): ?>
                        <p><strong>Accessibility Score:</strong> <?php echo esc_html($score); ?>%</p>
                    <?php endif; ?>
                    <p style="margin-top: 8px;">
                        <small>
                            <a href="<?php echo $this->api_base; ?>/public/embeddings/documents/<?php echo esc_attr($accesspdf_id); ?>" target="_blank">
                                View on AccessPDF →
                            </a>
                        </small>
                    </p>
                </div>
            <?php else: ?>
                <div style="padding: 10px; border: 1px solid #orange; border-radius: 4px; background: #fffbf0;">
                    <p><em>PDF not yet processed by AccessPDF</em></p>
                    <button type="button" onclick="accesspdf_process_now(<?php echo $post->ID; ?>)" class="button button-secondary">
                        Process Now
                    </button>
                </div>
            <?php endif; ?>
        </div>
        <?php
        return ob_get_clean();
    }
    
    public function settings_page() {
        ?>
        <div class="wrap">
            <h1>AccessPDF Settings</h1>
            <form method="post" action="options.php">
                <?php settings_fields('accesspdf_settings'); ?>
                <table class="form-table">
                    <tr>
                        <th scope="row">API Key</th>
                        <td>
                            <input type="password" name="accesspdf_api_key" value="<?php echo esc_attr($this->api_key); ?>" class="regular-text" />
                            <p class="description">Get your API key from <a href="https://dashboard.accesspdf.com" target="_blank">AccessPDF Dashboard</a></p>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row">Auto-Process PDFs</th>
                        <td>
                            <input type="checkbox" name="accesspdf_auto_process" value="1" <?php checked(get_option('accesspdf_auto_process', true)); ?> />
                            <label>Automatically process PDFs when uploaded</label>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row">Public Discovery</th>
                        <td>
                            <input type="checkbox" name="accesspdf_public_discovery" value="1" <?php checked(get_option('accesspdf_public_discovery', true)); ?> />
                            <label>Allow LLMs and search engines to discover your accessible documents</label>
                            <p class="description">Enables AI assistants like ChatGPT to search and reference your documents</p>
                        </td>
                    </tr>
                </table>
                <?php submit_button(); ?>
            </form>
            
            <hr style="margin: 30px 0;" />
            
            <h2>Integration Guide</h2>
            <div style="background: #f9f9f9; padding: 15px; border-radius: 4px;">
                <p><strong>LLM Discovery:</strong> When this plugin is active, your PDFs become discoverable by AI assistants.</p>
                <p><strong>How it works:</strong></p>
                <ol>
                    <li>Upload a PDF to your WordPress media library</li>
                    <li>Plugin automatically sends it to AccessPDF for processing</li>
                    <li>Adds special metadata tags to PDF links on your site</li>
                    <li>LLMs can discover and search your documents via AccessPDF API</li>
                </ol>
                
                <p style="margin-top: 15px;"><strong>API Endpoint:</strong></p>
                <code><?php echo $this->api_base; ?>/public/embeddings/search</code>
                
                <p style="margin-top: 15px;"><strong>Your Site's Documents:</strong></p>
                <code><?php echo $this->api_base; ?>/public/embeddings/documents?client_domain=<?php echo urlencode($this->client_domain); ?></code>
            </div>
        </div>
        <?php
    }
}

// Initialize the plugin
new AccessPDFPlugin();

// WordPress cron action for processing PDFs
add_action('accesspdf_process_pdf', 'accesspdf_process_pdf_callback');

function accesspdf_process_pdf_callback($args) {
    $api_key = get_option('accesspdf_api_key', '');
    
    if (empty($api_key)) {
        error_log('AccessPDF: Cannot process PDF, no API key configured');
        return;
    }
    
    $api_base = 'https://api.accesspdf.com';
    
    // Send PDF to AccessPDF service
    $response = wp_remote_post($api_base . '/v1/documents/client/upload', [
        'headers' => [
            'Authorization' => 'Bearer ' . $api_key,
            'Content-Type' => 'application/json',
        ],
        'body' => wp_json_encode([
            'file_url' => $args['file_url'],
            'filename' => $args['filename'],
            'client_metadata' => array_merge($args['client_metadata'], [
                'wordpress_post_id' => null, // Would be set when attached to post
                'client_domain' => parse_url(home_url(), PHP_URL_HOST),
                'plugin_version' => '1.0.0',
            ]),
            'callback_url' => admin_url('admin-ajax.php?action=accesspdf_webhook'),
            'public_discovery' => get_option('accesspdf_public_discovery', true),
        ]),
        'timeout' => 30,
    ]);
    
    if (is_wp_error($response)) {
        error_log('AccessPDF: Failed to send PDF for processing: ' . $response->get_error_message());
        return;
    }
    
    $body = wp_remote_retrieve_body($response);
    $result = json_decode($body, true);
    
    if (isset($result['accesspdf_id'])) {
        // Store AccessPDF ID for later reference
        // This would be stored against the WordPress attachment
        update_option('accesspdf_last_id', $result['accesspdf_id']);
        error_log('AccessPDF: PDF processing initiated, ID: ' . $result['accesspdf_id']);
    }
}

// Handle webhook callbacks from AccessPDF service
add_action('wp_ajax_nopriv_accesspdf_webhook', 'accesspdf_webhook_handler');
add_action('wp_ajax_accesspdf_webhook', 'accesspdf_webhook_handler');

function accesspdf_webhook_handler() {
    // Verify webhook signature here for security
    
    $input = file_get_contents('php://input');
    $data = json_decode($input, true);
    
    if (isset($data['accesspdf_id']) && isset($data['status'])) {
        $accesspdf_id = $data['accesspdf_id'];
        $status = $data['status'];
        
        // Find WordPress post with this AccessPDF ID
        $posts = get_posts([
            'meta_key' => '_accesspdf_id',
            'meta_value' => $accesspdf_id,
            'post_type' => 'attachment',
        ]);
        
        if ($posts) {
            $post_id = $posts[0]->ID;
            
            // Update metadata
            update_post_meta($post_id, '_accesspdf_status', $status);
            
            if ($status === 'completed' && isset($data['accessibility_score'])) {
                update_post_meta($post_id, '_accesspdf_score', $data['accessibility_score']);
                update_post_meta($post_id, '_accesspdf_completed_at', current_time('mysql'));
            }
        }
        
        wp_send_json_success(['message' => 'Webhook processed successfully']);
    }
    
    wp_send_json_error(['message' => 'Invalid webhook data']);
}
?>