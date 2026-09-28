<?php
/**
 * PDF inventory: finds every PDF in the media library and every PDF that published
 * content links to, checks each one locally, and records which pages link to it.
 *
 * Everything runs on the site's own server. Scans run in batches through a REST
 * endpoint so large sites don't time out.
 */

if (!defined('ABSPATH')) {
    exit;
}

class Make_PDF_Accessible_Inventory {
    const META = '_make_pdf_accessible_inventory';
    const LINKS_META = '_make_pdf_accessible_linked_from';
    const OTHER_OPTION = 'make_pdf_accessible_inventory_other';
    const STATE_OPTION = 'make_pdf_accessible_inventory_state';

    /** Bump when the analyzer changes so every file is checked again. */
    const ANALYSIS_VERSION = 1;

    const FILE_BATCH = 10;
    const POST_BATCH = 50;
    const MAX_EXTERNAL = 1000;

    /** Statuses beyond the analyzer's own. */
    const STATUS_MISSING = 'missing';
    const STATUS_NOT_CHECKED = 'not_checked';

    /** @var Make_PDF_Accessible_PDF_Analyzer|null */
    private $analyzer;

    /** @var array<string, int>|null Upload-relative path (lowercase) => attachment ID. */
    private $attachment_map;

    public function register() {
        add_action('add_attachment', [$this, 'analyze_attachment']);
        add_action('rest_api_init', [$this, 'register_routes']);
        add_action('admin_post_make_pdf_accessible_inventory_csv', [$this, 'export_csv']);
    }

    public static function capability() {
        return (string) apply_filters('make_pdf_accessible_inventory_capability', 'manage_options');
    }

    public function register_routes() {
        register_rest_route('make-pdf-accessible/v1', '/inventory/scan', [
            'methods' => 'POST',
            'callback' => [$this, 'rest_scan'],
            'permission_callback' => function () {
                return current_user_can(self::capability());
            },
            'args' => [
                'phase' => ['type' => 'string', 'enum' => ['files', 'links', 'other'], 'default' => 'files'],
                'offset' => ['type' => 'integer', 'minimum' => 0, 'default' => 0],
            ],
        ]);
    }

    /**
     * Runs one batch of the scan. The client calls again with the returned phase and
     * offset until done is true. Phases: check library files, map links from published
     * content, then check linked PDFs that aren't in the media library.
     */
    public function rest_scan(WP_REST_Request $request) {
        $phase = $request->get_param('phase');
        $offset = (int) $request->get_param('offset');

        if ('files' === $phase) {
            $ids = $this->pdf_attachment_ids();
            foreach (array_slice($ids, $offset, self::FILE_BATCH) as $id) {
                $this->analyze_attachment($id);
            }
            return $this->progress('files', $offset + self::FILE_BATCH, count($ids), 'links', __('Checking PDF files', 'make-pdf-accessible'));
        }

        if ('links' === $phase) {
            if (0 === $offset) {
                delete_post_meta_by_key(self::LINKS_META);
                update_option(self::OTHER_OPTION, ['local' => [], 'external' => []], false);
            }
            $ids = $this->published_post_ids();
            $this->record_links(array_slice($ids, $offset, self::POST_BATCH));
            return $this->progress('links', $offset + self::POST_BATCH, count($ids), 'other', __('Finding links in published content', 'make-pdf-accessible'));
        }

        $other = $this->other_pdfs();
        $keys = array_keys($other['local']);
        foreach (array_slice($keys, $offset, self::FILE_BATCH) as $key) {
            $entry = $other['local'][$key];
            $other['local'][$key]['analysis'] = empty($entry['file'])
                ? null
                : $this->stamp($this->analyzer()->analyze_file($entry['file']), $entry['file']);
        }
        update_option(self::OTHER_OPTION, $other, false);

        $next = $offset + self::FILE_BATCH;
        if ($next >= count($keys)) {
            update_option(self::STATE_OPTION, ['last_scan' => time()], false);
            return ['done' => true];
        }
        return $this->progress('other', $next, count($keys), null, __('Checking linked PDFs outside the media library', 'make-pdf-accessible'));
    }

    private function progress($phase, $next, $total, $next_phase, $label) {
        if ($next >= $total) {
            return null === $next_phase
                ? ['done' => true]
                : ['done' => false, 'phase' => $next_phase, 'offset' => 0, 'label' => $label, 'current' => $total, 'total' => $total];
        }
        return ['done' => false, 'phase' => $phase, 'offset' => $next, 'label' => $label, 'current' => $next, 'total' => $total];
    }

