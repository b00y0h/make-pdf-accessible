<?php
/**
 * Converts rendered post HTML into Markdown for AI agents.
 *
 * Plain PHP; its only WordPress call is wp_parse_url(), so it can be tested on its own.
 * Follows the same semantics as a screen reader: aria-hidden content and
 * decorative images (alt="") are skipped, screen-reader-only text is kept.
 */

if (!defined('ABSPATH')) {
    exit;
}

class AccessPDF_HTML_To_Markdown {
    /** Elements whose content never appears in the Markdown. */
    const SKIP_TAGS = [
        'button', 'canvas', 'embed', 'head', 'input', 'link', 'meta', 'noscript',
        'object', 'script', 'select', 'style', 'svg', 'template', 'textarea',
    ];

    /** Containers that start a new block but add no Markdown syntax. */
    const BLOCK_TAGS = [
        'address', 'article', 'aside', 'center', 'details', 'dialog', 'div', 'dl',
        'fieldset', 'footer', 'form', 'header', 'hgroup', 'main', 'nav', 'section', 'summary',
    ];

    /** Elements flattened to plain text inside headings, links and table cells. */
    const FLATTEN_TAGS = [
        'blockquote', 'dd', 'dt', 'figcaption', 'figure', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'hr', 'li', 'ol', 'p', 'pre', 'table', 'ul',
    ];

    /** Marks a fenced code block until the final pass puts it back. */
    const PLACEHOLDER = "\x1A";

    /** @var string */
    private $base_url;

    /** @var string[] */
    private $code_blocks = [];

    /**
     * @param string $base_url Absolute URL of the page, used to resolve relative links.
     */
    public function __construct($base_url = '') {
        $this->base_url = (string) $base_url;
    }

    /**
     * @param string $html HTML fragment, such as the output of the_content.
     * @return string Markdown ending in a newline, or an empty string.
     */
    public function convert($html) {
        $html = trim((string) $html);
        if ('' === $html) {
            return '';
        }

        $this->code_blocks = [];

        $doc = new DOMDocument();
        $previous = libxml_use_internal_errors(true);
        $doc->loadHTML(
            '<?xml encoding="utf-8"?><div>' . $html . '</div>',
            LIBXML_HTML_NOIMPLIED | LIBXML_HTML_NODEFDTD | LIBXML_NONET
        );
        libxml_clear_errors();
        libxml_use_internal_errors($previous);

        $markdown = '';
        foreach ($doc->childNodes as $child) {
            $markdown .= $this->render_node($child, []);
        }

        return $this->finalize($markdown);
    }

    private function render_children(DOMNode $node, array $ctx) {
        $out = '';
        foreach ($node->childNodes as $child) {
            $out .= $this->render_node($child, $ctx);
        }
        return $out;
    }

    private function render_node(DOMNode $node, array $ctx) {
        if ($node instanceof DOMText) {
            return $this->render_text($node->nodeValue, $ctx);
        }
        if (!$node instanceof DOMElement) {
            return '';
        }

        $tag = strtolower($node->nodeName);
        if (in_array($tag, self::SKIP_TAGS, true)
            || $node->hasAttribute('hidden')
            || 'true' === strtolower($node->getAttribute('aria-hidden'))) {
            return '';
        }

        if (!empty($ctx['flat']) && (in_array($tag, self::FLATTEN_TAGS, true) || in_array($tag, self::BLOCK_TAGS, true))) {
            return ' ' . $this->render_children($node, $ctx) . ' ';
        }

        switch ($tag) {
            case 'h1':
            case 'h2':
            case 'h3':
            case 'h4':
            case 'h5':
            case 'h6':
                $text = $this->flat_text($node, $ctx);
                return '' === $text ? '' : $this->block(str_repeat('#', (int) $tag[1]) . ' ' . $text);
            case 'p':
            case 'dd':
            case 'figcaption':
                return $this->block($this->escape_block_start(trim($this->render_children($node, $ctx))));
            case 'dt':
                return $this->block($this->wrap_inline($this->flat_text($node, $ctx), '**'));
            case 'br':
                return !empty($ctx['flat']) ? ' ' : "\\\n";
            case 'hr':
                return $this->block('---');
            case 'strong':
            case 'b':
                return $this->wrap_inline($this->render_children($node, $ctx), '**');
            case 'em':
            case 'i':
                return $this->wrap_inline($this->render_children($node, $ctx), '*');
            case 'del':
            case 's':
            case 'strike':
                return $this->wrap_inline($this->render_children($node, $ctx), '~~');
            case 'code':
                return $this->inline_code($node->textContent);
            case 'pre':
                return $this->code_block($node);
            case 'a':
                return $this->link($node, $ctx);
            case 'img':
                return $this->image($node);
            case 'iframe':
                return $this->iframe($node);
            case 'ul':
            case 'ol':
                return $this->render_list($node, $ctx);
            case 'blockquote':
                return $this->blockquote($node, $ctx);
            case 'table':
                return $this->table($node, $ctx);
            case 'figure':
                return $this->block(trim($this->render_children($node, $ctx)));
        }

        $content = $this->render_children($node, $ctx);
        return in_array($tag, self::BLOCK_TAGS, true) ? "\n\n" . $content . "\n\n" : $content;
    }

