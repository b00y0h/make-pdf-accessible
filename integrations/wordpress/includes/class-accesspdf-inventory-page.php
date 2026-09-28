<?php
/**
 * Media → PDF Inventory admin screen.
 */

if (!defined('ABSPATH')) {
    exit;
}

class AccessPDF_Inventory_Page {
    const SLUG = 'accesspdf-inventory';

    /** @var AccessPDF_Inventory */
    private $inventory;

    /** @var string */
    private $hook = '';

    public function __construct(AccessPDF_Inventory $inventory) {
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
            __('PDF Inventory', 'accesspdf'),
            __('PDF Inventory', 'accesspdf'),
            AccessPDF_Inventory::capability(),
            self::SLUG,
            [$this, 'render']
        );
    }

    public function enqueue($hook) {
        if ($hook !== $this->hook) {
            return;
        }
        // Links stacked in table cells need 24px targets (WCAG 2.2, 2.5.8).
        wp_register_style('accesspdf-inventory', false, [], ACCESSPDF_VERSION);
        wp_enqueue_style('accesspdf-inventory');
        wp_add_inline_style('accesspdf-inventory', '.accesspdf-inventory .column-file a, .accesspdf-inventory .column-linked a { display: inline-block; min-height: 24px; line-height: 24px; }');
        wp_enqueue_script('accesspdf-inventory', plugins_url('assets/inventory.js', ACCESSPDF_PLUGIN_FILE), [], ACCESSPDF_VERSION, true);
        wp_localize_script('accesspdf-inventory', 'accesspdfInventory', [
            'restUrl' => esc_url_raw(rest_url('accesspdf/v1/inventory/scan')),
            'nonce' => wp_create_nonce('wp_rest'),
            'i18n' => [
                'starting' => __('Scanning…', 'accesspdf'),
                'of' => __('of', 'accesspdf'),
                'done' => __('Scan complete. Loading results…', 'accesspdf'),
                'failed' => __('The scan stopped:', 'accesspdf'),
            ],
        ]);
    }

    public function render() {
        if (!current_user_can(AccessPDF_Inventory::capability())) {
            wp_die(esc_html__('You don’t have permission to view the PDF inventory.', 'accesspdf'), '', ['response' => 403]);
        }
        require_once ABSPATH . 'wp-admin/includes/class-wp-list-table.php';
        require_once __DIR__ . '/class-accesspdf-inventory-list-table.php';

        $rows = $this->inventory->rows();
        $summary = $this->inventory->summary($rows);
        $state = get_option(AccessPDF_Inventory::STATE_OPTION);
        $last_scan = is_array($state) && !empty($state['last_scan']) ? (int) $state['last_scan'] : 0;
        $table = new AccessPDF_Inventory_List_Table($rows);
        $table->prepare_items();
        ?>
        <div class="wrap accesspdf-inventory">
            <h1><?php esc_html_e('PDF Inventory', 'accesspdf'); ?></h1>
            <p><?php esc_html_e('Every PDF in your media library and every PDF your published content links to, checked for the basics screen readers need. Files are checked on this server and nothing is sent anywhere.', 'accesspdf'); ?></p>

            <p>
                <button type="button" class="button button-primary" id="accesspdf-scan" disabled>
                    <?php $last_scan ? esc_html_e('Scan again', 'accesspdf') : esc_html_e('Scan PDFs', 'accesspdf'); ?>
                </button>
                <span id="accesspdf-scan-status" role="status" style="margin-left: 8px;">
                    <?php
                    if ($last_scan) {
                        /* translators: %s: how long ago, e.g. "5 mins" */
                        printf(esc_html__('Last full scan %s ago.', 'accesspdf'), esc_html(human_time_diff($last_scan)));
                    }
                    ?>
                </span>
            </p>
            <p><progress id="accesspdf-scan-progress" max="100" value="0" aria-label="<?php esc_attr_e('Scan progress', 'accesspdf'); ?>" hidden></progress></p>
            <noscript><p><?php esc_html_e('Scanning needs JavaScript.', 'accesspdf'); ?></p></noscript>

            <?php if (!$last_scan && 0 === $summary['files']) : ?>
                <p><?php esc_html_e('Run a scan to see your PDFs.', 'accesspdf'); ?></p>
            <?php else : ?>
                <?php $this->render_summary($summary, $last_scan); ?>
                <?php $this->render_estimate($summary); ?>

                <h2><?php esc_html_e('All PDFs', 'accesspdf'); ?></h2>
                <?php $table->views(); ?>
                <form method="get">
                    <input type="hidden" name="page" value="<?php echo esc_attr(self::SLUG); ?>" />
                    <?php $view = AccessPDF_Inventory_List_Table::query_param('view'); ?>
                    <?php if ('' !== $view) : ?>
                        <input type="hidden" name="view" value="<?php echo esc_attr($view); ?>" />
                    <?php endif; ?>
                    <?php $table->display(); ?>
                </form>

                <form method="post" action="<?php echo esc_url(admin_url('admin-post.php')); ?>">
                    <input type="hidden" name="action" value="accesspdf_inventory_csv" />
                    <?php wp_nonce_field('accesspdf_inventory_csv'); ?>
                    <?php submit_button(__('Download CSV', 'accesspdf'), 'secondary', 'submit', false); ?>
                </form>

                <h2><?php esc_html_e('What this report doesn’t check yet', 'accesspdf'); ?></h2>
                <ul style="list-style: disc; padding-left: 20px;">
                    <li><?php esc_html_e('Whether existing tags are correct, such as reading order, table headers and alt text. “Tagged” only means tags exist.', 'accesspdf'); ?></li>
                    <li><?php esc_html_e('Links in menus, widgets and page-builder data. Only post and page content is searched for links.', 'accesspdf'); ?></li>
                    <li><?php esc_html_e('PDFs hosted on other sites. They are counted but not opened.', 'accesspdf'); ?></li>
                    <li><?php esc_html_e('Files stored off this server, for example by a media offload plugin. They show as “Couldn’t read”.', 'accesspdf'); ?></li>
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
            $unchecked += AccessPDF_Inventory::unchecked($status) ? $n : 0;
        }
        $pages = sprintf(
            /* translators: %s: number of pages */
            _n('%s page', '%s pages', $s['pages'], 'accesspdf'),
            number_format_i18n($s['pages'])
        );
        if ($s['unknown_pages']) {
            /* translators: %s: number of PDFs */
            $pages .= ', ' . sprintf(__('plus %s with an unknown page count', 'accesspdf'), number_format_i18n($s['unknown_pages']));
        }
        $rows = [
            [__('PDFs found', 'accesspdf'), number_format_i18n($s['files']) . ' (' . $pages . ')'],
            [__('Tagged', 'accesspdf'), number_format_i18n($count(AccessPDF_PDF_Analyzer::STATUS_TAGGED))],
            [__('Untagged', 'accesspdf'), number_format_i18n($count(AccessPDF_PDF_Analyzer::STATUS_UNTAGGED))],
            [__('No text layer (likely scanned)', 'accesspdf'), number_format_i18n($count(AccessPDF_PDF_Analyzer::STATUS_NO_TEXT))],
            [__('Couldn’t check', 'accesspdf'), number_format_i18n($unchecked)],
            [__('Linked from published content', 'accesspdf'), number_format_i18n($s['linked'])],
            [__('Not linked from published content', 'accesspdf'), number_format_i18n($s['unlinked'])],
            [__('Missing a document title', 'accesspdf'), number_format_i18n($s['missing_title'])],
            [__('Missing a document language', 'accesspdf'), number_format_i18n($s['missing_language'])],
            [__('Fillable forms', 'accesspdf'), number_format_i18n($s['forms'])],
            [__('Links to PDFs on other sites (not checked)', 'accesspdf'), number_format_i18n($s['external'])],
        ];
        ?>
        <h2><?php esc_html_e('Summary', 'accesspdf'); ?></h2>
        <?php if (!$last_scan) : ?>
            <p><?php esc_html_e('New uploads are checked automatically. Run a full scan to include older files and find which pages link to each PDF.', 'accesspdf'); ?></p>
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
        $rates = AccessPDF_Inventory::rates();
        $money = function ($amount) {
            return '$' . number_format_i18n($amount, 0);
        };
        ?>
        <h2><?php esc_html_e('Estimated cost to fix', 'accesspdf'); ?></h2>
        <?php if (0 === $s['needs_work_files']) : ?>
            <p><?php esc_html_e('No untagged or scanned PDFs were found.', 'accesspdf'); ?></p>
            <?php return; ?>
        <?php endif; ?>
        <p>
            <?php
            printf(
                /* translators: 1: number of PDFs, 2: number of pages, 3: low rate, 4: high rate, 5: low total, 6: high total */
                esc_html__('%1$s PDFs with %2$s pages need tagging or a text layer. At typical manual remediation rates of %3$s to %4$s per page, that’s about %5$s to %6$s.', 'accesspdf'),
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
                    esc_html__('%1$s of those pages are in PDFs that no published content links to. Archiving or removing those PDFs instead of fixing them would bring the estimate to about %2$s to %3$s. Check before removing anything: people may still reach a file through search engines or bookmarks.', 'accesspdf'),
                    esc_html(number_format_i18n($s['unlinked_needs_work_pages'])),
                    esc_html($money($kept * $rates['low'])),
                    esc_html($money($kept * $rates['high']))
                );
                ?>
            </p>
        <?php endif; ?>
        <p class="description"><?php esc_html_e('Tagged PDFs aren’t included in the estimate, but they can still have problems. This report only checks that tags exist.', 'accesspdf'); ?></p>
        <?php
    }
}