    /**
     * Checks a PDF attachment and stores the result. Skips files unchanged since the last check.
     *
     * @param int $attachment_id
     */
    public function analyze_attachment($attachment_id) {
        if ('application/pdf' !== get_post_mime_type($attachment_id)) {
            return;
        }
        $file = get_attached_file($attachment_id);
        $existing = get_post_meta($attachment_id, self::META, true);
        $fingerprint = $this->fingerprint($file);
        if (is_array($existing) && isset($existing['fingerprint']) && $existing['fingerprint'] === $fingerprint) {
            return;
        }
        update_post_meta($attachment_id, self::META, $this->stamp($this->analyzer()->analyze_file($file), $file));
    }

    private function stamp(array $analysis, $file) {
        $analysis['fingerprint'] = $this->fingerprint($file);
        $analysis['checked_at'] = time();
        return $analysis;
    }

    private function fingerprint($file) {
        if (!$file || !is_file($file)) {
            return self::ANALYSIS_VERSION . ':missing';
        }
        return self::ANALYSIS_VERSION . ':' . filesize($file) . ':' . filemtime($file);
    }

    private function analyzer() {
        if (null === $this->analyzer) {
            $max_bytes = (int) apply_filters('make_pdf_accessible_inventory_max_bytes', 50 * 1024 * 1024);
            $this->analyzer = new Make_PDF_Accessible_PDF_Analyzer($max_bytes);
        }
        return $this->analyzer;
    }

    /** @return int[] */
    public function pdf_attachment_ids() {
        return array_map('intval', get_posts([
            'post_type' => 'attachment',
            'post_mime_type' => 'application/pdf',
            'post_status' => 'any',
            'fields' => 'ids',
            'posts_per_page' => -1,
            'orderby' => 'ID',
            'order' => 'ASC',
            'no_found_rows' => true,
        ]));
    }

    /** @return int[] Published posts of every public type, where links to PDFs live. */
    private function published_post_ids() {
        $types = array_values(array_diff(get_post_types(['public' => true]), ['attachment']));
        return array_map('intval', get_posts([
            'post_type' => $types,
            'post_status' => 'publish',
            'fields' => 'ids',
            'posts_per_page' => -1,
            'orderby' => 'ID',
            'order' => 'ASC',
            'no_found_rows' => true,
        ]));
    }

    /** @param int[] $post_ids */
    private function record_links(array $post_ids) {
        $other = $this->other_pdfs();
        foreach ($post_ids as $post_id) {
            $post = get_post($post_id);
            if (!$post) {
                continue;
            }
            foreach (self::extract_pdf_urls($post->post_content) as $url) {
                $target = $this->resolve_pdf_url($url, get_permalink($post));
                if ('attachment' === $target['type']) {
                    $linked = self::post_ids(get_post_meta($target['id'], self::LINKS_META, true));
                    if (!in_array($post_id, $linked, true)) {
                        $linked[] = $post_id;
                        update_post_meta($target['id'], self::LINKS_META, $linked);
                    }
                } elseif ('local' === $target['type']) {
                    $key = $target['key'];
                    if (!isset($other['local'][$key])) {
                        $other['local'][$key] = ['url' => $target['url'], 'file' => $target['file'], 'linked_from' => [], 'analysis' => null];
                    }
                    if (!in_array($post_id, $other['local'][$key]['linked_from'], true)) {
                        $other['local'][$key]['linked_from'][] = $post_id;
                    }
                } elseif (isset($other['external'][$target['url']]) || count($other['external']) < self::MAX_EXTERNAL) {
                    $other['external'][$target['url']][] = $post_id;
                }
            }
        }
        update_option(self::OTHER_OPTION, $other, false);
    }

    /** @return array{local: array, external: array} */
    public function other_pdfs() {
        $other = get_option(self::OTHER_OPTION);
        return is_array($other) ? $other + ['local' => [], 'external' => []] : ['local' => [], 'external' => []];
    }

