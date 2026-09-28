<?php
/**
 * Serves a Markdown version of published posts and pages to AI agents.
 *
 * - /some-page.md (or ?make_pdf_accessible_md=1 without pretty permalinks) always returns Markdown.
 * - The normal URL returns Markdown when the request's Accept header prefers text/markdown.
 * - HTML responses advertise the Markdown version with a <link rel="alternate"> tag and header.
 *
 * Only published, public, non-password-protected content is ever served.
 */

if (!defined('ABSPATH')) {
    exit;
}

class Make_PDF_Accessible_Markdown {
    const QUERY_VAR = 'make_pdf_accessible_md';
    const PATH_VAR = 'make_pdf_accessible_md_path';
    const REWRITE_REGEX = '^(.+?)\.md/?$';
    const REWRITE_VERSION = '1';

    public function register() {
        add_action('init', [$this, 'add_rewrite_rule']);
        add_filter('query_vars', [$this, 'add_query_vars']);
        add_filter('request', [$this, 'resolve_markdown_path']);
        add_action('template_redirect', [$this, 'maybe_serve'], 0);
        add_action('wp_head', [$this, 'output_alternate_link']);
    }

    public static function activate() {
        delete_option('make_pdf_accessible_rewrite_version');
        (new self())->add_rewrite_rule();
    }

    public static function deactivate() {
        global $wp_rewrite;
        unset($wp_rewrite->extra_rules_top[self::REWRITE_REGEX]);
        delete_option('make_pdf_accessible_rewrite_version');
        flush_rewrite_rules();
    }

    public function add_rewrite_rule() {
        add_rewrite_rule(self::REWRITE_REGEX, 'index.php?' . self::PATH_VAR . '=$matches[1]', 'top');

        // Sites that update the plugin without reactivating it still need the rule saved.
        if (self::REWRITE_VERSION !== get_option('make_pdf_accessible_rewrite_version')) {
            flush_rewrite_rules(false);
            update_option('make_pdf_accessible_rewrite_version', self::REWRITE_VERSION);
        }
    }

    public function add_query_vars($vars) {
        $vars[] = self::QUERY_VAR;
        $vars[] = self::PATH_VAR;
        return $vars;
    }

    /**
     * Turns /some-page.md into a normal query for that post, flagged for Markdown output.
     */
    public function resolve_markdown_path($query_vars) {
        if (!isset($query_vars[self::PATH_VAR])) {
            return $query_vars;
        }

        $path = trim($query_vars[self::PATH_VAR], '/');
        $post_id = 0;
        if ('index' === $path && 'page' === get_option('show_on_front')) {
            $post_id = (int) get_option('page_on_front');
        }
        if (!$post_id) {
            $post_id = url_to_postid(home_url(user_trailingslashit('/' . $path)));
        }
        if (!$post_id) {
            return ['error' => '404', self::QUERY_VAR => '1'];
        }

        $post_type = get_post_type($post_id);
        if ('page' === $post_type) {
            $vars = ['page_id' => $post_id];
        } elseif ('attachment' === $post_type) {
            $vars = ['attachment_id' => $post_id];
        } else {
            $vars = ['p' => $post_id, 'post_type' => $post_type];
        }
        $vars[self::QUERY_VAR] = '1';
        return $vars;
    }

    public function maybe_serve() {
        $explicit = (bool) get_query_var(self::QUERY_VAR);
        $post = $this->current_post();

        if (!$post) {
            if ($explicit) {
                $this->send_not_found();
            }
            return;
        }

        $accept = isset($_SERVER['HTTP_ACCEPT']) ? sanitize_text_field(wp_unslash($_SERVER['HTTP_ACCEPT'])) : '';
        if ($explicit || self::prefers_markdown($accept)) {
            $this->send_markdown($post, $explicit);
            exit;
        }

        // The HTML response: tell caches and agents that a Markdown version exists.
        header('Vary: Accept', false);
        header('Link: <' . esc_url_raw($this->markdown_url($post)) . '>; rel="alternate"; type="text/markdown"', false);
    }

    public function output_alternate_link() {
        $post = $this->current_post();
        if ($post) {
            printf(
                '<link rel="alternate" type="text/markdown" href="%s" />' . "\n",
                esc_url($this->markdown_url($post))
            );
        }
    }

    /**
     * Whether an Accept header prefers text/markdown over text/html.
     *
     * text/markdown must be listed explicitly. It wins when its q-value is higher
     * than HTML's, or equal and listed first, so browsers (which never list it)
     * always get HTML.
     *
     * @param string $accept Raw Accept header.
     * @return bool
     */
    public static function prefers_markdown($accept) {
        $accept = (string) $accept;
        if ('' === $accept || false === stripos($accept, 'text/markdown')) {
            return false;
        }

        $entries = [];
        foreach (explode(',', $accept) as $index => $part) {
            $params = array_map('trim', explode(';', $part));
            $type = strtolower(array_shift($params));
            if ('' === $type) {
                continue;
            }
            $q = 1.0;
            foreach ($params as $param) {
                if (0 === stripos($param, 'q=')) {
                    $q = (float) substr($param, 2);
                }
            }
            $entries[] = ['type' => $type, 'q' => $q, 'index' => $index];
        }

        $markdown = self::match_media_type($entries, 'text/markdown');
        if (!$markdown || 'text/markdown' !== $markdown['type'] || $markdown['q'] <= 0) {
            return false;
        }
        $html = self::match_media_type($entries, 'text/html');
        if (!$html || $html['q'] < $markdown['q']) {
            return true;
        }
        return $html['q'] === $markdown['q'] && $markdown['index'] < $html['index'];
    }

