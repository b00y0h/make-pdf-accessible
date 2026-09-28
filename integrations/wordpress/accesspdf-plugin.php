<?php
/**
 * Plugin Name: AccessPDF
 * Plugin URI: https://accesspdf.com/wordpress
 * Description: Inventories your PDFs for accessibility, makes uploaded PDFs accessible, and serves Markdown versions of your posts and pages to AI agents
 * Version: 1.2.0
 * Author: AccessPDF
 * License: GPL v2 or later
 * License URI: https://www.gnu.org/licenses/gpl-2.0.html
 * Requires at least: 6.5
 * Requires PHP: 7.4
 * Text Domain: accesspdf
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

define('ACCESSPDF_VERSION', '1.2.0');
define('ACCESSPDF_PLUGIN_FILE', __FILE__);

require_once __DIR__ . '/includes/class-accesspdf-html-to-markdown.php';
require_once __DIR__ . '/includes/class-accesspdf-markdown.php';
require_once __DIR__ . '/includes/class-accesspdf-pdf-analyzer.php';
require_once __DIR__ . '/includes/class-accesspdf-inventory.php';
require_once __DIR__ . '/includes/class-accesspdf-inventory-page.php';

class AccessPDFPlugin {
    private $api_base = 'https://api.accesspdf.com';
    private $api_key;
    private $client_domain;

    public function __construct() {
        $this->api_key = get_option('accesspdf_api_key', '');
        $this->client_domain = wp_parse_url(home_url(), PHP_URL_HOST);

        add_action('init', [$this, 'init']);
        add_action('admin_init', [$this, 'register_settings']);
        add_action('admin_menu', [$this, 'add_admin_menu']);

        // Hook into PDF uploads
        add_filter('wp_handle_upload', [$this, 'handle_pdf_upload']);
        add_filter('attachment_fields_to_edit', [$this, 'add_accessibility_fields'], 10, 2);
        add_filter('attachment_fields_to_save', [$this, 'save_accessibility_fields'], 10, 2);

        (new AccessPDF_Markdown())->register();

        $inventory = new AccessPDF_Inventory();
        $inventory->register();
        if (is_admin()) {
            (new AccessPDF_Inventory_Page($inventory))->register();
        }
    }

    public function init() {
        // Register settings
        add_option('accesspdf_api_key', '');
        add_option('accesspdf_auto_process', true);
        add_option('accesspdf_serve_markdown', true);
    }

    public function register_settings() {
        register_setting('accesspdf_settings', 'accesspdf_api_key', [
            'type' => 'string',
            'sanitize_callback' => 'sanitize_text_field',
        ]);
        register_setting('accesspdf_settings', 'accesspdf_auto_process', [
            'type' => 'boolean',
            'sanitize_callback' => 'rest_sanitize_boolean',
        ]);
        register_setting('accesspdf_settings', 'accesspdf_serve_markdown', [
            'type' => 'boolean',
            'sanitize_callback' => 'rest_sanitize_boolean',
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
            do_action('accesspdf_log', 'No API key configured, skipping PDF processing');
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
                            <?php echo esc_html(ucfirst($status ?: 'pending')); ?>
                        </span>
                    </p>
                    <?php if ($score): ?>
                        <p><strong>Accessibility Score:</strong> <?php echo esc_html($score); ?>%</p>
                    <?php endif; ?>
                </div>
            <?php else: ?>
                <div style="padding: 10px; border: 1px solid #orange; border-radius: 4px; background: #fffbf0;">
                    <p><em>PDF not yet processed by AccessPDF. PDFs are sent for processing when they're uploaded with an API key set and Auto-Process PDFs turned on.</em></p>
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
                        <th scope="row"><label for="accesspdf_api_key">API Key</label></th>
                        <td>
                            <input type="password" id="accesspdf_api_key" name="accesspdf_api_key" value="<?php echo esc_attr($this->api_key); ?>" class="regular-text" />
                            <p class="description">Get your API key from <a href="https://dashboard.accesspdf.com" target="_blank">AccessPDF Dashboard</a></p>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row">Auto-Process PDFs</th>
                        <td>
                            <label for="accesspdf_auto_process">
                                <input type="checkbox" id="accesspdf_auto_process" name="accesspdf_auto_process" value="1" <?php checked(get_option('accesspdf_auto_process', true)); ?> />
                                Automatically process PDFs when uploaded
                            </label>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row">Markdown for AI agents</th>
                        <td>
                            <label for="accesspdf_serve_markdown">
                                <input type="checkbox" id="accesspdf_serve_markdown" name="accesspdf_serve_markdown" value="1" <?php checked(get_option('accesspdf_serve_markdown', true)); ?> />
                                Serve a Markdown version of published posts and pages
                            </label>
                            <p class="description">AI agents read Markdown more reliably than full web pages. Visitors always see the normal page.</p>
                        </td>
                    </tr>
                </table>
                <?php submit_button(); ?>
            </form>

            <hr style="margin: 30px 0;" />

            <h2>PDF inventory</h2>
            <p>See every PDF on your site, which ones need accessibility work, and which pages link to them: <a href="<?php echo esc_url(AccessPDF_Inventory_Page::url()); ?>">Media → PDF Inventory</a>.</p>

            <h2>How Markdown versions work</h2>
            <ul style="list-style: disc; padding-left: 20px;">
                <?php if (get_option('permalink_structure')): ?>
                    <li>Add <code>.md</code> to any post or page address to get its Markdown version, for example <code><?php echo esc_html(untrailingslashit(home_url('/about')) . '.md'); ?></code>.</li>
                <?php else: ?>
                    <li>Add <code>?accesspdf_md=1</code> to any post or page address to get its Markdown version. Turn on pretty permalinks to use <code>.md</code> addresses instead.</li>
                <?php endif; ?>
                <li>Agents that ask for <code>text/markdown</code> in their <code>Accept</code> header get Markdown from the normal address.</li>
                <li>Each page links to its Markdown version with <code>&lt;link rel="alternate" type="text/markdown"&gt;</code>.</li>
                <li>Drafts, private posts and password-protected posts are never served.</li>
                <li>If a page cache or CDN serves your HTML, agents asking for Markdown on the normal address may get the cached HTML. The <code>.md</code> addresses always work.</li>
            </ul>
        </div>
        <?php
    }
}

// Initialize the plugin
new AccessPDFPlugin();

register_activation_hook(__FILE__, ['AccessPDF_Markdown', 'activate']);
register_deactivation_hook(__FILE__, ['AccessPDF_Markdown', 'deactivate']);

// WordPress cron action for processing PDFs
add_action('accesspdf_process_pdf', 'accesspdf_process_pdf_callback');

function accesspdf_process_pdf_callback($args) {
    $api_key = get_option('accesspdf_api_key', '');
    
    if (empty($api_key)) {
        do_action('accesspdf_log', 'Cannot process PDF, no API key configured');
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
                'client_domain' => wp_parse_url(home_url(), PHP_URL_HOST),
                'plugin_version' => ACCESSPDF_VERSION,
            ]),
            'callback_url' => admin_url('admin-ajax.php?action=accesspdf_webhook'),
        ]),
        'timeout' => 30,
    ]);
    
    if (is_wp_error($response)) {
        do_action('accesspdf_log', 'Failed to send PDF for processing: ' . $response->get_error_message());
        return;
    }
    
    $body = wp_remote_retrieve_body($response);
    $result = json_decode($body, true);
    
    if (isset($result['accesspdf_id'])) {
        // Store AccessPDF ID for later reference
        // This would be stored against the WordPress attachment
        update_option('accesspdf_last_id', $result['accesspdf_id']);
        do_action('accesspdf_log', 'PDF processing initiated, ID: ' . $result['accesspdf_id']);
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
            'meta_key' => '_accesspdf_id', // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- Looks up one attachment by its service ID.
            'meta_value' => $accesspdf_id, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_value -- As above.
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
