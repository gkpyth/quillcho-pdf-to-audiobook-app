import fitz

# Open the PDF
pdf_path = "lighthouse.pdf"         # Replace with the actual path to your PDF file
doc = fitz.open(pdf_path)

# Extract text from all pages
full_text = ""
for page in doc:
    full_text += page.get_text()

doc.close()

# Print the full text
print(full_text)