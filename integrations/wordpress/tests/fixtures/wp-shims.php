<?php
/**
 * Minimal stand-ins for the few WordPress functions the standalone classes call,
 * so their unit tests run with plain PHP.
 */

if (!defined('ABSPATH')) {
    define('ABSPATH', __DIR__ . '/');
}

if (!function_exists('wp_parse_url')) {
    function wp_parse_url($url, $component = -1) {
        return parse_url($url, $component);
    }
}
