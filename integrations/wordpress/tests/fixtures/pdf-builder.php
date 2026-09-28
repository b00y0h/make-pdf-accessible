<?php
/**
 * Builds small, valid PDFs for tests, so no binary fixtures live in the repository.
 * Used by the unit tests and by the end-to-end seed.
 */

/** Builds a PDF with a valid xref table from object bodies keyed by object number. */
function make_pdf_accessible_test_build_pdf(array $objects, $trailer = '/Root 1 0 R') {
    $out = "%PDF-1.7\n%\xE2\xE3\xCF\xD3\n";
    $offsets = [];
    foreach ($objects as $number => $body) {
        $offsets[$number] = strlen($out);
        $out .= "$number 0 obj\n$body\nendobj\n";
    }
    $xref = strlen($out);
    $max = max(array_keys($objects));
    $out .= "xref\n0 " . ($max + 1) . "\n0000000000 65535 f \n";
    for ($i = 1; $i <= $max; $i++) {
        $out .= isset($offsets[$i]) ? sprintf("%010d 00000 n \n", $offsets[$i]) : "0000000000 65535 f \n";
    }
    return $out . "trailer\n<< /Size " . ($max + 1) . " $trailer >>\nstartxref\n$xref\n%%EOF\n";
}

function make_pdf_accessible_test_stream($content, $dict = '') {
    return "<< $dict /Length " . strlen($content) . " >>\nstream\n$content\nendstream";
}

/**
 * Catalog, page tree and $pages pages of text. Object numbers 1 to 5 plus two per extra page.
 *
 * @param string[] $catalog_extra Extra catalog entries, e.g. '/Lang (en-US)'.
 */
function make_pdf_accessible_test_text_objects(array $catalog_extra = [], $pages = 1) {
    $objects = [
        1 => '<< /Type /Catalog /Pages 2 0 R ' . implode(' ', $catalog_extra) . ' >>',
        4 => '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    ];
    $kids = [];
    for ($i = 0; $i < $pages; $i++) {
        $page = 3 + $i * 100;
        $kids[] = "$page 0 R";
        $objects[$page] = "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents " . ($page + 2) . ' 0 R >>';
        $objects[$page + 2] = make_pdf_accessible_test_stream("BT /F1 12 Tf 72 720 Td (Page $i) Tj ET");
    }
    $objects[2] = '<< /Type /Pages /Kids [' . implode(' ', $kids) . "] /Count $pages >>";
    ksort($objects);
    return $objects;
}

/** Image-only pages with no fonts, like a scan without OCR. */
function make_pdf_accessible_test_scanned_objects($pages = 1) {
    $objects = [
        1 => '<< /Type /Catalog /Pages 2 0 R >>',
        4 => make_pdf_accessible_test_stream(str_repeat("\x80", 64), '/Type /XObject /Subtype /Image /Width 8 /Height 8 /ColorSpace /DeviceGray /BitsPerComponent 8'),
    ];
    $kids = [];
    for ($i = 0; $i < $pages; $i++) {
        $page = 3 + $i * 100;
        $kids[] = "$page 0 R";
        $objects[$page] = "<< /Type /Page /Parent 2 0 R /Resources << /XObject << /Im0 4 0 R >> >> /Contents " . ($page + 2) . ' 0 R >>';
        $objects[$page + 2] = make_pdf_accessible_test_stream('q 8 0 0 8 0 0 cm /Im0 Do Q');
    }
    $objects[2] = '<< /Type /Pages /Kids [' . implode(' ', $kids) . "] /Count $pages >>";
    ksort($objects);
    return $objects;
}

/** A PDF whose catalog sits in an encrypted object stream, so nothing can be checked. */
function make_pdf_accessible_test_encrypted_pdf() {
    return make_pdf_accessible_test_build_pdf([
        6 => "<< /Type /ObjStm /N 3 /First 20 /Filter /FlateDecode /Length 32 >>\nstream\n" . str_repeat("\x9C", 32) . "\nendstream",
        9 => '<< /Filter /Standard /V 5 /R 6 >>',
    ], '/Root 1 0 R /Encrypt 9 0 R');
}
