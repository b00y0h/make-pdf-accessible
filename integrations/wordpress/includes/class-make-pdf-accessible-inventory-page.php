<?php
/**
 * Media → PDF Inventory admin screen.
 */

if (!defined('ABSPATH')) {
    exit;
}

class Make_PDF_Accessible_Inventory_Page {
    const SLUG = 'make-pdf-accessible-inventory';

    /** @var Make_PDF_Accessible_Inventory */
    private $inventory;

    /** @var string */
    private $hook = '';

    public function __construct(Make_PDF_Accessible_Inventory $inventory) {
        $this->inventory = $inventory;
    }

    public function register() {
        add_action('admin_menu', [$this, 'add_page']);
        add_action('admin_enqueue_scripts', [$this, 'enqueue']);
    }

    public static function url(array $args = []) {
        return add_query_arg(array_merge(['page' => self::SLUG], $args), admin_url('upload.php'));
    }

    public function add_page() {
        $this->hook = (string) add_media_page(
            __('PDF Inventory', 'make-pdf-accessible'),
            __('PDF Inventory', 'make-pdf-accessible'),
            Make_PDF_Accessible_Inventory::capability(),
            self::SLUG,
            [$this, 'render']
        );
    }

    public function enqueue($hook) {
        if ($hook !== $this->hook) {
            return;
        }
        // Links stacked in table cells need 24px targets (WCAG 2.2, 2.5.8).
        wp_register_style('make-pdf-accessible-inventory', false, [], MAKE_PDF_ACCESSIBLE_VERSION);
        wp_enqueue_style('make-pdf-accessible-inventory');
        wp_add_inline_style('make-pdf-accessible-inventory', '.make-pdf-accessible-inventory .column-file a, .make-pdf-accessible-inventory .column-linked a { display: inline-block; min-height: 24px; line-height: 24px; }');
        wp_enqueue_script('make-pdf-accessible-inventory', plugins_url('assets/inventory.js', MAKE_PDF_ACCESSIBLE_PLUGIN_FILE), [], MAKE_PDF_ACCESSIBLE_VERSION, true);
        wp_localize_script('make-pdf-accessible-inventory', 'makePdfAccessibleInventory', [
            'restUrl' => esc_url_raw(rest_url('make-pdf-accessible/v1/inventory/scan')),
            'nonce' => wp_create_nonce('wp_rest'),
            'i18n' => [
                'starting' => __('Scanning…', 'make-pdf-accessible'),
                'of' => __('of', 'make-pdf-accessible'),
                'done' => __('Scan complete. Loading results…', 'make-pdf-accessible'),
                'failed' => __('The scan stopped:', 'make-pdf-accessible'),
            ],
        ]);
    }

