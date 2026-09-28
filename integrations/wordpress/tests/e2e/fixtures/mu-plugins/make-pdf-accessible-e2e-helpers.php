<?php
/**
 * Test-only helpers for the end-to-end suite. The harness mounts this file as a
 * must-use plugin and defines MAKE_PDF_ACCESSIBLE_E2E; it is never shipped with the plugin.
 */

if (!defined('MAKE_PDF_ACCESSIBLE_E2E') || !MAKE_PDF_ACCESSIBLE_E2E) {
    return;
}

add_shortcode('e2e_shortcode', function () {
    return '<p>Rendered by a shortcode.</p>';
});

add_action('init', function () {
    // ?e2e_set=option&value=x: change an option between checks.
    if (isset($_GET['e2e_set'], $_GET['value'])) {
        $name = sanitize_key(wp_unslash($_GET['e2e_set']));
        update_option($name, wp_unslash($_GET['value']));
        if ('permalink_structure' === $name) {
            flush_rewrite_rules(false);
        }
        wp_send_json(['ok' => true]);
    }
    // ?e2e_ids=1: IDs of the seeded content.
    if (isset($_GET['e2e_ids'])) {
        wp_send_json(get_option('make_pdf_accessible_e2e_ids'));
    }
    // ?e2e_reset_inventory=1: forget scan results, keeping the checks made on upload.
    if (isset($_GET['e2e_reset_inventory'])) {
        delete_option('make_pdf_accessible_inventory_state');
        delete_option('make_pdf_accessible_inventory_other');
        delete_post_meta_by_key('_make_pdf_accessible_linked_from');
        wp_send_json(['ok' => true]);
    }
}, 1);
