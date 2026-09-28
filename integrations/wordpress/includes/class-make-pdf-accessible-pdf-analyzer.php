<?php
/**
 * Checks a PDF for the basics assistive technology needs, without external services.
 *
 * Plain PHP with no WordPress dependencies. It is not a full PDF parser: it
 * finds the document catalog and info dictionary through the trailer (including
 * inside compressed object streams) and reads the markers that matter:
 * accessibility tags, a text layer, title, language and form fields.
 */

if (!defined('ABSPATH')) {
    exit;
}

class Make_PDF_Accessible_PDF_Analyzer {
    const STATUS_TAGGED = 'tagged';
    const STATUS_UNTAGGED = 'untagged';
    const STATUS_NO_TEXT = 'no_text';
    const STATUS_ENCRYPTED = 'encrypted';
    const STATUS_TOO_LARGE = 'too_large';
    const STATUS_UNREADABLE = 'unreadable';

    /** Upper bound on decompressed object-stream data, to guard against zip bombs. */
    const MAX_EXPANDED_BYTES = 33554432;

    /** @var int */
    private $max_bytes;

    /** @var array<int, array{text: string, position: int}> Objects found inside object streams. */
    private $stream_objects = [];

    /**
     * @param int $max_bytes Files larger than this are reported as too large instead of read.
     */
    public function __construct($max_bytes = 52428800) {
        $this->max_bytes = (int) $max_bytes;
    }

    /**
     * @param string $path Absolute path to a PDF file.
     * @return array See analyze_bytes().
     */
    public function analyze_file($path) {
        if (!is_string($path) || '' === $path || !is_file($path) || !is_readable($path)) {
            return $this->result(self::STATUS_UNREADABLE, ['error' => 'File not found on this server']);
        }
        $size = (int) filesize($path);
        if ($size > $this->max_bytes) {
            return $this->result(self::STATUS_TOO_LARGE, ['size' => $size]);
        }
        $data = file_get_contents($path);
        if (false === $data) {
            return $this->result(self::STATUS_UNREADABLE, ['size' => $size, 'error' => 'File could not be read']);
        }
        return $this->analyze_bytes($data);
    }