    public function render() {
        if (!current_user_can(Make_PDF_Accessible_Inventory::capability())) {
            wp_die(esc_html__('You don’t have permission to view the PDF inventory.', 'make-pdf-accessible'), '', ['response' => 403]);
        }
        require_once ABSPATH . 'wp-admin/includes/class-wp-list-table.php';
        require_once __DIR__ . '/class-make-pdf-accessible-inventory-list-table.php';

        $rows = $this->inventory->rows();
        $summary = $this->inventory->summary($rows);
        $state = get_option(Make_PDF_Accessible_Inventory::STATE_OPTION);
        $last_scan = is_array($state) && !empty($state['last_scan']) ? (int) $state['last_scan'] : 0;
        $table = new Make_PDF_Accessible_Inventory_List_Table($rows);
        $table->prepare_items();
        ?>
        <div class="wrap make-pdf-accessible-inventory">
            <h1><?php esc_html_e('PDF Inventory', 'make-pdf-accessible'); ?></h1>
            <p><?php esc_html_e('Every PDF in your media library and every PDF your published content links to, checked for the basics screen readers need. Files are checked on this server and nothing is sent anywhere.', 'make-pdf-accessible'); ?></p>

            <p>
                <button type="button" class="button button-primary" id="make-pdf-accessible-scan" disabled>
                    <?php $last_scan ? esc_html_e('Scan again', 'make-pdf-accessible') : esc_html_e('Scan PDFs', 'make-pdf-accessible'); ?>
                </button>
                <span id="make-pdf-accessible-scan-status" role="status" style="margin-left: 8px;">
                    <?php
                    if ($last_scan) {
                        /* translators: %s: how long ago, e.g. "5 mins" */
                        printf(esc_html__('Last full scan %s ago.', 'make-pdf-accessible'), esc_html(human_time_diff($last_scan)));
                    }
                    ?>
                </span>
            </p>
            <p><progress id="make-pdf-accessible-scan-progress" max="100" value="0" aria-label="<?php esc_attr_e('Scan progress', 'make-pdf-accessible'); ?>" hidden></progress></p>
            <noscript><p><?php esc_html_e('Scanning needs JavaScript.', 'make-pdf-accessible'); ?></p></noscript>

            <?php if (!$last_scan && 0 === $summary['files']) : ?>
                <p><?php esc_html_e('Run a scan to see your PDFs.', 'make-pdf-accessible'); ?></p>
            <?php else : ?>
                <?php $this->render_summary($summary, $last_scan); ?>
                <?php $this->render_estimate($summary); ?>

                <h2><?php esc_html_e('All PDFs', 'make-pdf-accessible'); ?></h2>
                <?php $table->views(); ?>
                <form method="get">
                    <input type="hidden" name="page" value="<?php echo esc_attr(self::SLUG); ?>" />
                    <?php $view = Make_PDF_Accessible_Inventory_List_Table::query_param('view'); ?>
                    <?php if ('' !== $view) : ?>
                        <input type="hidden" name="view" value="<?php echo esc_attr($view); ?>" />
                    <?php endif; ?>
                    <?php $table->display(); ?>
                </form>

                <form method="post" action="<?php echo esc_url(admin_url('admin-post.php')); ?>">
                    <input type="hidden" name="action" value="make_pdf_accessible_inventory_csv" />
                    <?php wp_nonce_field('make_pdf_accessible_inventory_csv'); ?>
                    <?php submit_button(__('Download CSV', 'make-pdf-accessible'), 'secondary', 'submit', false); ?>
                </form>

                <h2><?php esc_html_e('What this report doesn’t check yet', 'make-pdf-accessible'); ?></h2>
                <ul style="list-style: disc; padding-left: 20px;">
                    <li><?php esc_html_e('Whether existing tags are correct, such as reading order, table headers and alt text. “Tagged” only means tags exist.', 'make-pdf-accessible'); ?></li>
                    <li><?php esc_html_e('Links in menus, widgets and page-builder data. Only post and page content is searched for links.', 'make-pdf-accessible'); ?></li>
                    <li><?php esc_html_e('PDFs hosted on other sites. They are counted but not opened.', 'make-pdf-accessible'); ?></li>
                    <li><?php esc_html_e('Files stored off this server, for example by a media offload plugin. They show as “Couldn’t read”.', 'make-pdf-accessible'); ?></li>
                </ul>
            <?php endif; ?>
        </div>
        <?php
    }

