<?php
/**
 * Tests for the PDF analyzer and the inventory's pure helpers.
 *
 * Run: php integrations/wordpress/tests/pdf-inventory-test.php
 * Needs only PHP with the zlib extension; WordPress is not loaded.
 */

require __DIR__ . '/fixtures/wp-shims.php';

require __DIR__ . '/../includes/class-accesspdf-pdf-analyzer.php';
require __DIR__ . '/../includes/class-accesspdf-inventory.php';
require __DIR__ . '/fixtures/pdf-builder.php';

$failures = 0;
$total = 0;

function check($name, $expected, $actual) {
    global $failures, $total;
    $total++;
    if ($expected === $actual) {
        echo "ok   $name\n";
        return;
    }
    $failures++;
    echo "FAIL $name\n--- expected\n" . var_export($expected, true) . "\n--- actual\n" . var_export($actual, true) . "\n";
}

/** Checks several fields of an analysis at once. */
function check_fields($name, array $expected, array $actual) {
    $actual = array_intersect_key($actual, $expected);
    ksort($expected);
    ksort($actual);
    check($name, $expected, $actual);
}

$analyzer = new AccessPDF_PDF_Analyzer();

// Basic classification
check_fields(
    'untagged text PDF',
    ['status' => 'untagged', 'pages' => 1, 'tagged' => false, 'has_text' => true, 'has_title' => false, 'has_language' => false, 'has_form' => false, 'encrypted' => false],
    $analyzer->analyze_bytes(accesspdf_test_build_pdf(accesspdf_test_text_objects()))
);

$tagged = accesspdf_test_text_objects(['/StructTreeRoot 6 0 R', '/MarkInfo << /Marked true >>', '/Lang (en-US)']);
$tagged[6] = '<< /Type /StructTreeRoot /K [] >>';
$tagged[7] = '<< /Title (Annual Report) /Producer (Test) >>';
check_fields(
    'tagged PDF with title and language',
    ['status' => 'tagged', 'tagged' => true, 'title' => 'Annual Report', 'has_title' => true, 'language' => 'en-US', 'has_language' => true],
    $analyzer->analyze_bytes(accesspdf_test_build_pdf($tagged, '/Root 1 0 R /Info 7 0 R'))
);

check_fields(
    'image-only PDF has no text layer',
    ['status' => 'no_text', 'has_text' => false, 'has_images' => true, 'pages' => 1],
    $analyzer->analyze_bytes(accesspdf_test_build_pdf(accesspdf_test_scanned_objects()))
);

$form = accesspdf_test_text_objects(['/AcroForm << /Fields [6 0 R] >>']);
$form[6] = '<< /FT /Tx /T (name) /Subtype /Widget /Rect [0 0 100 20] >>';
check_fields('fillable form fields are detected', ['has_form' => true], $analyzer->analyze_bytes(accesspdf_test_build_pdf($form)));

// Titles: only the document info dictionary counts, not bookmarks
$bookmarks = accesspdf_test_text_objects(['/Outlines 6 0 R']);
$bookmarks[6] = '<< /Type /Outlines /First 7 0 R /Last 7 0 R /Count 1 >>';
$bookmarks[7] = '<< /Title (Chapter 1) /Parent 6 0 R >>';
$bookmarks[8] = '<< /Title () >>';
check_fields(
    'bookmark titles are not the document title',
    ['has_title' => false, 'title' => ''],
    $analyzer->analyze_bytes(accesspdf_test_build_pdf($bookmarks, '/Root 1 0 R /Info 8 0 R'))
);

$utf16 = accesspdf_test_text_objects();
$utf16[6] = '<< /Title <FEFF0041006E006E00750061006C> >>';
check('UTF-16 hex title is decoded', 'Annual', $analyzer->analyze_bytes(accesspdf_test_build_pdf($utf16, '/Root 1 0 R /Info 6 0 R'))['title']);

$escaped = accesspdf_test_text_objects();
$escaped[6] = '<< /Title (Caf\\351 \\(draft\\)) >>';
check('escaped literal title is decoded', 'Café (draft)', $analyzer->analyze_bytes(accesspdf_test_build_pdf($escaped, '/Root 1 0 R /Info 6 0 R'))['title']);

$xmp = accesspdf_test_text_objects(['/Metadata 6 0 R']);
$xmp[6] = accesspdf_test_stream('<x:xmpmeta><rdf:RDF><rdf:Description><dc:title><rdf:Alt><rdf:li xml:lang="x-default">Course Catalog</rdf:li></rdf:Alt></dc:title><pdfuaid:part>1</pdfuaid:part></rdf:Description></rdf:RDF></x:xmpmeta>', '/Type /Metadata /Subtype /XML');
check_fields(
    'XMP title and PDF/UA claim',
    ['has_title' => true, 'title' => 'Course Catalog', 'pdf_ua' => true],
    $analyzer->analyze_bytes(accesspdf_test_build_pdf($xmp))
);