    /**
     * @param string $data Raw PDF bytes.
     * @return array{
     *     status: string, pages: int|null, tagged: bool|null, has_text: bool|null,
     *     has_images: bool|null, has_title: bool|null, title: string, has_language: bool|null,
     *     language: string, has_form: bool|null, pdf_ua: bool, encrypted: bool,
     *     version: string, size: int, error: string
     * }
     */
    public function analyze_bytes($data) {
        $data = (string) $data;
        $size = strlen($data);
        $header = strpos(substr($data, 0, 1024), '%PDF-');
        if (false === $header) {
            return $this->result(self::STATUS_UNREADABLE, ['size' => $size, 'error' => 'Not a PDF file']);
        }
        preg_match('/%PDF-(\d\.\d)/', substr($data, $header, 16), $version);

        $encrypted = (bool) preg_match('/\/Encrypt\s*(?:\d+\s+\d+\s+R|<<)/', $data);
        list($expanded, $undecodable) = $this->expand_object_streams($data, $encrypted);
        $all = $data . "\n" . $expanded;

        $root = $this->last_reference($data, 'Root');
        $catalog = $root ? $this->find_object($data, $root) : null;
        if (null === $catalog && 0 === $root && !preg_match('/\/Type\s*\/Catalog\b/', $all)) {
            return $this->result(self::STATUS_UNREADABLE, ['size' => $size, 'error' => 'The file is damaged']);
        }

        $base = [
            'size' => $size,
            'version' => isset($version[1]) ? $version[1] : '',
            'encrypted' => $encrypted,
        ];

        // Encrypted object streams hide their contents. Without the catalog nothing can be
        // checked; with it, anything not found may simply be hidden, so it counts as unknown.
        $hidden = $encrypted && $undecodable > 0;
        if (null === $catalog && $hidden) {
            return $this->result(self::STATUS_ENCRYPTED, $base);
        }

        $catalog_text = null === $catalog ? $all : $catalog;
        $tagged = (bool) preg_match('/\/StructTreeRoot\s*(?:\d+\s+\d+\s+R|<<)/', $catalog_text);
        $has_text = (bool) preg_match('/\/Font\s*(?:<<|\d+\s+\d+\s+R)|\/Type\s*\/Font\b/', $all);
        $has_images = (bool) preg_match('/\/Subtype\s*\/Image\b/', $all);

        $language_raw = $this->string_value($catalog_text, 'Lang');
        $info_ref = $this->last_reference($data, 'Info');
        $info = $info_ref ? $this->find_object($data, $info_ref) : null;
        $title_raw = null === $info ? null : $this->string_value($info, 'Title');
        $xmp_title = preg_match('/<dc:title>.*?<rdf:li[^>]*>\s*([^<\s][^<]*)<\/rdf:li>/s', $all, $xmp) ? trim($xmp[1]) : '';

        $title = '';
        if (null !== $title_raw && !$encrypted) {
            $title = trim($this->decode_string($title_raw));
        } elseif ('' !== $xmp_title) {
            $title = html_entity_decode($xmp_title, ENT_QUOTES | ENT_XML1, 'UTF-8');
        }
        $has_title = '' !== $title || (null !== $title_raw && $encrypted && !$this->is_empty_string($title_raw));

        $language = null !== $language_raw && !$encrypted ? trim($this->decode_string($language_raw)) : '';
        $has_language = '' !== $language || (null !== $language_raw && $encrypted && !$this->is_empty_string($language_raw));

        $has_form = (bool) preg_match('/\/FT\s*\/(?:Tx|Btn|Ch|Sig)\b/', $all);

        if ($tagged) {
            $status = $has_text || $hidden ? self::STATUS_TAGGED : self::STATUS_NO_TEXT;
        } elseif ($has_text) {
            $status = self::STATUS_UNTAGGED;
        } else {
            $status = $hidden ? self::STATUS_ENCRYPTED : self::STATUS_NO_TEXT;
        }

        return $this->result($status, $base + [
            'pages' => $this->count_pages($data, $catalog, $all),
            'tagged' => $tagged,
            'has_text' => $has_text || !$hidden ? $has_text : null,
            'has_images' => $has_images || !$hidden ? $has_images : null,
            'has_title' => $has_title || !$hidden ? $has_title : null,
            'title' => $title,
            'has_language' => $has_language,
            'language' => $language,
            'has_form' => $has_form || !$hidden ? $has_form : null,
            'pdf_ua' => (bool) preg_match('/pdfuaid:part/i', $all),
        ]);
    }

    private function result($status, array $fields) {
        return array_merge([
            'status' => $status,
            'pages' => null,
            'tagged' => null,
            'has_text' => null,
            'has_images' => null,
            'has_title' => null,
            'title' => '',
            'has_language' => null,
            'language' => '',
            'has_form' => null,
            'pdf_ua' => false,
            'encrypted' => false,
            'version' => '',
            'size' => 0,
            'error' => '',
        ], $fields);
    }

    /**
     * Decompresses object streams and XMP metadata so their contents can be searched.
     *
     * @return array{0: string, 1: int} Expanded text and the number of streams that couldn't be read.
     */
    private function expand_object_streams($data, $encrypted) {
        $this->stream_objects = [];
        $expanded = '';
        $undecodable = 0;
        $budget = self::MAX_EXPANDED_BYTES;
        $offset = 0;
        $seen = 0;

        while (false !== ($pos = strpos($data, 'stream', $offset))) {
            $offset = $pos + 6;
            if ($pos >= 3 && 'end' === substr($data, $pos - 3, 3)) {
                continue;
            }
            $start = $pos + 6;
            if ("\r\n" === substr($data, $start, 2)) {
                $start += 2;
            } elseif (isset($data[$start]) && ("\n" === $data[$start] || "\r" === $data[$start])) {
                $start += 1;
            } else {
                continue;
            }

            $dict = $this->dictionary_before($data, $pos);
            if (!preg_match('/\/Type\s*\/(ObjStm|Metadata)\b/', $dict, $type)) {
                continue;
            }
            $end = strpos($data, 'endstream', $start);
            if (false === $end) {
                break;
            }
            $offset = $end + 9;
            if (++$seen > 20000) {
                break;
            }

            $raw = substr($data, $start, $end - $start);
            if (!preg_match('/\/FlateDecode\b/', $dict)) {
                // Uncompressed metadata is already searchable in the raw bytes.
                continue;
            }
            if ($encrypted) {
                $undecodable++;
                continue;
            }
            $text = $this->inflate($raw, $budget);
            if (null === $text) {
                $undecodable++;
                continue;
            }
            $budget -= strlen($text);
            $expanded .= "\n" . $text;
            if ('ObjStm' === $type[1]) {
                $this->index_object_stream($dict, $text, $pos);
            }
            if ($budget <= 0) {
                break;
            }
        }

        return [$expanded, $undecodable];
    }

