<?php
/**
 * Seeds the test site. Run once by the blueprint after the plugin is activated,
 * so uploads below also exercise the inventory's check-on-upload hook.
 */

require_once __DIR__ . '/../../fixtures/pdf-builder.php';

$ids = [];

// Markdown: a page with the block types the converter handles.
$admissions = <<<'HTML'
<!-- wp:heading --><h2 class="wp-block-heading">Application deadlines</h2><!-- /wp:heading -->
<!-- wp:paragraph --><p>Apply by <strong>March 1</strong>. See the <a href="/financial-aid/">financial aid page</a>.</p><!-- /wp:paragraph -->
<!-- wp:list --><ul><li>Transcripts</li><li>Two recommendation letters</li></ul><!-- /wp:list -->
<!-- wp:table --><figure class="wp-block-table"><table><thead><tr><th>Program</th><th>Tuition</th></tr></thead><tbody><tr><td>Nursing</td><td>$12,000</td></tr></tbody></table></figure><!-- /wp:table -->
<!-- wp:image --><figure class="wp-block-image"><img src="/wp-content/uploads/quad.jpg" alt="Students on the quad"/></figure><!-- /wp:image -->
<!-- wp:shortcode -->[e2e_shortcode]<!-- /wp:shortcode -->
HTML;
$ids['admissions'] = wp_insert_post(['post_type' => 'page', 'post_status' => 'publish', 'post_title' => 'Admissions & “Deadlines”', 'post_name' => 'admissions', 'post_content' => $admissions]);
$ids['transfer'] = wp_insert_post(['post_type' => 'page', 'post_status' => 'publish', 'post_title' => 'Transfer', 'post_name' => 'transfer', 'post_parent' => $ids['admissions'], 'post_content' => '<p>Transfer credits.</p>']);
$ids['news'] = wp_insert_post(['post_type' => 'post', 'post_status' => 'publish', 'post_title' => 'Campus news', 'post_name' => 'campus-news', 'post_content' => '<p>News body.</p>']);
$ids['draft'] = wp_insert_post(['post_type' => 'post', 'post_status' => 'draft', 'post_title' => 'Draft', 'post_name' => 'secret-draft', 'post_content' => '<p>DRAFT-SECRET</p>']);
$ids['private'] = wp_insert_post(['post_type' => 'post', 'post_status' => 'private', 'post_title' => 'Private', 'post_name' => 'private-post', 'post_content' => '<p>PRIVATE-SECRET</p>']);
$ids['protected'] = wp_insert_post(['post_type' => 'post', 'post_status' => 'publish', 'post_title' => 'Protected', 'post_name' => 'protected-post', 'post_password' => 'pw', 'post_content' => '<p>PROTECTED-SECRET</p>']);
$ids['front'] = wp_insert_post(['post_type' => 'page', 'post_status' => 'publish', 'post_title' => 'Welcome', 'post_name' => 'welcome', 'post_content' => '<p>Front page body.</p>']);
update_option('show_on_front', 'page');
update_option('page_on_front', $ids['front']);

// Inventory: PDFs in the media library, uploaded after activation so they're checked on upload.
$pdfs = [
    'research-paper' => accesspdf_test_build_pdf(accesspdf_test_text_objects([], 14)),
    'structure-guide' => accesspdf_test_build_pdf(accesspdf_test_text_objects(['/StructTreeRoot 900 0 R', '/Lang (en-US)']) + [900 => '<< /Type /StructTreeRoot /K [] >>']),
    'scanned-flyer' => accesspdf_test_build_pdf(accesspdf_test_scanned_objects()),
    'aid-form' => accesspdf_test_build_pdf(accesspdf_test_text_objects(['/StructTreeRoot 900 0 R', '/Lang (FR)', '/AcroForm << /Fields [901 0 R] >>']) + [
        900 => '<< /Type /StructTreeRoot /K [] >>',
        901 => '<< /FT /Tx /T (name) /Subtype /Widget /Rect [0 0 100 20] >>',
    ]),
    'old-memo' => accesspdf_test_build_pdf(accesspdf_test_text_objects()),
    'encrypted-report' => accesspdf_test_encrypted_pdf(),
];
$url = [];
foreach ($pdfs as $name => $bytes) {
    $upload = wp_upload_bits("$name.pdf", null, $bytes);
    $ids[$name] = wp_insert_attachment(['post_mime_type' => 'application/pdf', 'post_title' => $name, 'post_status' => 'inherit'], $upload['file']);
    $url[$name] = wp_get_attachment_url($ids[$name]);
}

// A PDF outside the media library, the way FTP uploads land on many sites.
wp_mkdir_p(ABSPATH . 'files');
file_put_contents(ABSPATH . 'files/old-catalog.pdf', accesspdf_test_build_pdf(accesspdf_test_scanned_objects(4)));

$ids['pdf_links'] = wp_insert_post(['post_type' => 'page', 'post_status' => 'publish', 'post_title' => 'Forms and documents', 'post_name' => 'forms-and-documents', 'post_content' =>
    '<p><a href="' . $url['research-paper'] . '">Research paper</a></p>'
    . '<p><a href="' . $url['scanned-flyer'] . '">Scanned flyer</a></p>'
    . '<p><a href="/files/old-catalog.pdf">Old catalog</a> and <a href="/files/missing.pdf">a missing form</a></p>'
    . '<p><a href="https://example.org/guide.pdf">External guide</a></p>']);
$ids['library_news'] = wp_insert_post(['post_type' => 'post', 'post_status' => 'publish', 'post_title' => 'Library news', 'post_content' =>
    '<!-- wp:file --><div class="wp-block-file"><a href="' . wp_parse_url($url['structure-guide'], PHP_URL_PATH) . '?v=2&amp;x=1">Guide</a></div><!-- /wp:file -->']);
// Links from drafts don't count as "in use".
wp_update_post(['ID' => $ids['draft'], 'post_content' => '<p>DRAFT-SECRET</p><a href="' . $url['aid-form'] . '">Form</a>']);

wp_insert_user(['user_login' => 'sub', 'user_pass' => 'subpass', 'user_email' => 'sub@example.org', 'role' => 'subscriber']);
update_option('accesspdf_e2e_ids', $ids);