    private function render_summary(array $s, $last_scan) {
        $count = function ($status) use ($s) {
            return isset($s['status'][$status]) ? (int) $s['status'][$status] : 0;
        };
        $unchecked = 0;
        foreach ($s['status'] as $status => $n) {
            $unchecked += Make_PDF_Accessible_Inventory::unchecked($status) ? $n : 0;
        }
        $pages = sprintf(
            /* translators: %s: number of pages */
            _n('%s page', '%s pages', $s['pages'], 'make-pdf-accessible'),
            number_format_i18n($s['pages'])
        );
        if ($s['unknown_pages']) {
            /* translators: %s: number of PDFs */
            $pages .= ', ' . sprintf(__('plus %s with an unknown page count', 'make-pdf-accessible'), number_format_i18n($s['unknown_pages']));
        }
        $rows = [
            [__('PDFs found', 'make-pdf-accessible'), number_format_i18n($s['files']) . ' (' . $pages . ')'],
            [__('Tagged', 'make-pdf-accessible'), number_format_i18n($count(Make_PDF_Accessible_PDF_Analyzer::STATUS_TAGGED))],
            [__('Untagged', 'make-pdf-accessible'), number_format_i18n($count(Make_PDF_Accessible_PDF_Analyzer::STATUS_UNTAGGED))],
            [__('No text layer (likely scanned)', 'make-pdf-accessible'), number_format_i18n($count(Make_PDF_Accessible_PDF_Analyzer::STATUS_NO_TEXT))],
            [__('Couldn’t check', 'make-pdf-accessible'), number_format_i18n($unchecked)],
            [__('Linked from published content', 'make-pdf-accessible'), number_format_i18n($s['linked'])],
            [__('Not linked from published content', 'make-pdf-accessible'), number_format_i18n($s['unlinked'])],
            [__('Missing a document title', 'make-pdf-accessible'), number_format_i18n($s['missing_title'])],
            [__('Missing a document language', 'make-pdf-accessible'), number_format_i18n($s['missing_language'])],
            [__('Fillable forms', 'make-pdf-accessible'), number_format_i18n($s['forms'])],
            [__('Links to PDFs on other sites (not checked)', 'make-pdf-accessible'), number_format_i18n($s['external'])],
        ];
        ?>
        <h2><?php esc_html_e('Summary', 'make-pdf-accessible'); ?></h2>
        <?php if (!$last_scan) : ?>
            <p><?php esc_html_e('New uploads are checked automatically. Run a full scan to include older files and find which pages link to each PDF.', 'make-pdf-accessible'); ?></p>
        <?php endif; ?>
        <table class="widefat striped" style="max-width: 44rem;">
            <tbody>
                <?php foreach ($rows as $row) : ?>
                    <tr>
                        <th scope="row"><?php echo esc_html($row[0]); ?></th>
                        <td><?php echo esc_html($row[1]); ?></td>
                    </tr>
                <?php endforeach; ?>
            </tbody>
        </table>
        <?php
    }

    private function render_estimate(array $s) {
        $rates = Make_PDF_Accessible_Inventory::rates();
        $money = function ($amount) {
            return '$' . number_format_i18n($amount, 0);
        };
        ?>
        <h2><?php esc_html_e('Estimated cost to fix', 'make-pdf-accessible'); ?></h2>
        <?php if (0 === $s['needs_work_files']) : ?>
            <p><?php esc_html_e('No untagged or scanned PDFs were found.', 'make-pdf-accessible'); ?></p>
            <?php return; ?>
        <?php endif; ?>
        <p>
            <?php
            printf(
                /* translators: 1: number of PDFs, 2: number of pages, 3: low rate, 4: high rate, 5: low total, 6: high total */
                esc_html__('%1$s PDFs with %2$s pages need tagging or a text layer. At typical manual remediation rates of %3$s to %4$s per page, that’s about %5$s to %6$s.', 'make-pdf-accessible'),
                esc_html(number_format_i18n($s['needs_work_files'])),
                esc_html(number_format_i18n($s['needs_work_pages'])),
                esc_html('$' . number_format_i18n($rates['low'], 2)),
                esc_html('$' . number_format_i18n($rates['high'], 2)),
                esc_html($money($s['needs_work_pages'] * $rates['low'])),
                esc_html($money($s['needs_work_pages'] * $rates['high']))
            );
            ?>
        </p>
        <?php if ($s['unlinked_needs_work_pages'] > 0) : ?>
            <?php $kept = $s['needs_work_pages'] - $s['unlinked_needs_work_pages']; ?>
            <p>
                <?php
                printf(
                    /* translators: 1: number of pages, 2: low total, 3: high total */
                    esc_html__('%1$s of those pages are in PDFs that no published content links to. Archiving or removing those PDFs instead of fixing them would bring the estimate to about %2$s to %3$s. Check before removing anything: people may still reach a file through search engines or bookmarks.', 'make-pdf-accessible'),
                    esc_html(number_format_i18n($s['unlinked_needs_work_pages'])),
                    esc_html($money($kept * $rates['low'])),
                    esc_html($money($kept * $rates['high']))
                );
                ?>
            </p>
        <?php endif; ?>
        <p class="description"><?php esc_html_e('Tagged PDFs aren’t included in the estimate, but they can still have problems. This report only checks that tags exist.', 'make-pdf-accessible'); ?></p>
        <?php
    }
}