    private function render_text($text, array $ctx) {
        $text = str_replace(self::PLACEHOLDER, '', $text);
        $text = preg_replace('/[ \t\r\n\f]+/', ' ', $text);
        return $this->escape($text);
    }

    /** Escapes characters that would otherwise become Markdown syntax. */
    private function escape($text) {
        $text = str_replace('\\', '\\\\', $text);
        $text = preg_replace('/([*`\[\]])/', '\\\\$1', $text);
        // Underscores inside words (snake_case) are not emphasis, so leave them readable.
        $text = preg_replace('/(?<![\p{L}\p{N}])_|_(?![\p{L}\p{N}])/u', '\\_', $text);
        return preg_replace('/<(?=[A-Za-z\/!?])/', '\\<', $text);
    }

    /** Stops paragraph text such as "1. Apply" or "# 1" from turning into a list or heading. */
    private function escape_block_start($text) {
        if (preg_match('/^(\d+)([.)])(\s)/', $text, $m)) {
            return $m[1] . '\\' . $m[2] . substr($text, strlen($m[1]) + 1);
        }
        if (preg_match('/^(#{1,6}\s|>|[-+]\s)/', $text)) {
            return '\\' . $text;
        }
        return $text;
    }

    private function block($text) {
        return '' === $text ? '' : "\n\n" . $text . "\n\n";
    }

    /** Renders an element as a single line of text. */
    private function flat_text(DOMNode $node, array $ctx) {
        $ctx['flat'] = true;
        return trim(preg_replace('/\s+/', ' ', $this->render_children($node, $ctx)));
    }

    private function wrap_inline($content, $marker) {
        if ('' === trim($content)) {
            return $content;
        }
        preg_match('/^(\s*)(.*?)(\s*)$/su', $content, $m);
        return $m[1] . $marker . $m[2] . $marker . $m[3];
    }

    private function inline_code($text) {
        $text = preg_replace('/\s+/', ' ', $text);
        if ('' === trim($text)) {
            return '';
        }
        $fence = str_repeat('`', $this->longest_backtick_run($text) + 1);
        $pad = ('`' === $text[0] || '`' === substr($text, -1)) ? ' ' : '';
        return $fence . $pad . $text . $pad . $fence;
    }

    private function code_block(DOMElement $pre) {
        $code = rtrim(str_replace("\r\n", "\n", $pre->textContent), "\n");
        if ('' === trim($code)) {
            return '';
        }

        $language = '';
        $classes = $pre->getAttribute('class');
        foreach ($pre->getElementsByTagName('code') as $code_element) {
            $classes .= ' ' . $code_element->getAttribute('class');
            break;
        }
        if (preg_match('/(?:language|lang)-([\w+#.-]+)/', $classes, $m)) {
            $language = $m[1];
        }

        $fence = str_repeat('`', max(3, $this->longest_backtick_run($code) + 1));
        $this->code_blocks[] = $fence . $language . "\n" . $code . "\n" . $fence;
        $id = count($this->code_blocks) - 1;
        return "\n\n" . self::PLACEHOLDER . $id . self::PLACEHOLDER . "\n\n";
    }

