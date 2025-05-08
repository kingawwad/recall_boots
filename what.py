import os
import re
import streamlit as st
from PyPDF2 import PdfReader
from fpdf import FPDF

def extract_article_numbers(pdf_path):
    """
    Extracts all 6-digit article numbers that start with '1' from structured product lines.
    """
    article_numbers = set()
    reader = PdfReader(pdf_path)

    for page in reader.pages:
        text = page.extract_text()
        if not text:
            continue

        lines = text.split("\n")
        for line in lines:
            # Look for 6-digit numbers that start with 1
            matches = re.findall(r'\b1\d{5}\b', line)
            article_numbers.update(matches)

    return article_numbers

def find_matching_descriptions(article_numbers, folder_path, source_pdf_name):
    """
    Searches all PDFs in the specified folder (except for the source PDF) for lines containing any of the article numbers.
    Once an article number is found in any PDF, it moves on to the next article number.
    """
    matches = []
    found_articles = set()  # Set to track already found article numbers

    # Loop through all PDFs in the folder
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".pdf") and filename != source_pdf_name:
            filepath = os.path.join(folder_path, filename)
            reader = PdfReader(filepath)

            # Loop through each page in the current PDF
            for page in reader.pages:
                text = page.extract_text()
                if not text:
                    continue  # Skip empty pages

                # Loop through each line in the extracted text
                for line in text.split("\n"):
                    for number in article_numbers:
                        if number in found_articles:
                            continue  # Skip if this article number is already found

                        # Ensure an exact match of the article number
                        if re.search(rf'\b{number}\b', line):
                            matches.append(line.strip())  # Save the matched line
                            found_articles.add(number)  # Mark this article number as found
                            break  # Stop checking for other article numbers in this line

                    # If all article numbers have been found, no need to continue searching further
                    if len(found_articles) == len(article_numbers):
                        break

            # If all article numbers are found, stop searching this PDF
            if len(found_articles) == len(article_numbers):
                break

    return matches, found_articles

def save_to_pdf(matches, article_numbers, found_articles, output_path="matched_frames.pdf"):
    """
    Saves matched lines to a PDF:
    - Matched lines sorted by article number.
    - Unmatched article numbers listed in red.
    - Exclude descriptions with article numbers that are not found.
    """
    from fpdf import FPDF
    import re

    class PDF(FPDF):
        def header(self):
            self.set_font("Arial", "B", 12)
            self.cell(0, 10, "Matched Frame Descriptions (Sorted by Article Number)", ln=True, align='C')
            self.ln(5)

    # Sort matches by first 6-digit article number in the line
    def get_article_number(line):
        match = re.search(r'\b(\d{6})\b', line)
        return int(match.group(1)) if match else float('inf')

    # Filter out lines that contain article numbers not found in the PDFs
    filtered_matches = []
    for line in matches:
        # Get all the article numbers in the line
        line_numbers = re.findall(r'\b1\d{5}\b', line)
        
        # Check if **all** the article numbers in the line were found
        if all(num in found_articles for num in line_numbers):
            filtered_matches.append(line)

    sorted_matches = sorted(filtered_matches, key=get_article_number)

    # Extract matched article numbers
    matched_numbers = set()
    for line in sorted_matches:
        match = re.search(r'\b(\d{6})\b', line)
        if match:
            matched_numbers.add(match.group(1))

    # Find unmatched ones
    global not_found 
    not_found= sorted(set(article_numbers) - matched_numbers, key=lambda x: int(x))

    # Write to PDF
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)

    # Write matched lines
    for line in sorted_matches:
        pdf.set_text_color(0, 0, 0)  # Black
        pdf.multi_cell(0, 10, txt=line)

    # Write unmatched numbers in red
    if not_found:
        pdf.ln(10)
        pdf.set_font("Arial", "B", 10)
        pdf.set_text_color(200, 0, 0)
        pdf.cell(0, 10, "Articles NOT FOUND:", ln=True)
        
        pdf.set_font("Arial", size=10)
        for nf in not_found:
            pdf.cell(0, 10, f"NOT FOUND: {nf}", ln=True)  # ✅ inside the loop

    pdf.output(output_path)
    return output_path

# Streamlit Interface
def main():
    st.title("PDF Article Number Finder")

    # File upload for the main PDF
    uploaded_main_pdf = st.file_uploader("Upload the main PDF", type=["pdf"])
    if uploaded_main_pdf is not None:
        # Extract article numbers from the uploaded main PDF
        with open("main_pdf.pdf", "wb") as f:
            f.write(uploaded_main_pdf.read())
        article_numbers = extract_article_numbers("main_pdf.pdf")
        st.write(f"Found {len(article_numbers)} article numbers")

        # File uploader for other PDFs
        uploaded_pdfs = st.file_uploader("Upload other PDFs for comparison", type=["pdf"], accept_multiple_files=True)
        
        if uploaded_pdfs:
            # Save the uploaded PDFs to a folder
            folder_path = "uploaded_pdfs"
            os.makedirs(folder_path, exist_ok=True)

            for uploaded_pdf in uploaded_pdfs:
                with open(os.path.join(folder_path, uploaded_pdf.name), "wb") as f:
                    f.write(uploaded_pdf.read())
            
            # Find matching descriptions in the uploaded PDFs
            matches, found_articles = find_matching_descriptions(article_numbers, folder_path, "main_pdf.pdf")
            
            # Save results to PDF
            output_pdf_path = save_to_pdf(matches, article_numbers, found_articles)

            # Display the matched results in the Streamlit app
            st.write(f"Found {len(matches)} matched descriptions.")
            st.write(f"Not Found {len(not_found)} you will find them in the pdf in red")
            

            # Provide download link for the generated PDF
            with open(output_pdf_path, "rb") as f:
                st.download_button("Download Matched Descriptions PDF", f, file_name="matched_frames.pdf")

# Run Streamlit app
if __name__ == "__main__":
    main()