    /**
     * PDF URLs in an HTML fragment: href, src and data attributes whose path ends in .pdf.
     *
     * @param string $html
     * @return string[]
     */
    public static function extract_pdf_urls($html) {
        if (!preg_match_all('/\b(?:href|src|data)\s*=\s*(["\'])(.*?)\1/is', (string) $html, $m)) {
            return [];
        }
        $urls = [];
        foreach ($m[2] as $raw) {
            $url = trim(html_entity_decode($raw, ENT_QUOTES | ENT_HTML5, 'UTF-8'));
            $path = wp_parse_url($url, PHP_URL_PATH);
            if (is_string($path) && preg_match('/\.pdf$/i', $path)) {
                $urls[] = $url;
            }
        }
        return array_values(array_unique($urls));
    }

    /**
     * Classifies a PDF URL as a media library attachment, a local file outside the
     * library, or a file on another site.
     */
    private function resolve_pdf_url($url, $base) {
        $absolute = WP_Http::make_absolute_url($url, $base ? $base : home_url('/'));
        $parts = wp_parse_url($absolute);
        $host = isset($parts['host']) ? strtolower($parts['host']) : '';
        $site_hosts = array_unique([
            strtolower((string) wp_parse_url(home_url(), PHP_URL_HOST)),
            strtolower((string) wp_parse_url(site_url(), PHP_URL_HOST)),
        ]);
        if ('' !== $host && !in_array($host, $site_hosts, true)) {
            return ['type' => 'external', 'url' => strtok($absolute, '#')];
        }

        $path = rawurldecode(isset($parts['path']) ? $parts['path'] : '');
        $uploads = wp_get_upload_dir();
        $uploads_path = trailingslashit((string) wp_parse_url($uploads['baseurl'], PHP_URL_PATH));
        if (0 === strpos($path, $uploads_path)) {
            $relative = strtolower(substr($path, strlen($uploads_path)));
            $map = $this->attachment_map();
            if (isset($map[$relative])) {
                return ['type' => 'attachment', 'id' => $map[$relative]];
            }
        }

        $origin = isset($parts['scheme'], $parts['host']) ? $parts['scheme'] . '://' . $parts['host'] . (isset($parts['port']) ? ':' . $parts['port'] : '') : home_url();
        return ['type' => 'local', 'key' => $path, 'url' => $origin . $path, 'file' => $this->local_file($path, $uploads)];
    }

    /** @return array<string, int> */
    private function attachment_map() {
        if (null === $this->attachment_map) {
            global $wpdb;
            // One query per scan request, kept in $this->attachment_map for the rest of it.
            // phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching
            $rows = $wpdb->get_results(
                "SELECT post_id, meta_value FROM {$wpdb->postmeta} WHERE meta_key = '_wp_attached_file' AND meta_value LIKE '%.pdf'"
            );
            $this->attachment_map = [];
            foreach ($rows as $row) {
                $this->attachment_map[strtolower($row->meta_value)] = (int) $row->post_id;
            }
        }
        return $this->attachment_map;
    }

    /** Maps a URL path to a PDF on disk inside the WordPress or uploads directory, or null. */
    private function local_file($path, array $uploads) {
        $candidates = [];
        $uploads_path = trailingslashit((string) wp_parse_url($uploads['baseurl'], PHP_URL_PATH));
        if (0 === strpos($path, $uploads_path)) {
            $candidates[] = trailingslashit($uploads['basedir']) . substr($path, strlen($uploads_path));
        }
        $site_path = untrailingslashit((string) wp_parse_url(site_url(), PHP_URL_PATH));
        if ('' === $site_path || 0 === strpos($path, $site_path . '/')) {
            $candidates[] = ABSPATH . ltrim(substr($path, strlen($site_path)), '/');
        }

        $allowed = array_filter([realpath(ABSPATH), realpath($uploads['basedir'])]);
        foreach ($candidates as $candidate) {
            $real = realpath($candidate);
            if (!$real || !is_file($real) || !preg_match('/\.pdf$/i', $real)) {
                continue;
            }
            foreach ($allowed as $root) {
                if (0 === strpos($real, trailingslashit($root))) {
                    return $real;
                }
            }
        }
        return null;
    }

