<?php
/**
 * Tests for the HTML-to-Markdown converter and Accept header negotiation.
 *
 * Run: php integrations/wordpress/tests/markdown-test.php
 * Needs only PHP with the DOM extension; WordPress is not loaded.
 */

define('ABSPATH', __DIR__ . '/');

require __DIR__ . '/../includes/class-accesspdf-html-to-markdown.php';
require __DIR__ . '/../includes/class-accesspdf-markdown.php';

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

function md($html, $base = 'https://example.edu/admissions/apply/') {
    return (new AccessPDF_HTML_To_Markdown($base))->convert($html);
}

// Structure
check(
    'headings, paragraphs and emphasis',
    "## Deadlines\n\nApply by **March 1** or *earlier*.\n",
    md('<h2>Deadlines</h2><p>Apply by <strong>March 1</strong> or <em>earlier</em>.</p>')
);
check(
    'WordPress block comments are ignored',
    "Hello\n",
    md("<!-- wp:paragraph -->\n<p>Hello</p>\n<!-- /wp:paragraph -->")
);
check(
    'nested and ordered lists',
    "- Forms\n  1. FAFSA\n  2. CSS Profile\n- Deadlines\n",
    md('<ul><li>Forms<ol><li>FAFSA</li><li>CSS Profile</li></ol></li><li>Deadlines</li></ul>')
);
check(
    'ordered list start attribute',
    "3. Third\n4. Fourth\n",
    md('<ol start="3"><li>Third</li><li>Fourth</li></ol>')
);
check(
    'table with header row, caption and escaped pipe',
    "Tuition 2026-27\n\n| Program | Cost |\n| --- | --- |\n| Nursing \\| BSN | \$12,000 |\n",
    md('<table><caption>Tuition 2026-27</caption><thead><tr><th>Program</th><th>Cost</th></tr></thead>'
        . '<tbody><tr><td>Nursing | BSN</td><td>$12,000</td></tr></tbody></table>')
);
check(
    'colspan keeps later cells in their columns',
    "| A | B | C |\n| --- | --- | --- |\n| wide | | c |\n",
    md('<table><tr><th>A</th><th>B</th><th>C</th></tr><tr><td colspan="2">wide</td><td>c</td></tr></table>')
);
check(
    'block content inside a table cell is flattened',
    "| Steps |\n| --- |\n| One Two |\n",
    md('<table><tr><th>Steps</th></tr><tr><td><p>One</p><p>Two</p></td></tr></table>')
);
check(
    'blockquote with citation',
    "> Knowledge is power.\n>\n> Francis Bacon\n",
    md('<blockquote><p>Knowledge is power.</p><cite>Francis Bacon</cite></blockquote>')
);
check(
    'horizontal rule and line break',
    "Line one\\\nLine two\n\n---\n",
    md('<p>Line one<br>Line two</p><hr>')
);

// Links and images
check(
    'relative links become absolute',
    "[Visit](https://example.edu/visit/), [form](https://example.edu/admissions/apply/form.pdf), [top](https://example.edu/admissions/apply/#top)\n",
    md('<p><a href="/visit/">Visit</a>, <a href="form.pdf">form</a>, <a href="#top">top</a></p>')
);
check(
    'javascript links keep only their text',
    "Open menu\n",
    md('<p><a href="javascript:void(0)">Open menu</a></p>')
);
check(
    'icon-only link falls back to aria-label',
    "[Search](https://example.edu/search/)\n",
    md('<p><a href="/search/" aria-label="Search"><span aria-hidden="true">icon</span></a></p>')
);
check(
    'URLs with spaces are wrapped in angle brackets',
    "[Guide](<https://example.edu/files/My Guide.pdf>)\n",
    md('<p><a href="https://example.edu/files/My Guide.pdf">Guide</a></p>')
);
check(
    'images keep alt text; decorative images are skipped',
    "![Campus map](https://example.edu/map.png)\n",
    md('<p><img src="/map.png" alt="Campus map"><img src="/divider.png" alt=""></p>')
);
check(
    'figure with caption',
    "![Students on the quad](https://example.edu/quad.jpg)\n\nFall orientation\n",
    md('<figure><img src="/quad.jpg" alt="Students on the quad"><figcaption>Fall orientation</figcaption></figure>')
);
check(
    'headings inside links stay on one line',
    "[Nursing BSN](https://example.edu/nursing/)\n",
    md('<a href="/nursing/"><h3>Nursing</h3><p>BSN</p></a>')
);
check(
    'embedded iframe becomes a link',
    "[Campus tour video](https://www.youtube.com/embed/abc)\n",
    md('<iframe src="https://www.youtube.com/embed/abc" title="Campus tour video"></iframe>')
);

// Code
check(
    'fenced code block keeps language and whitespace',
    "```python\ndef f():\n    return 1\n```\n",
    md('<pre><code class="language-python">def f():' . "\n" . '    return 1' . "\n" . '</code></pre>')
);
check(
    'inline code containing a backtick',
    "Use ``a`b`` here\n",
    md('<p>Use <code>a`b</code> here</p>')
);
check(
    'code block inside a list item is indented',
    "- Run:\n  ```\n  make dev\n  ```\n",
    md('<ul><li>Run:<pre>make dev</pre></li></ul>')
);

// Accessibility semantics and noise removal
check(
    'scripts, styles, hidden and aria-hidden content are dropped',
    "Visible\n",
    md('<script>alert(1)</script><style>p{}</style><p>Visible</p><p hidden>Hidden</p><div aria-hidden="true">Decor</div>')
);
check(
    'screen-reader-only text is kept',
    "Read more about Nursing\n",
    md('<p>Read more<span class="screen-reader-text"> about Nursing</span></p>')
);

// Escaping
check(
    'Markdown characters in text are escaped',
    "2 \\* 3 \\[draft\\] \\_start snake_case \\<div>\n",
    md('<p>2 * 3 [draft] _start snake_case &lt;div&gt;</p>')
);
check(
    'paragraphs that look like lists or headings are escaped',
    "1\\. Apply online\n\n\\# 1 in the state\n",
    md('<p>1. Apply online</p><p># 1 in the state</p>')
);
check(
    'UTF-8 text and entities survive',
    "Café “quotes” 日本語… ok\n",
    md('<p>Café &ldquo;quotes&rdquo; 日本語&hellip; ok</p>')
);
check('empty input', '', md('   '));

// Accept header negotiation
$negotiation = [
    ['text/markdown', true],
    ['text/markdown, text/html;q=0.9, */*;q=0.8', true],
    ['text/markdown, */*', true],
    ['text/markdown, text/html', true],
    ['text/html, text/markdown', false],
    ['text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', false],
    ['text/markdown;q=0.5, text/html', false],
    ['text/html;q=0.5, text/markdown;q=0.8', true],
    ['text/markdown;q=0', false],
    ['*/*', false],
    ['', false],
];
foreach ($negotiation as $case) {
    check('Accept: ' . ('' === $case[0] ? '(empty)' : $case[0]), $case[1], AccessPDF_Markdown::prefers_markdown($case[0]));
}

echo "\n" . ($total - $failures) . " of $total passed\n";
exit($failures ? 1 : 0);