    /** Finds the most specific Accept entry for a type: exact, then type/*, then * / *. */
    private static function match_media_type(array $entries, $type) {
        $major = strtok($type, '/');
        $best = null;
        $best_rank = -1;
        foreach ($entries as $entry) {
            if ($entry['type'] === $type) {
                $rank = 2;
            } elseif ($entry['type'] === $major . '/*') {
                $rank = 1;
            } elseif ('*/*' === $entry['type']) {
                $rank = 0;
            } else {
                continue;
            }
            if ($rank > $best_rank) {
                $best = $entry;
                $best_rank = $rank;
            }
        }
        return $best;
    }

    public function markdown_url(WP_Post $post) {
        $permalink = get_permalink($post);
        if (!get_option('permalink_structure') || false !== strpos($permalink, '?')) {
            return add_query_arg(self::QUERY_VAR, '1', $permalink);
        }
        if (untrailingslashit($permalink) === untrailingslashit(home_url())) {
            return trailingslashit(home_url()) . 'index.md';
        }
        return untrailingslashit($permalink) . '.md';
    }

    public function render(WP_Post $post) {
        setup_postdata($post);
        $html = apply_filters('the_content', $post->post_content); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Core filter, so blocks and shortcodes render as on the page.
        wp_reset_postdata();

        /** Lets another component supply the HTML, such as a converted PDF. */
        $html = apply_filters('make_pdf_accessible_markdown_source_html', $html, $post);

        $permalink = get_permalink($post);
        $converter = new Make_PDF_Accessible_HTML_To_Markdown($permalink);
        $title = html_entity_decode(wp_strip_all_tags(get_the_title($post)), ENT_QUOTES, 'UTF-8');
        $json = JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE;

        $markdown = "---\n"
            . 'title: ' . wp_json_encode($title, $json) . "\n"
            . 'url: ' . wp_json_encode($permalink, $json) . "\n"
            . 'last_modified: ' . wp_json_encode(get_post_modified_time('c', true, $post), $json) . "\n"
            . 'language: ' . wp_json_encode(get_bloginfo('language'), $json) . "\n"
            . "---\n\n"
            . ('' === $title ? '' : '# ' . $title . "\n\n")
            . $converter->convert($html);

        return apply_filters('make_pdf_accessible_markdown_output', $markdown, $post);
    }

    private function is_enabled() {
        return (bool) get_option('make_pdf_accessible_serve_markdown', true);
    }

    /** The queried post, if this request is for content we may serve as Markdown. */
    private function current_post() {
        if (!$this->is_enabled() || !is_singular() || is_feed() || is_embed() || is_preview()) {
            return null;
        }
        $post = get_queried_object();
        return ($post instanceof WP_Post && $this->is_eligible($post)) ? $post : null;
    }

    private function is_eligible(WP_Post $post) {
        if ('publish' !== get_post_status($post) || '' !== $post->post_password) {
            return false;
        }
        $types = array_diff(get_post_types(['public' => true]), ['attachment']);
        $types = (array) apply_filters('make_pdf_accessible_markdown_post_types', array_values($types));
        if (!in_array($post->post_type, $types, true)) {
            return false;
        }
        return (bool) apply_filters('make_pdf_accessible_markdown_enabled_for_post', true, $post);
    }

    private function send_markdown(WP_Post $post, $explicit) {
        $markdown = $this->render($post);

        // Keep page-cache plugins from storing Markdown under the HTML URL.
        if (!defined('DONOTCACHEPAGE')) {
            define('DONOTCACHEPAGE', true); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- Standard constant page-cache plugins check.
        }

        status_header(200);
        if (!$explicit) {
            // Negotiated on the HTML URL, so shared caches must not store it. Set
            // explicitly because nocache_headers() only adds "private" on newer WordPress.
            nocache_headers();
            header('Cache-Control: no-store, private, max-age=0');
        }
        header('Content-Type: text/markdown; charset=utf-8');
        header('Vary: Accept', false);
        header('Link: <' . esc_url_raw(get_permalink($post)) . '>; rel="canonical"', false);
        header('Last-Modified: ' . get_post_modified_time('D, d M Y H:i:s', true, $post) . ' GMT');
        header('X-Content-Type-Options: nosniff');

        if (isset($_SERVER['REQUEST_METHOD']) && 'HEAD' === $_SERVER['REQUEST_METHOD']) {
            return;
        }
        echo $markdown; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Markdown text, not HTML.
    }

    private function send_not_found() {
        status_header(404);
        nocache_headers();
        header('Content-Type: text/plain; charset=utf-8');
        echo "Not found\n";
        exit;
    }
}