    /**
     * One row per PDF: media library files, then linked files outside the library.
     *
     * @return array<int, array{key: string, source: string, id: int, name: string, url: string,
     *     edit_url: string, status: string, analysis: array|null, linked_from: int[]}>
     */
    public function rows() {
        $ids = $this->pdf_attachment_ids();
        update_meta_cache('post', $ids);
        $rows = [];
        foreach ($ids as $id) {
            $analysis = get_post_meta($id, self::META, true);
            $analysis = is_array($analysis) ? $analysis : null;
            $file = get_attached_file($id);
            $title = get_the_title($id);
            $rows[] = [
                'key' => 'a' . $id,
                'source' => 'library',
                'id' => $id,
                'name' => '' !== $title ? $title : wp_basename((string) $file),
                'url' => (string) wp_get_attachment_url($id),
                'edit_url' => (string) get_edit_post_link($id, 'raw'),
                'status' => $analysis ? $analysis['status'] : self::STATUS_NOT_CHECKED,
                'analysis' => $analysis,
                'linked_from' => self::post_ids(get_post_meta($id, self::LINKS_META, true)),
            ];
        }
        foreach ($this->other_pdfs()['local'] as $key => $entry) {
            $analysis = is_array($entry['analysis']) ? $entry['analysis'] : null;
            if (empty($entry['file'])) {
                $status = self::STATUS_MISSING;
            } else {
                $status = $analysis ? $analysis['status'] : self::STATUS_NOT_CHECKED;
            }
            $rows[] = [
                'key' => 'u' . md5($key),
                'source' => 'outside',
                'id' => 0,
                'name' => wp_basename($key),
                'url' => $entry['url'],
                'edit_url' => '',
                'status' => $status,
                'analysis' => $analysis,
                'linked_from' => self::post_ids($entry['linked_from']),
            ];
        }
        return $rows;
    }

    /** Normalizes a stored list of post IDs; an empty meta value becomes an empty list. */
    private static function post_ids($value) {
        return is_array($value) ? array_values(array_filter(array_map('intval', $value))) : [];
    }

    /** Statuses that mean the PDF needs remediation work. */
    public static function needs_work($status) {
        return in_array($status, [Make_PDF_Accessible_PDF_Analyzer::STATUS_UNTAGGED, Make_PDF_Accessible_PDF_Analyzer::STATUS_NO_TEXT], true);
    }

    /** Statuses where the file couldn't be checked. */
    public static function unchecked($status) {
        return in_array($status, [
            Make_PDF_Accessible_PDF_Analyzer::STATUS_ENCRYPTED,
            Make_PDF_Accessible_PDF_Analyzer::STATUS_TOO_LARGE,
            Make_PDF_Accessible_PDF_Analyzer::STATUS_UNREADABLE,
            self::STATUS_MISSING,
            self::STATUS_NOT_CHECKED,
        ], true);
    }

    /** Totals for the summary and cost estimate. */
    public function summary(array $rows) {
        $summary = [
            'files' => count($rows),
            'pages' => 0,
            'unknown_pages' => 0,
            'status' => [],
            'linked' => 0,
            'unlinked' => 0,
            'needs_work_files' => 0,
            'needs_work_pages' => 0,
            'unlinked_needs_work_pages' => 0,
            'missing_title' => 0,
            'missing_language' => 0,
            'forms' => 0,
            'external' => count($this->other_pdfs()['external']),
        ];
        foreach ($rows as $row) {
            $status = $row['status'];
            $summary['status'][$status] = (isset($summary['status'][$status]) ? $summary['status'][$status] : 0) + 1;
            $pages = $row['analysis'] && null !== $row['analysis']['pages'] ? (int) $row['analysis']['pages'] : null;
            if (null === $pages) {
                $summary['unknown_pages']++;
            } else {
                $summary['pages'] += $pages;
            }
            if (empty($row['linked_from'])) {
                $summary['unlinked']++;
            } else {
                $summary['linked']++;
            }

            if (self::needs_work($status)) {
                $summary['needs_work_files']++;
                $summary['needs_work_pages'] += (int) $pages;
                if (empty($row['linked_from'])) {
                    $summary['unlinked_needs_work_pages'] += (int) $pages;
                }
            }
            if ($row['analysis'] && !self::unchecked($status)) {
                $summary['missing_title'] += false === $row['analysis']['has_title'] ? 1 : 0;
                $summary['missing_language'] += false === $row['analysis']['has_language'] ? 1 : 0;
                $summary['forms'] += true === $row['analysis']['has_form'] ? 1 : 0;
            }
        }
        return $summary;
    }

