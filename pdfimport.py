import fitz  # PyMuPDF

doc = fitz.open("data/NLL-Policy-Manual-Dec2025-1.pdf")
for i, page in enumerate(doc):
    text = page.get_text()
    marker = "◀ FOUND PROCTORING" if "proctoring" in text.lower() else ""
    print(f"Page {i+1}: {len(text)} characters {marker}")