    /** The dictionary text of the object whose stream starts at $pos. */
    private function dictionary_before($data, $pos) {
        $from = max(0, $pos - 4096);
        $window = substr($data, $from, $pos - $from);
        if (preg_match_all('/\d+\s+\d+\s+obj\b/', $window, $m, PREG_OFFSET_CAPTURE)) {
            $last = end($m[0]);
            return substr($window, $last[1]);
        }
        return $window;
    }

    /** Inflates a Flate stream in chunks, stopping at $limit bytes of output. */
    private function inflate($raw, $limit) {
        $raw = rtrim($raw, "\r\n");
        $context = @inflate_init(ZLIB_ENCODING_DEFLATE);
        if (false === $context) {
            return null;
        }
        $out = '';
        $length = strlen($raw);
        for ($i = 0; $i < $length; $i += 8192) {
            $chunk = @inflate_add($context, substr($raw, $i, 8192), $i + 8192 >= $length ? ZLIB_FINISH : ZLIB_SYNC_FLUSH);
            if (false === $chunk) {
                return '' === $out ? null : $out;
            }
            $out .= $chunk;
            if (strlen($out) > $limit) {
                return substr($out, 0, max(0, $limit));
            }
            if (ZLIB_STREAM_END === inflate_get_status($context)) {
                break;
            }
        }
        return $out;
    }

    /** Records each object inside an object stream so it can be looked up by number. */
    private function index_object_stream($dict, $text, $position) {
        if (!preg_match('/\/N\s+(\d+)/', $dict, $n) || !preg_match('/\/First\s+(\d+)/', $dict, $first)) {
            return;
        }
        $count = (int) $n[1];
        $first = (int) $first[1];
        if (!preg_match_all('/\d+/', substr($text, 0, $first), $numbers) || count($numbers[0]) < $count * 2) {
            return;
        }
        $pairs = array_chunk(array_map('intval', array_slice($numbers[0], 0, $count * 2)), 2);
        foreach ($pairs as $i => $pair) {
            $start = $first + $pair[1];
            $next = isset($pairs[$i + 1]) ? $first + $pairs[$i + 1][1] : strlen($text);
            $this->stream_objects[$pair[0]] = [
                'text' => substr($text, $start, max(0, $next - $start)),
                'position' => $position,
            ];
        }
    }

    /** The object number of the last /Key N G R reference in the file (the newest revision). */
    private function last_reference($data, $key) {
        if (preg_match_all('/\/' . $key . '\s+(\d+)\s+\d+\s+R/', $data, $m)) {
            return (int) end($m[1]);
        }
        return 0;
    }

    /** The text of object $number, preferring whichever copy appears last in the file. */
    private function find_object($data, $number) {
        $raw = null;
        $raw_position = -1;
        if (preg_match_all('/(?<!\d)' . $number . '\s+\d+\s+obj\b/', $data, $m, PREG_OFFSET_CAPTURE)) {
            $last = end($m[0]);
            $raw_position = $last[1];
            $end = strpos($data, 'endobj', $raw_position);
            $raw = substr($data, $raw_position, false === $end ? 65536 : min(1048576, $end - $raw_position));
        }
        if (isset($this->stream_objects[$number]) && $this->stream_objects[$number]['position'] > $raw_position) {
            return $this->stream_objects[$number]['text'];
        }
        return $raw;
    }

