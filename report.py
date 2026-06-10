# -*- coding: utf-8 -*-
"""
Sinh báo cáo rà soát hợp đồng ra file Word (.docx) — khổ A4, Times New Roman,
bảng màu theo mức rủi ro. Báo cáo ĐỘC LẬP (không tham chiếu hợp đồng/dự án khác).

Trả về bytes của file .docx để Streamlit tải về.
"""
import io
from datetime import datetime

from docx import Document
from docx.shared import Pt, RGBColor, Twips
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from knowledge import DO, CAM, XANH, LEVEL_LABEL

# Màu cờ
C_DO = RGBColor(0xC0, 0x00, 0x00)
C_CAM = RGBColor(0xC4, 0x59, 0x11)
C_XANH = RGBColor(0x2E, 0x7D, 0x32)
C_HEAD = RGBColor(0x1F, 0x37, 0x64)
LEVEL_RGB = {DO: C_DO, CAM: C_CAM, XANH: C_XANH}
# Nền ô tiêu đề mức rủi ro
LEVEL_FILL = {DO: "F8CBAD", CAM: "FCE4D6", XANH: "E2EFDA"}

FONT = "Times New Roman"
CONTENT_WIDTH = 9026  # DXA, khổ A4 trừ lề


def _set_font(run, size=13, bold=False, color=None, italic=False):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), FONT)
    rfonts.set(qn("w:hAnsi"), FONT)
    rfonts.set(qn("w:cs"), FONT)


def _shade(cell, fill_hex):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    tcpr.append(shd)


def _para(doc, text="", size=13, bold=False, color=None, italic=False,
          align=None, space_after=4):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.space_before = Pt(0)
    if text:
        r = p.add_run(text)
        _set_font(r, size, bold, color, italic)
    return p


def _heading(doc, text, size=14):
    p = _para(doc, text, size=size, bold=True, color=C_HEAD, space_after=6)
    return p


def _cell_text(cell, text, size=11, bold=False, color=None, italic=False):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.space_before = Pt(2)
    r = p.add_run(text)
    _set_font(r, size, bold, color, italic)
    return p


def _add_cell_line(cell, label, text, size=11):
    p = cell.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.space_before = Pt(0)
    r1 = p.add_run(label)
    _set_font(r1, size, bold=True)
    r2 = p.add_run(text)
    _set_font(r2, size)


