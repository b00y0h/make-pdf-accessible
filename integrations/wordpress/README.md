# AccessPDF WordPress plugin

Serves a Markdown version of published posts and pages to AI agents, and sends uploaded PDFs to the AccessPDF service for processing.

## Markdown for AI agents

AI agents read Markdown more reliably than full web pages, which carry navigation, scripts and styling. The plugin gives every published post and page a Markdown version. Visitors always see the normal page.

| Request | Response |
| --- | --- |
| `GET /admissions/` from a browser | The normal HTML page, plus `<link rel="alternate" type="text/markdown">`, a matching `Link` header, and `Vary: Accept` |
| `GET /admissions.md` | Markdown (`text/markdown`), with a `Link: rel="canonical"` header pointing at the HTML page |
| `GET /admissions/` with `Accept: text/markdown` | Markdown, marked `Cache-Control: no-store, private` so shared caches don't store it under the HTML address |
| `GET /index.md` | The static front page, when one is set |
| `GET /?page_id=5&accesspdf_md=1` | Markdown, for sites without pretty permalinks |

`text/markdown` must appear in the `Accept` header with a higher q-value than `text/html`, or the same q-value and listed first. Browsers never send it, so they always get HTML.

### What gets served

- Only published posts, pages and other public post types. Attachments are excluded.
- Never drafts, private posts, previews or password-protected posts. Their `.md` addresses return 404.
- The content is the same HTML the page shows, after blocks and shortcodes render, converted to Markdown. It starts with front matter (`title`, `url`, `last_modified`, `language`) and the title as a heading.

The converter follows screen reader semantics: it drops `aria-hidden` and `hidden` content and decorative images (`alt=""`), and keeps screen-reader-only text. Relative links and image addresses become absolute.

### Caching

Full-page caches and CDNs that key only on the URL may hand agents the cached HTML at the normal address. The `.md` addresses always work. The plugin defines `DONOTCACHEPAGE` on Markdown responses so page-cache plugins don't store Markdown in place of HTML.

### Settings

**Settings → AccessPDF → Markdown for AI agents** turns the feature on or off. It is on by default.

### Filters

| Filter | Purpose |
| --- | --- |
| `accesspdf_markdown_post_types` | Post types that get a Markdown version. Defaults to public types except `attachment`. |
| `accesspdf_markdown_enabled_for_post` | Return `false` to exclude a specific post. |
| `accesspdf_markdown_source_html` | Replace the HTML that gets converted, for example with a converted PDF. |
| `accesspdf_markdown_output` | Change the final Markdown. |

## PDF processing

When **Auto-Process PDFs** is on and an API key is set, uploaded PDFs are sent to the AccessPDF API.

Known issues, not yet fixed:

- The upload goes to `/v1/documents/client/upload`, but the API route is `/v1/client/upload`.
- The returned document ID is never saved on the attachment, so the completion webhook can't update its status.
- The webhook doesn't verify a signature.

## Tests

The converter and `Accept` header logic have tests that run with plain PHP (no WordPress needed):

```bash
php integrations/wordpress/tests/markdown-test.php
```