    private function count_pages($data, $catalog, $all) {
        if (null !== $catalog && preg_match('/\/Pages\s+(\d+)\s+\d+\s+R/', $catalog, $ref)) {
            $pages = $this->find_object($data, (int) $ref[1]);
            if (null !== $pages && preg_match('/\/Count\s+(\d+)/', $pages, $count)) {
                return (int) $count[1];
            }
        }
        // Fallback: count page objects.
        $found = preg_match_all('/\/Type\s*\/Page(?![A-Za-z])/', $all);
        return $found ? (int) $found : null;
    }

    /** The raw string token after /Key: "(...)", "<...>" or an indirect reference; null if absent. */
    private function string_value($text, $key) {
        if (!preg_match('/\/' . $key . '\s*([(<])/', $text, $m, PREG_OFFSET_CAPTURE)) {
            if (preg_match('/\/' . $key . '\s+\d+\s+\d+\s+R/', $text)) {
                return '(indirect)';
            }
            return null;
        }
        $start = $m[1][1];
        if ('<' === $m[1][0]) {
            $end = strpos($text, '>', $start);
            return false === $end ? null : substr($text, $start, $end - $start + 1);
        }
        // Literal string: balanced parentheses, honoring backslash escapes.
        $depth = 0;
        $length = strlen($text);
        for ($i = $start; $i < $length && $i < $start + 65536; $i++) {
            $char = $text[$i];
            if ('\\' === $char) {
                $i++;
            } elseif ('(' === $char) {
                $depth++;
            } elseif (')' === $char && 0 === --$depth) {
                return substr($text, $start, $i - $start + 1);
            }
        }
        return null;
    }

    private function is_empty_string($token) {
        return '()' === preg_replace('/\s+/', '', $token) || '<>' === preg_replace('/\s+/', '', $token);
    }

    /** Decodes a PDF string token (literal or hex, PDFDocEncoding or UTF-16BE) to UTF-8. */
    private function decode_string($token) {
        if ('(indirect)' === $token) {
            return '';
        }
        if ('<' === $token[0]) {
            $hex = preg_replace('/[^0-9A-Fa-f]/', '', $token);
            if (strlen($hex) % 2) {
                $hex .= '0';
            }
            $bytes = (string) hex2bin($hex);
        } else {
            $bytes = $this->unescape_literal(substr($token, 1, -1));
        }

        if ("\xFE\xFF" === substr($bytes, 0, 2)) {
            return $this->utf16be_to_utf8(substr($bytes, 2));
        }
        if ("\xEF\xBB\xBF" === substr($bytes, 0, 3)) {
            return substr($bytes, 3);
        }
        // PDFDocEncoding matches Latin-1 for the printable range.
        return function_exists('mb_convert_encoding') ? mb_convert_encoding($bytes, 'UTF-8', 'ISO-8859-1') : $bytes;
    }

    private function unescape_literal($text) {
        $map = ['n' => "\n", 'r' => "\r", 't' => "\t", 'b' => "\x08", 'f' => "\x0C", '(' => '(', ')' => ')', '\\' => '\\'];
        return preg_replace_callback(
            '/\\\\([0-7]{1,3}|.|\n)/s',
            function ($m) use ($map) {
                if (ctype_digit($m[1])) {
                    return chr(octdec($m[1]) & 0xFF);
                }
                return isset($map[$m[1]]) ? $map[$m[1]] : ("\n" === $m[1] ? '' : $m[1]);
            },
            $text
        );
    }

    private function utf16be_to_utf8($bytes) {
        if (function_exists('mb_convert_encoding')) {
            return mb_convert_encoding($bytes, 'UTF-8', 'UTF-16BE');
        }
        $out = '';
        $length = strlen($bytes) - 1;
        for ($i = 0; $i < $length; $i += 2) {
            $code = (ord($bytes[$i]) << 8) | ord($bytes[$i + 1]);
            $out .= $code < 0x80 ? chr($code) : '?';
        }
        return $out;
    }
}