def build_report(result: dict) -> bytes:
    doc = Document()

    # Khổ A4 + lề
    sec = doc.sections[0]
    sec.page_width = Twips(11906)
    sec.page_height = Twips(16838)
    sec.left_margin = Twips(1440)
    sec.right_margin = Twips(1440)
    sec.top_margin = Twips(1080)
    sec.bottom_margin = Twips(1080)

    style = doc.styles["Normal"]
    style.font.name = FONT
    style.font.size = Pt(13)

    ctx = result["context"]
    meta = result["meta"]
    summary = result["summary"]

    # ---- Tiêu đề ----
    _para(doc, "CÔNG TY CỔ PHẦN TEXO TƯ VẤN VÀ ĐẦU TƯ",
          size=12, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _para(doc, "BÁO CÁO RÀ SOÁT PHÁP LÝ HỢP ĐỒNG",
          size=16, bold=True, color=C_HEAD, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _para(doc, "(Góc nhìn Đơn vị tư vấn — Bên B)",
          size=12, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _para(doc, f"Ngày lập: {datetime.now().strftime('%d/%m/%Y')}",
          size=11, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

    # ---- 1. Thông tin chung ----
    _heading(doc, "1. THÔNG TIN CHUNG & BỐI CẢNH")
    _para(doc, f"• Tệp hợp đồng: {meta['filename']}", space_after=2)
    _para(doc, f"• Quy mô: {meta['n_paragraphs']} đoạn, {meta['n_headings']} đề mục, "
               f"{meta['n_comments']} ghi chú (comment).", space_after=2)
    _para(doc, f"• Kiểu kết cấu: {ctx['kieu_ket_cau']}.", space_after=2)
    langs = ", ".join(ctx["content_languages"]) or "vi"
    _para(doc, f"• Ngôn ngữ: {langs}"
               f"{' (song ngữ)' if ctx['song_ngu'] else ''}.", space_after=2)
    _para(doc, f"• Nguồn vốn: {ctx['nguon_von']}.", space_after=2)
    _para(doc, f"• Trần phạt áp dụng: {ctx['tran_phat']}.", space_after=2)
    _para(doc, f"• Đối chiếu mẫu TT 02/2023/TT-BXD: {ctx['ghi_chu_tt02']}", space_after=8)

    # ---- Vai trò tư vấn ----
    roles = result.get("roles") or {}
    pm = roles.get("primary_meta")
    if pm:
        _heading(doc, "1b. VAI TRÒ TƯ VẤN & PHẠM VI CHUẨN")
        _para(doc, f"• Vai trò chính (đoán): {pm['name']}.", space_after=2)
        if roles.get("multi_role"):
            others = ", ".join(m["name"] for m in roles["present_meta"] if m["id"] != pm["id"])
            _para(doc, f"• Hợp đồng có thể GỘP NHIỀU vai trò (cũng thấy: {others}) → tách "
                       f"phạm vi & căn cứ pháp lý từng phần.", color=C_CAM, space_after=2)
        _para(doc, f"• Phạm vi chuẩn: {pm['scope']}", size=11, space_after=2)
        _para(doc, f"• Căn cứ pháp lý: {pm['basis']}", size=11, space_after=2)
        if pm.get("independence"):
            _para(doc, f"• Yêu cầu độc lập: {pm['independence']}", size=11, space_after=2)
        _para(doc, f"• Lưu ý rà soát: {pm['review']}", size=11, space_after=2)
        for note in roles.get("cross_role_flags", []):
            _para(doc, f"• [Cờ đỏ – vượt vai trò] {note}", size=11, bold=True,
                  color=C_DO, space_after=2)
        _para(doc, "", space_after=6)

    # ---- 2. Tóm tắt điều hành ----
    _heading(doc, "2. TÓM TẮT ĐIỀU HÀNH")
    _para(doc,
          f"Phát hiện {summary[DO]} rủi ro mức CAO (đỏ), {summary[CAM]} rủi ro mức "
          f"TRUNG BÌNH (cam), và {summary['missing']} chủ đề chuẩn không thấy xuất hiện "
          f"trong hợp đồng (trong đó {summary['missing_do']} thuộc nhóm trọng yếu).",
          space_after=4)
    _para(doc,
          "Lưu ý: đây là kết quả rà soát SƠ BỘ bằng công cụ tự động (đối chiếu mẫu câu "
          "và độ phủ chủ đề), KHÔNG thay thế ý kiến luật sư. Mọi phát hiện cần người "
          "có chuyên môn kiểm chứng lại trên bản hợp đồng gốc trước khi đàm phán/ký.",
          size=11, italic=True, space_after=8)

    # ---- 3. Bảng phân tích rủi ro ----
    _heading(doc, "3. BẢNG PHÂN TÍCH RỦI RO PHÁT HIỆN")
    findings = result["findings"]
    if not findings:
        _para(doc, "Không phát hiện mẫu câu rủi ro điển hình nào. Vẫn nên rà soát thủ "
                   "công và xem mục độ phủ chủ đề bên dưới.", italic=True, space_after=8)
    else:
        table = doc.add_table(rows=1, cols=3)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.style = "Table Grid"
        widths = [1500, 4400, 3126]
        hdr = table.rows[0].cells
        for c, (w, label) in enumerate(zip(widths, ["Mức / Chủ đề", "Vấn đề & căn cứ", "Đề xuất đàm phán"])):
            _cell_text(hdr[c], label, size=11, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
            _shade(hdr[c], "1F3764")
        for f in findings:
            row = table.add_row().cells
            # cột 1: mức + chủ đề
            _cell_text(row[0], f"[{LEVEL_LABEL[f['level']]}]", size=11, bold=True,
                       color=LEVEL_RGB[f["level"]])
            _add_cell_line(row[0], "Chủ đề ", str(f["topic"]))
            p = row[0].add_paragraph()
            r = p.add_run(f["label"])
            _set_font(r, 10, italic=True)
            _shade(row[0], LEVEL_FILL[f["level"]])
            # cột 2: vấn đề + trích dẫn + căn cứ
            _cell_text(row[1], f["problem"], size=11)
            _add_cell_line(row[1], "Trích: ", f"“{f['quote']}”", size=10)
            _add_cell_line(row[1], "Căn cứ: ", f["basis"], size=10)
            # cột 3: đề xuất
            _cell_text(row[2], f["suggest"], size=11)
        # set column widths
        for row in table.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Twips(w)
        _para(doc, "", space_after=6)

    # ---- 4. Độ phủ chủ đề ----
    _heading(doc, "4. ĐỘ PHỦ 21 CHỦ ĐỀ CHUẨN (chủ đề THIẾU cũng là rủi ro)")
    missing = [c for c in result["coverage"] if not c["present"]]
    if not missing:
        _para(doc, "Hợp đồng có nhắc tới toàn bộ 21 chủ đề chuẩn.", italic=True, space_after=8)
    else:
        t2 = doc.add_table(rows=1, cols=3)
        t2.alignment = WD_TABLE_ALIGNMENT.CENTER
        t2.style = "Table Grid"
        w2 = [800, 3200, 5026]
        hdr = t2.rows[0].cells
        for c, label in enumerate(["Mức", "Chủ đề thiếu", "Khuyến nghị"]):
            _cell_text(hdr[c], label, size=11, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
            _shade(hdr[c], "1F3764")
        for m in missing:
            row = t2.add_row().cells
            _cell_text(row[0], LEVEL_LABEL[m["missing_risk"]], size=10, bold=True,
                       color=LEVEL_RGB[m["missing_risk"]])
            _cell_text(row[1], f"{m['id']}. {m['name']}", size=11)
            _cell_text(row[2], m["missing_note"], size=11)
            _shade(row[0], LEVEL_FILL[m["missing_risk"]])
        for row in t2.rows:
            for i, w in enumerate(w2):
                row.cells[i].width = Twips(w)
        _para(doc, "", space_after=6)

    # ---- 5. Ghi chú/comment trong file ----
    if result["comments"]:
        _heading(doc, "5. GHI CHÚ (COMMENT) CÓ SẴN TRONG FILE")
        for c in result["comments"]:
            _para(doc, f"• [{c['author']} – {c['date']}] {c['text']}", size=11, space_after=2)
        _para(doc, "", space_after=6)

    # ---- 6. Lưu ý ----
    _heading(doc, "6. LƯU Ý SỬ DỤNG")
    _para(doc,
          "Báo cáo do công cụ tự động lập theo bộ tiêu chí rà soát hợp đồng TVGS của "
          "TEXO, không sử dụng AI. Công cụ phát hiện theo MẪU CÂU và TỪ KHÓA nên có thể "
          "bỏ sót cách diễn đạt lạ hoặc báo nhầm khi câu chữ trùng từ khóa. Hãy coi đây "
          "là bước sàng lọc đầu tiên; quyết định đàm phán/ký kết phải dựa trên rà soát "
          "của người có chuyên môn trên bản gốc.", size=11, space_after=4)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
