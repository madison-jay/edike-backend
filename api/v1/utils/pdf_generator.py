from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from io import BytesIO
import qrcode
from datetime import datetime


def generate_barcode_pdf(
    barcodes_data,
    item_name,
    batch_id,
    boxes_count,
    quantity_per_box,
    password=""
):
    """
    barcodes_data       : list[dict] → {'barcode': str, 'quantity_in_box': int}
    item_name           : str
    batch_id            : str
    boxes_count         : int
    quantity_per_box    : int            ← NEW – qty you entered in the form
    password            : str (optional)
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=LETTER)
    width, height = LETTER

    # -----------------------------------------------------------------
    # 1. Password (your existing method – works with free ReportLab)
    # -----------------------------------------------------------------
    if password:
        c.setAuthor("Inventory System")
        c.setTitle(f"{item_name} – {batch_id}")
        c.setEncrypt(password)

    # -----------------------------------------------------------------
    # 2. Header – clean, centered, professional
    # -----------------------------------------------------------------
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - 25 * mm, item_name)

    c.setFont("Helvetica", 13)
    c.drawCentredString(width / 2, height - 38 * mm, f"Batch ID: {batch_id}")

    c.setFont("Helvetica", 12)
    c.drawCentredString(
        width / 2,
        height - 50 * mm,
        f"{boxes_count} Box{'es' if boxes_count != 1 else ''} • "
        f"{quantity_per_box} pcs per box"
    )

    c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(
        width / 2,
        height - 60 * mm,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )

    # -----------------------------------------------------------------
    # 3. Vertical layout – ONE QR per row (6 per page)
    # -----------------------------------------------------------------
    start_y = height - 80 * mm          # first QR top reference point (top of the first label slot)
    row_height = 38 * mm                # slot height for each label
    margin_x = 30 * mm

    labels_per_page = 6
    
    # Reduced QR size for better fit within the row_height
    qr_size = 25 * mm
    qr_box_size = 8 # Box size adjusted for 25mm QR

    for idx, info in enumerate(barcodes_data):
        if idx > 0 and idx % labels_per_page == 0:
            c.showPage()
            start_y = height - 80 * mm

        # y is the top reference point for the current label slot
        y = start_y - (idx % labels_per_page) * row_height

        # --- DRAWING ELEMENTS (Text -> QR -> Quantity) ---
        
        barcode = info["barcode"]
        
        # 1. Barcode Text (Top)
        c.setFont("Helvetica-Bold", 11) # Slightly smaller font
        
        # Line 1 baseline is 3mm down from the slot top
        text_baseline_1 = y - 3 * mm
        c.drawCentredString(width / 2, text_baseline_1, barcode[:36])

        # Line 2 baseline is 4mm further down
        if len(barcode) > 36:
            text_baseline_2 = y - 7 * mm
            c.drawCentredString(width / 2, text_baseline_2, barcode[36:72])
            # Set the anchor point for the QR code below the second line of text
            qr_top_anchor_y = text_baseline_2 - 2 * mm 
        else:
            # Set the anchor point for the QR code below the first line of text
            qr_top_anchor_y = text_baseline_1 - 2 * mm

        # 2. QR Code (Middle - below the text)
        qr = qrcode.QRCode(version=1, box_size=qr_box_size, border=4)
        qr.add_data(info["barcode"])
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img_io = BytesIO()
        img.save(img_io, "PNG")
        img_io.seek(0)

        # The drawImage Y position is the bottom-left corner.
        # Bottom corner Y = Anchor Y (top of QR) - QR Size
        qr_bottom_y = qr_top_anchor_y - qr_size

        c.drawImage(
            ImageReader(img_io),
            (width - qr_size) / 2,
            qr_bottom_y, # This is the bottom-left corner
            width=qr_size,
            height=qr_size,
            mask="auto"
        )

        # 3. Quantity text (Bottom - below the QR)
        c.setFont("Helvetica", 10) # Slightly smaller font
        qty_baseline_y = qr_bottom_y - 3 * mm # 3mm buffer below QR
        c.drawCentredString(width / 2, qty_baseline_y,
                            f"Qty in this box: {info['quantity_in_box']}")

        # 4. Separator line (Near the bottom of the 38mm slot)
        c.setStrokeColorRGB(0.85, 0.85, 0.85)
        c.line(margin_x, y - 37 * mm, width - margin_x, y - 37 * mm) # Drawn 1mm from the bottom of the slot

    # -----------------------------------------------------------------
    # 4. Save
    # -----------------------------------------------------------------
    c.save()
    buffer.seek(0)
    return buffer