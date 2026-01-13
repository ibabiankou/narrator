import io

from fpdf import FPDF

def create_pdf(content: list[list[str]]) -> io.BytesIO:
    pdf = FPDF()
    font_size = 12
    pdf.set_font("Helvetica", size=font_size)

    for page in content:
        pdf.add_page()
        for line in page:
            pdf.cell(0, font_size, txt=line, ln=True)

    return io.BytesIO(pdf.output(dest="S").encode('latin1'))