    /** @return array{low: float, high: float} Per-page rates for the cost estimate. */
    public static function rates() {
        $rates = (array) apply_filters('make_pdf_accessible_inventory_rates', ['low' => 2.50, 'high' => 12.00]);
        return ['low' => (float) $rates['low'], 'high' => (float) $rates['high']];
    }

    public static function status_label($status) {
        $labels = [
            Make_PDF_Accessible_PDF_Analyzer::STATUS_TAGGED => __('Tagged', 'make-pdf-accessible'),
            Make_PDF_Accessible_PDF_Analyzer::STATUS_UNTAGGED => __('Untagged', 'make-pdf-accessible'),
            Make_PDF_Accessible_PDF_Analyzer::STATUS_NO_TEXT => __('No text layer (likely scanned)', 'make-pdf-accessible'),
            Make_PDF_Accessible_PDF_Analyzer::STATUS_ENCRYPTED => __('Encrypted, couldn’t check', 'make-pdf-accessible'),
            Make_PDF_Accessible_PDF_Analyzer::STATUS_TOO_LARGE => __('Too large to check here', 'make-pdf-accessible'),
            Make_PDF_Accessible_PDF_Analyzer::STATUS_UNREADABLE => __('Couldn’t read', 'make-pdf-accessible'),
            self::STATUS_MISSING => __('Linked file not found', 'make-pdf-accessible'),
            self::STATUS_NOT_CHECKED => __('Not checked yet', 'make-pdf-accessible'),
        ];
        return isset($labels[$status]) ? $labels[$status] : $status;
    }

    public function export_csv() {
        if (!current_user_can(self::capability())) {
            wp_die(esc_html__('You don’t have permission to export the PDF inventory.', 'make-pdf-accessible'), '', ['response' => 403]);
        }
        check_admin_referer('make_pdf_accessible_inventory_csv');

        nocache_headers();
        header('Content-Type: text/csv; charset=utf-8');
        header('Content-Disposition: attachment; filename="pdf-inventory-' . gmdate('Y-m-d') . '.csv"');

        $csv = "\xEF\xBB\xBF" . self::csv_line(['File', 'URL', 'Location', 'Status', 'Pages', 'Size (bytes)', 'PDF title', 'Language', 'Fillable form', 'Encrypted', 'PDF/UA claimed', 'Linked from (count)', 'Linked from', 'Checked']);
        foreach ($this->rows() as $row) {
            $a = $row['analysis'];
            $links = array_filter(array_map('get_permalink', $row['linked_from']));
            $csv .= self::csv_line([
                $row['name'],
                $row['url'],
                'library' === $row['source'] ? 'Media library' : 'Outside media library',
                self::status_label($row['status']),
                $a && null !== $a['pages'] ? $a['pages'] : '',
                $a ? $a['size'] : '',
                $a ? self::yes_no_unknown($a['has_title'], $a['title']) : '',
                $a ? self::yes_no_unknown($a['has_language'], $a['language']) : '',
                $a ? self::yes_no_unknown($a['has_form']) : '',
                $a ? ($a['encrypted'] ? 'Yes' : 'No') : '',
                $a ? ($a['pdf_ua'] ? 'Yes' : 'No') : '',
                count($row['linked_from']),
                implode(' ', $links),
                $a && !empty($a['checked_at']) ? gmdate('Y-m-d H:i', $a['checked_at']) . ' UTC' : '',
            ]);
        }
        echo $csv; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- A CSV download, not HTML; csv_line() quotes every cell and neutralizes formulas.
        exit;
    }

    private static function yes_no_unknown($value, $detail = '') {
        if (null === $value) {
            return 'Unknown';
        }
        if ($value && '' !== $detail) {
            return $detail;
        }
        return $value ? 'Yes' : 'No';
    }

    /** One RFC 4180 CSV line: cells quoted when needed, formulas neutralized. */
    public static function csv_line(array $cells) {
        $out = [];
        foreach ($cells as $cell) {
            $cell = self::csv_cell($cell);
            $out[] = preg_match('/[",\r\n]/', $cell) ? '"' . str_replace('"', '""', $cell) . '"' : $cell;
        }
        return implode(',', $out) . "\r\n";
    }

    /** Stops spreadsheet apps from treating a cell as a formula. */
    public static function csv_cell($value) {
        $value = (string) $value;
        return preg_match('/^[=+\-@\t\r]/', $value) ? "'" . $value : $value;
    }
}