// Compressed object streams hold the catalog in most modern PDFs
$objstm_objects = [
    1 => '<< /Type /Catalog /Pages 2 0 R /StructTreeRoot 5 0 R /Lang (fr-CA) >>',
    2 => '<< /Type /Pages /Kids [3 0 R] /Count 7 >>',
    4 => '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
];
$header = '';
$body = '';
foreach ($objstm_objects as $number => $text) {
    $header .= $number . ' ' . strlen($body) . ' ';
    $body .= $text . "\n";
}
$compressed = gzcompress($header . $body);
$objstm_pdf = accesspdf_test_build_pdf([
    3 => '<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> >>',
    5 => '<< /Type /StructTreeRoot /K [] >>',
    6 => "<< /Type /ObjStm /N 3 /First " . strlen($header) . " /Filter /FlateDecode /Length " . strlen($compressed) . " >>\nstream\n$compressed\nendstream",
]);
check_fields(
    'catalog inside a compressed object stream',
    ['status' => 'tagged', 'tagged' => true, 'pages' => 7, 'language' => 'fr-CA', 'has_text' => true],
    $analyzer->analyze_bytes($objstm_pdf)
);

$encrypted_pdf = accesspdf_test_encrypted_pdf();
check_fields(
    'encrypted object streams can’t be checked',
    ['status' => 'encrypted', 'encrypted' => true, 'pages' => null, 'tagged' => null],
    $analyzer->analyze_bytes($encrypted_pdf)
);

// Incremental updates: the newest copy of an object wins
$original = accesspdf_test_build_pdf(accesspdf_test_text_objects());
$update = "1 0 obj\n<< /Type /Catalog /Pages 2 0 R /StructTreeRoot 6 0 R >>\nendobj\n6 0 obj\n<< /Type /StructTreeRoot >>\nendobj\n"
    . "trailer\n<< /Size 7 /Root 1 0 R /Prev 0 >>\nstartxref\n0\n%%EOF\n";
check('incremental update adding tags counts as tagged', 'tagged', $analyzer->analyze_bytes($original . $update)['status']);

// Files that can't be checked
check_fields('non-PDF bytes', ['status' => 'unreadable', 'error' => 'Not a PDF file'], $analyzer->analyze_bytes('<html>not a pdf</html>'));
check_fields('damaged PDF', ['status' => 'unreadable', 'error' => 'The file is damaged'], $analyzer->analyze_bytes("%PDF-1.4\n" . str_repeat('garbage ', 20)));
check_fields('missing file', ['status' => 'unreadable', 'error' => 'File not found on this server'], $analyzer->analyze_file(__DIR__ . '/does-not-exist.pdf'));
$tmp = tempnam(sys_get_temp_dir(), 'pdf');
file_put_contents($tmp, accesspdf_test_build_pdf(accesspdf_test_text_objects()));
check_fields('files over the size limit are not read', ['status' => 'too_large'], (new AccessPDF_PDF_Analyzer(100))->analyze_file($tmp));
check_fields('files under the size limit are read', ['status' => 'untagged'], $analyzer->analyze_file($tmp));
unlink($tmp);

// Link extraction from post content
check(
    'PDF links from href, src and data attributes',
    ['/files/a.pdf', 'https://example.edu/b.PDF?v=2&x=1#page=3', 'c.pdf'],
    AccessPDF_Inventory::extract_pdf_urls(
        '<a href="/files/a.pdf">A</a> <a href=\'https://example.edu/b.PDF?v=2&amp;x=1#page=3\'>B</a>'
        . '<object data="c.pdf"></object><a href="/about/">not a pdf</a><a href="/files/a.pdf">dupe</a>'
        . '<a href="/report.pdf.html">not a pdf either</a>'
    )
);
check('no links in plain text', [], AccessPDF_Inventory::extract_pdf_urls('Download report.pdf from the office.'));

// Status groups
check('untagged needs work', true, AccessPDF_Inventory::needs_work('untagged'));
check('no text layer needs work', true, AccessPDF_Inventory::needs_work('no_text'));
check('tagged does not need work', false, AccessPDF_Inventory::needs_work('tagged'));
check('encrypted is unchecked', true, AccessPDF_Inventory::unchecked('encrypted'));
check('missing file is unchecked', true, AccessPDF_Inventory::unchecked('missing'));

// CSV cells that spreadsheets would run as formulas
check('formula cell is neutralized', "'=HYPERLINK(\"x\")", AccessPDF_Inventory::csv_cell('=HYPERLINK("x")'));
check('at-sign cell is neutralized', "'@SUM(A1)", AccessPDF_Inventory::csv_cell('@SUM(A1)'));
check('ordinary cell is unchanged', 'Annual Report.pdf', AccessPDF_Inventory::csv_cell('Annual Report.pdf'));
check(
    'CSV line quotes cells with commas, quotes and newlines',
    "plain,\"a, b\",\"say \"\"hi\"\"\",\"two\nlines\",'=1+1,14\r\n",
    AccessPDF_Inventory::csv_line(['plain', 'a, b', 'say "hi"', "two\nlines", '=1+1', 14])
);

echo "\n" . ($total - $failures) . " of $total passed\n";
exit($failures ? 1 : 0);