    private function longest_backtick_run($text) {
        $longest = 0;
        if (preg_match_all('/`+/', $text, $matches)) {
            foreach ($matches[0] as $run) {
                $longest = max($longest, strlen($run));
            }
        }
        return $longest;
    }

    private function link(DOMElement $node, array $ctx) {
        $ctx['flat'] = true;
        $text = trim(preg_replace('/\s+/', ' ', $this->render_children($node, $ctx)));
        if ('' === $text) {
            $text = $this->escape(trim($node->getAttribute('aria-label')));
        }

        $href = trim($node->getAttribute('href'));
        if ('' === $href || preg_match('/^javascript:/i', $href)) {
            return $text;
        }
        if ('' === $text) {
            return '';
        }
        return '[' . $text . '](' . $this->format_url($this->absolute_url($href)) . ')';
    }

    private function image(DOMElement $node) {
        // alt="" marks a decorative image, which screen readers skip too.
        if ($node->hasAttribute('alt') && '' === trim($node->getAttribute('alt'))) {
            return '';
        }
        $alt = $this->escape(trim(preg_replace('/\s+/', ' ', $node->getAttribute('alt'))));
        $src = trim($node->getAttribute('src'));
        if ('' === $src || 0 === stripos($src, 'data:')) {
            return $alt;
        }
        return '![' . $alt . '](' . $this->format_url($this->absolute_url($src)) . ')';
    }

    private function iframe(DOMElement $node) {
        $src = trim($node->getAttribute('src'));
        if ('' === $src) {
            return '';
        }
        $title = trim($node->getAttribute('title'));
        $text = '' === $title ? 'Embedded content' : $this->escape($title);
        return $this->block('[' . $text . '](' . $this->format_url($this->absolute_url($src)) . ')');
    }

    private function render_list(DOMElement $node, array $ctx) {
        $ordered = 'ol' === strtolower($node->nodeName);
        $number = ($ordered && $node->hasAttribute('start')) ? (int) $node->getAttribute('start') : 1;

        $items = [];
        foreach ($node->childNodes as $child) {
            if (!$child instanceof DOMElement || 'li' !== strtolower($child->nodeName)) {
                continue;
            }
            $marker = $ordered ? $number . '.' : '-';
            $number++;

            $content = $this->normalize_fragment($this->render_children($child, $ctx), true);
            $indent = str_repeat(' ', strlen($marker) + 1);
            $lines = explode("\n", $content);
            $item = $marker . ' ' . array_shift($lines);
            foreach ($lines as $line) {
                $item .= "\n" . ('' === $line ? '' : $indent . $line);
            }
            $items[] = $item;
        }

        return empty($items) ? '' : $this->block(implode("\n", $items));
    }

    private function blockquote(DOMElement $node, array $ctx) {
        $content = $this->normalize_fragment($this->render_children($node, $ctx), false);
        if ('' === $content) {
            return '';
        }
        $lines = array_map(
            function ($line) {
                return '' === $line ? '>' : '> ' . $line;
            },
            explode("\n", $content)
        );
        return $this->block(implode("\n", $lines));
    }

