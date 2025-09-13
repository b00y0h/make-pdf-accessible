#!/usr/bin/env python3
import fitz  # PyMuPDF
import pdfplumber

pdf_path = "/app/test-document-with-rich.pdf"

print("Testing PDF extraction...")

# Test with pdfplumber
print("\n=== PDFPLUMBER ===")
with pdfplumber.open(pdf_path) as pdf:
    for page_num, page in enumerate(pdf.pages, 1):
        print(f"\nPage {page_num}:")

        # Check for images
        if hasattr(page, 'images'):
            print(f"  Images found: {len(page.images) if page.images else 0}")
            if page.images:
                for idx, img in enumerate(page.images):
                    print(f"    Image {idx}: bbox={img.get('bbox', 'N/A')}, size={img.get('width', 0)}x{img.get('height', 0)}")

        # Check for tables
        tables = page.extract_tables()
        print(f"  Tables found: {len(tables) if tables else 0}")
        if tables:
            for idx, table in enumerate(tables):
                if table:
                    print(f"    Table {idx}: {len(table)} rows x {len(table[0]) if table else 0} columns")

# Test with PyMuPDF
print("\n=== PYMUPDF (fitz) ===")
doc = fitz.open(pdf_path)
for page_num, page in enumerate(doc, 1):
    print(f"\nPage {page_num}:")

    # Get images
    image_list = page.get_images()
    print(f"  Images found: {len(image_list)}")
    for idx, img in enumerate(image_list):
        xref = img[0]
        print(f"    Image {idx}: xref={xref}, size={img[2]}x{img[3]}")

    # Get drawings/vector graphics
    drawings = page.get_drawings()
    print(f"  Vector drawings found: {len(drawings)}")

doc.close()
