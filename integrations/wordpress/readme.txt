=== AccessPDF ===
Contributors: REPLACE-WITH-WPORG-USERNAME
Tags: accessibility, pdf, wcag, ada, markdown
Requires at least: 6.5
Tested up to: 7.1
Requires PHP: 7.4
Stable tag: 1.2.0
License: GPLv2 or later
License URI: https://www.gnu.org/licenses/gpl-2.0.html

Find the PDFs on your site that need accessibility work, and serve Markdown versions of your pages to AI agents.

== Description ==

= PDF inventory =

Media → PDF Inventory lists every PDF in your media library and every PDF your published content links to, and checks each one on your own server. Nothing is sent anywhere.

For each PDF it reports:

* Whether it has accessibility tags.
* Whether it has a text layer, or is likely a scan that needs OCR.
* Page count, document title, language, fillable form fields and encryption.
* Which published pages link to it.

It also finds PDFs linked from your content that live outside the media library, reports broken PDF links, and estimates the cost of remediating the PDFs that need work. PDFs that nothing links to are called out separately: archiving documents that are no longer in use can cost less than fixing them.

Export everything as a CSV.

= Markdown for AI agents =

AI agents read Markdown more reliably than full web pages. Every published post and page gets a Markdown version:

* Add `.md` to any address, for example `/about.md`.
* Agents that send `Accept: text/markdown` get Markdown from the normal address.
* Pages advertise their Markdown version with a `<link rel="alternate">` tag.

Visitors always see the normal page. Drafts, private and password-protected posts are never served.

== Installation ==

1. Install and activate the plugin.
2. Go to Media → PDF Inventory and select Scan PDFs.
3. Optional: adjust Markdown settings under Settings → AccessPDF.

== Frequently Asked Questions ==

= Does the inventory send my files anywhere? =

No. Every check runs on your server.

= What does "Tagged" mean? =

The PDF has an accessibility structure (tags). The inventory doesn't check whether the tags are correct, for example reading order or table headers.

= Why are some PDFs "Encrypted, couldn't check"? =

Some encrypted PDFs hide the parts the inventory reads. Open them in a PDF editor to check them.

= Does serving Markdown affect search engines? =

Markdown responses point search engines to the HTML page as the canonical version.

== External services ==

This plugin can send uploaded PDFs to the AccessPDF API (api.accesspdf.com) to be made accessible. It does this only when you enter an API key and turn on Auto-Process PDFs under Settings → AccessPDF. Both are off until you set them.

When a PDF is uploaded, the plugin sends the file's URL and name, your site's URL, name and domain, the upload date, the plugin version and a callback URL for completion notices.

* Terms of service: https://accesspdf.com/terms
* Privacy policy: https://accesspdf.com/privacy

The PDF inventory and Markdown features don't use any external service.

== Screenshots ==

1. The PDF Inventory: a summary, the estimated cost to fix, and every PDF with its status and the pages that link to it.

== Changelog ==

= 1.2.0 =
* New: PDF inventory under Media → PDF Inventory, with CSV export and a remediation cost estimate.
* Fixed: the settings form now saves.

= 1.1.0 =
* New: Markdown versions of published posts and pages for AI agents.
* Removed: public embeddings API integration.

== Upgrade Notice ==

= 1.2.0 =
Adds the PDF inventory.
