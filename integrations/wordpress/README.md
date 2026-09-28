# AccessPDF WordPress plugin

Inventories a site's PDFs for accessibility, serves a Markdown version of published posts and pages to AI agents, and sends uploaded PDFs to the AccessPDF service for processing.

## PDF inventory

**Media → PDF Inventory** lists every PDF in the media library and every PDF that published content links to. It checks each file on the site's own server, shows which pages link to it, and estimates the cost of fixing the ones that need work. Nothing is sent to an outside service.

### What each file is checked for

| Check         | How it's determined                                                                                                                                                                      |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Tags          | The document catalog has a structure tree (`/StructTreeRoot`). This shows tags exist, not that they're correct.                                                                          |
| Text layer    | The file uses at least one font. Files with images and no fonts are reported as "No text layer (likely scanned)".                                                                        |
| Pages         | The page tree's `/Count`.                                                                                                                                                                |
| Title         | The document info title, or `dc:title` in XMP metadata. Bookmark titles don't count.                                                                                                     |
| Language      | The catalog's `/Lang`.                                                                                                                                                                   |
| Fillable form | Form fields (`/FT`) are present.                                                                                                                                                         |
| Encrypted     | The trailer has `/Encrypt`. When encryption hides the catalog, the file is reported as "Encrypted, couldn't check"; fields hidden by encryption are reported as unknown, not as missing. |
| PDF/UA claim  | `pdfuaid:part` in XMP metadata.                                                                                                                                                          |

The checker is a small parser in plain PHP (`includes/class-accesspdf-pdf-analyzer.php`). It reads the trailer to find the catalog and document info, including inside compressed object streams, and handles incremental updates. Files over 50 MB are reported as "Too large to check here".

### Links

Published posts, pages and other public post types are searched for `href`, `src` and `data` attributes ending in `.pdf`. Each link is classified as:

- **Media library:** matched to its attachment.
- **Outside the media library:** a file on this server, such as one uploaded by FTP. It is checked like any other PDF, or reported as "Linked file not found" if it doesn't exist.
- **Another site:** counted, not opened.

PDFs that no published content links to are called out separately. Under the ADA Title II rule, documents no longer in use may qualify for an exception, so archiving or removing them can cost less than fixing them.

### Scanning

- New uploads are checked automatically.
- **Scan PDFs** runs a full scan in batches through `POST /wp-json/accesspdf/v1/inventory/scan` (requires `manage_options`), so large sites don't time out.
- Rescans skip files whose size and modified time haven't changed.
- **Download CSV** exports every row, with cells that start with `=`, `+`, `-` or `@` prefixed so spreadsheets don't run them as formulas.

### Cost estimate

Pages in untagged and scanned PDFs, multiplied by typical manual remediation rates of $2.50 to $12 per page. A second figure leaves out PDFs that nothing links to.

### Not covered yet

- Whether existing tags are correct (reading order, table headers, alt text).
- Links in menus, widgets and page-builder data.
- Files stored off the server by media offload plugins. They show as "Couldn't read".
- Encrypted files whose catalog is inside an encrypted object stream.

### Filters

| Filter                           | Purpose                                                             |
| -------------------------------- | ------------------------------------------------------------------- |
| `accesspdf_inventory_capability` | Capability needed to view and scan. Defaults to `manage_options`.   |
| `accesspdf_inventory_max_bytes`  | Largest file that will be read. Defaults to 50 MB.                  |
| `accesspdf_inventory_rates`      | `['low' => 2.50, 'high' => 12.00]` per-page rates for the estimate. |

## Markdown for AI agents

AI agents read Markdown more reliably than full web pages, which carry navigation, scripts and styling. The plugin gives every published post and page a Markdown version. Visitors always see the normal page.

| Request                                         | Response                                                                                                               |
| ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `GET /admissions/` from a browser               | The normal HTML page, plus `<link rel="alternate" type="text/markdown">`, a matching `Link` header, and `Vary: Accept` |
| `GET /admissions.md`                            | Markdown (`text/markdown`), with a `Link: rel="canonical"` header pointing at the HTML page                            |
| `GET /admissions/` with `Accept: text/markdown` | Markdown, marked `Cache-Control: no-store, private` so shared caches don't store it under the HTML address             |
| `GET /index.md`                                 | The static front page, when one is set                                                                                 |
| `GET /?page_id=5&accesspdf_md=1`                | Markdown, for sites without pretty permalinks                                                                          |

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

| Filter                                | Purpose                                                                               |
| ------------------------------------- | ------------------------------------------------------------------------------------- |
| `accesspdf_markdown_post_types`       | Post types that get a Markdown version. Defaults to public types except `attachment`. |
| `accesspdf_markdown_enabled_for_post` | Return `false` to exclude a specific post.                                            |
| `accesspdf_markdown_source_html`      | Replace the HTML that gets converted, for example with a converted PDF.               |
| `accesspdf_markdown_output`           | Change the final Markdown.                                                            |

## PDF processing

When **Auto-Process PDFs** is on and an API key is set, uploaded PDFs are sent to the AccessPDF API.

Known issues, not yet fixed:

- The upload goes to `/v1/documents/client/upload`, but the API route is `/v1/client/upload`.
- The returned document ID is never saved on the attachment, so the completion webhook can't update its status.
- The webhook doesn't verify a signature.

## Tests

These tests run with plain PHP (no WordPress needed):

```bash
php integrations/wordpress/tests/markdown-test.php       # Markdown converter and Accept header logic
php integrations/wordpress/tests/pdf-inventory-test.php  # PDF checker, link extraction, CSV safety
```