    private function table(DOMElement $table, array $ctx) {
        $rows = [];
        $caption = '';
        $header_rows = [];
        $body_rows = [];

        foreach ($table->childNodes as $child) {
            if (!$child instanceof DOMElement) {
                continue;
            }
            $name = strtolower($child->nodeName);
            if ('caption' === $name) {
                $caption = $this->flat_text($child, $ctx);
            } elseif ('tr' === $name) {
                $body_rows[] = $child;
            } elseif (in_array($name, ['thead', 'tbody', 'tfoot'], true)) {
                foreach ($child->childNodes as $row) {
                    if ($row instanceof DOMElement && 'tr' === strtolower($row->nodeName)) {
                        if ('thead' === $name) {
                            $header_rows[] = $row;
                        } else {
                            $body_rows[] = $row;
                        }
                    }
                }
            }
        }

        foreach (array_merge($header_rows, $body_rows) as $tr) {
            $cells = [];
            foreach ($tr->childNodes as $cell) {
                if (!$cell instanceof DOMElement || !in_array(strtolower($cell->nodeName), ['td', 'th'], true)) {
                    continue;
                }
                $cells[] = str_replace('|', '\\|', $this->flat_text($cell, $ctx));
                // Keep later cells in their columns when a cell spans several.
                $span = max(1, (int) $cell->getAttribute('colspan'));
                for ($i = 1; $i < $span; $i++) {
                    $cells[] = '';
                }
            }
            if (!empty($cells)) {
                $rows[] = $cells;
            }
        }

        if (empty($rows)) {
            return '' === $caption ? '' : $this->block($caption);
        }

        $columns = max(array_map('count', $rows));
        $lines = [];
        foreach ($rows as $index => $cells) {
            $cells = array_pad($cells, $columns, '');
            $lines[] = '| ' . implode(' | ', $cells) . ' |';
            if (0 === $index) {
                // Markdown tables need a header row; the first row serves as one.
                $lines[] = '|' . str_repeat(' --- |', $columns);
            }
        }

        $markdown = implode("\n", $lines);
        if ('' !== $caption) {
            $markdown = $caption . "\n\n" . $markdown;
        }
        return $this->block($markdown);
    }

    /** Resolves a link or image URL against the page URL. */
    private function absolute_url($url) {
        if ('' === $this->base_url || preg_match('/^[a-z][a-z0-9+.-]*:/i', $url)) {
            return $url;
        }
        $base = wp_parse_url($this->base_url);
        if (empty($base['scheme']) || empty($base['host'])) {
            return $url;
        }
        $origin = $base['scheme'] . '://' . $base['host'] . (isset($base['port']) ? ':' . $base['port'] : '');
        $path = isset($base['path']) ? $base['path'] : '/';

        if (0 === strpos($url, '//')) {
            return $base['scheme'] . ':' . $url;
        }
        if ('#' === $url[0]) {
            return strtok($this->base_url, '#') . $url;
        }
        if ('?' === $url[0]) {
            return $origin . $path . $url;
        }
        if ('/' === $url[0]) {
            return $origin . $url;
        }
        return $origin . preg_replace('#/[^/]*$#', '/', $path) . $url;
    }

    private function format_url($url) {
        if (preg_match('/[\s()<>]/', $url)) {
            return '<' . str_replace(['<', '>'], ['%3C', '%3E'], $url) . '>';
        }
        return $url;
    }

    /** Cleans up a nested fragment (list item or quote) before it is indented. */
    private function normalize_fragment($markdown, $tight) {
        $text = $this->normalize_lines($markdown);
        $text = preg_replace($tight ? "/\n{2,}/" : "/\n{3,}/", $tight ? "\n" : "\n\n", $text);
        return trim($text, "\n ");
    }

    private function normalize_lines($markdown) {
        $lines = explode("\n", str_replace("\r", '', $markdown));
        foreach ($lines as $i => $line) {
            $lines[$i] = preg_replace('/(?<=\S) {2,}/', ' ', rtrim($line));
        }
        return implode("\n", $lines);
    }

    private function finalize($markdown) {
        $text = $this->normalize_lines($markdown);
        $text = trim(preg_replace("/\n{3,}/", "\n\n", $text));

        // Put code blocks back, indented to match any list or quote they sit in.
        $blocks = $this->code_blocks;
        $text = preg_replace_callback(
            '/^([ >]*)' . self::PLACEHOLDER . '(\d+)' . self::PLACEHOLDER . '$/m',
            function ($m) use ($blocks) {
                $prefix = $m[1];
                $lines = explode("\n", $blocks[(int) $m[2]]);
                foreach ($lines as $i => $line) {
                    $lines[$i] = '' === $line ? rtrim($prefix) : $prefix . $line;
                }
                return implode("\n", $lines);
            },
            $text
        );

        return '' === $text ? '' : $text . "\n";
    }
}
