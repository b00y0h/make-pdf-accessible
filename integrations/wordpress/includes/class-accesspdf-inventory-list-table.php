<?php
/**
 * The table of PDFs on the PDF Inventory screen. Loaded only when that screen renders.
 */

if (!defined('ABSPATH')) {
    exit;
}

class AccessPDF_Inventory_List_Table extends WP_List_Table {
    const PER_PAGE = 50;

    /** @var array[] */
    private $all_rows;

    public function __construct(array $rows) {
        parent::__construct(['singular' => 'pdf', 'plural' => 'pdfs', 'ajax' => false]);
        $this->all_rows = array_values($rows);
    }

    public function get_columns() {
        return [
            'file' => __('File', 'accesspdf'),
            'status' => __('Status', 'accesspdf'),
            'pages' => __('Pages', 'accesspdf'),
            'checks' => __('Other checks', 'accesspdf'),
            'linked' => __('Linked from', 'accesspdf'),
        ];
    }

    protected function get_sortable_columns() {
        return [
            'file' => ['file', false],
            'status' => ['status', false],
            'pages' => ['pages', true],
            'linked' => ['linked', true],
        ];
    }

    private function views_list() {
        return [
            'all' => __('All', 'accesspdf'),
            'needs_work' => __('Needs work', 'accesspdf'),
            'no_text' => __('No text layer', 'accesspdf'),
            'tagged' => __('Tagged', 'accesspdf'),
            'unlinked' => __('Not linked', 'accesspdf'),
            'unchecked' => __('Couldn’t check', 'accesspdf'),
        ];
    }

    /** A view or sort parameter from the URL. These only change what's displayed, so no nonce is involved. */
    public static function query_param($name) {
        // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Read-only display parameter.
        return isset($_GET[$name]) ? sanitize_key(wp_unslash($_GET[$name])) : '';
    }

    private function current_view() {
        $view = self::query_param('view');
        return isset($this->views_list()[$view]) ? $view : 'all';
    }

    private function matches(array $row, $view) {
        switch ($view) {
            case 'needs_work':
                return AccessPDF_Inventory::needs_work($row['status']);
            case 'no_text':
                return AccessPDF_PDF_Analyzer::STATUS_NO_TEXT === $row['status'];
            case 'tagged':
                return AccessPDF_PDF_Analyzer::STATUS_TAGGED === $row['status'];
            case 'unlinked':
                return empty($row['linked_from']);
            case 'unchecked':
                return AccessPDF_Inventory::unchecked($row['status']);
        }
        return true;
    }

    protected function get_views() {
        $current = $this->current_view();
        $views = [];
        foreach ($this->views_list() as $view => $label) {
            $count = 0;
            foreach ($this->all_rows as $row) {
                $count += $this->matches($row, $view) ? 1 : 0;
            }
            $views[$view] = sprintf(
                '<a href="%s"%s>%s <span class="count">(%s)</span></a>',
                esc_url(AccessPDF_Inventory_Page::url('all' === $view ? [] : ['view' => $view])),
                $view === $current ? ' class="current" aria-current="page"' : '',
                esc_html($label),
                esc_html(number_format_i18n($count))
            );
        }
        return $views;
    }

    public function prepare_items() {
        $view = $this->current_view();
        $rows = array_values(array_filter($this->all_rows, function ($row) use ($view) {
            return $this->matches($row, $view);
        }));

        $orderby = self::query_param('orderby');
        $desc = 'desc' === self::query_param('order');
        usort($rows, function ($a, $b) use ($orderby, $desc) {
            switch ($orderby) {
                case 'pages':
                    $cmp = $this->pages($a) <=> $this->pages($b);
                    break;
                case 'linked':
                    $cmp = count($a['linked_from']) <=> count($b['linked_from']);
                    break;
                case 'status':
                    $cmp = strcmp(AccessPDF_Inventory::status_label($a['status']), AccessPDF_Inventory::status_label($b['status']));
                    break;
                default:
                    $cmp = strcasecmp($a['name'], $b['name']);
            }
            return $desc ? -$cmp : $cmp;
        });

        $total = count($rows);
        $page = $this->get_pagenum();
        $this->items = array_slice($rows, ($page - 1) * self::PER_PAGE, self::PER_PAGE);
        $this->set_pagination_args(['total_items' => $total, 'per_page' => self::PER_PAGE]);
        $this->_column_headers = [$this->get_columns(), [], $this->get_sortable_columns(), 'file'];
    }

    private function pages(array $row) {
        return $row['analysis'] && null !== $row['analysis']['pages'] ? (int) $row['analysis']['pages'] : -1;
    }

    protected function column_file($row) {
        $link = '' !== $row['edit_url'] ? $row['edit_url'] : $row['url'];
        $out = sprintf('<strong><a href="%s">%s</a></strong>', esc_url($link), esc_html($row['name']));
        $details = [];
        if ('outside' === $row['source']) {
            $details[] = esc_html__('Not in the media library', 'accesspdf');
        }
        if ('' !== $row['url']) {
            $details[] = sprintf('<a href="%s">%s</a>', esc_url($row['url']), esc_html__('Open file', 'accesspdf'));
        }
        return $out . ($details ? '<br />' . implode(' · ', $details) : '');
    }

    protected function column_status($row) {
        $label = esc_html(AccessPDF_Inventory::status_label($row['status']));
        if (AccessPDF_Inventory::needs_work($row['status'])) {
            return '<strong>' . $label . '</strong>';
        }
        if ($row['analysis'] && !empty($row['analysis']['error'])) {
            $label .= '<br /><span class="description">' . esc_html($row['analysis']['error']) . '</span>';
        }
        return $label;
    }

    protected function column_pages($row) {
        $pages = $this->pages($row);
        return $pages < 0 ? esc_html__('Unknown', 'accesspdf') : esc_html(number_format_i18n($pages));
    }

    protected function column_checks($row) {
        $a = $row['analysis'];
        if (!$a || AccessPDF_Inventory::unchecked($row['status'])) {
            return esc_html__('Not available', 'accesspdf');
        }
        $notes = [];
        if (false === $a['has_title']) {
            $notes[] = __('No document title', 'accesspdf');
        }
        if (false === $a['has_language']) {
            $notes[] = __('No document language', 'accesspdf');
        }
        if (true === $a['has_form']) {
            $notes[] = __('Fillable form', 'accesspdf');
        }
        if ($a['encrypted']) {
            $notes[] = __('Encrypted', 'accesspdf');
        }
        if ($a['pdf_ua']) {
            $notes[] = __('Claims PDF/UA', 'accesspdf');
        }
        return $notes ? esc_html(implode(', ', $notes)) : esc_html__('No other issues found', 'accesspdf');
    }

    protected function column_linked($row) {
        if (empty($row['linked_from'])) {
            return esc_html__('Not linked', 'accesspdf');
        }
        $links = [];
        foreach (array_slice($row['linked_from'], 0, 3) as $post_id) {
            $title = get_the_title($post_id);
            $links[] = sprintf(
                '<a href="%s">%s</a>',
                esc_url((string) get_permalink($post_id)),
                /* translators: %d: post ID */
                esc_html('' !== $title ? $title : sprintf(__('Post %d', 'accesspdf'), $post_id))
            );
        }
        $more = count($row['linked_from']) - count($links);
        if ($more > 0) {
            /* translators: %s: number of additional pages */
            $links[] = esc_html(sprintf(__('and %s more', 'accesspdf'), number_format_i18n($more)));
        }
        return implode('<br />', $links);
    }

    public function no_items() {
        esc_html_e('No PDFs match this view.', 'accesspdf');
    }
}
