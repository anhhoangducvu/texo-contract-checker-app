# -*- coding: utf-8 -*-
"""
Engine phân tích hợp đồng RULE-BASED (không dùng AI).

Đầu vào: file .docx hoặc .pdf (bytes hoặc đường dẫn).
Đầu ra: dict kết quả gồm
  - meta        : tên file, số đoạn, số comment
  - context     : ngôn ngữ, song ngữ, kiểu kết cấu, nguồn vốn (đoán), trần phạt áp dụng
  - roles       : vai trò tư vấn (TVGS/QLDA/thẩm tra/kiểm định...) + nhãn Bên B
  - structure   : danh sách heading (điều/mục/phụ lục)
  - findings    : danh sách rủi ro phát hiện (theo RISK_RULES) — kèm trích dẫn câu
  - coverage    : 21 chủ đề — có/không, mức rủi ro khi thiếu
  - comments    : comment trong file (nếu có)
  - en_warnings : thuật ngữ tiếng Anh cần lưu ý
  - summary     : đếm theo mức rủi ro
"""
import io, os, re, zipfile
import xml.etree.ElementTree as ET

from knowledge import (
    RISK_RULES, TOPICS, EN_WARN_TERMS, DO, CAM, XANH, LEVEL_ORDER,
)
from roles import detect_roles, party_label

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

VI_DIACRITIC = re.compile(r"[À-ɏḀ-ỿ]")
EN_WORDS = re.compile(
    r"\b(the|and|of|to|in|for|shall|agreement|party|parties|hereby|contract|article|"
    r"clause|payment|consultant|employer|contractor|works|conditions|supervision|"
    r"liability|indemnif|damages|termination|force majeure|whereas)\b", re.IGNORECASE)


# --------------------------------------------------------------------------- #
# 1. TRÍCH XUẤT VĂN BẢN
# --------------------------------------------------------------------------- #
def _lang_of(s):
    han = len(re.findall(r"[一-鿿]", s))
    lat = len(re.findall(r"[a-zA-ZÀ-ɏḀ-ỿ]", s))
    if han > 0 and han >= lat:
        return "zh"
    if VI_DIACRITIC.search(s):
        return "vi"
    if lat > 0:
        return "en" if len(EN_WORDS.findall(s)) >= 2 else "vi"
    return "other"


def _read_docx(data: bytes):
    """Trả về (paragraphs, comments). paragraphs = list[str]."""
    paras, comments = [], []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        if "word/document.xml" in names:
            body = ET.fromstring(z.read("word/document.xml")).find(W + "body")
            if body is not None:
                for p in body.iter(W + "p"):
                    line = "".join(t.text for t in p.iter(W + "t") if t.text).strip()
                    if line:
                        paras.append(line)
        if "word/comments.xml" in names:
            for c in ET.fromstring(z.read("word/comments.xml")).findall(W + "comment"):
                txt = "".join(t.text for t in c.iter(W + "t") if t.text).strip()
                if txt:
                    comments.append({
                        "author": c.get(W + "author") or "(không rõ)",
                        "date": (c.get(W + "date") or "")[:10],
                        "text": txt,
                    })
    return paras, comments


def _read_pdf(data: bytes):
    """Trả về (paragraphs, []). Cần pdfplumber; nếu thiếu thì thử PyPDF2."""
    paras = []
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                txt = page.extract_text() or ""
                for line in txt.split("\n"):
                    line = line.strip()
                    if line:
                        paras.append(line)
        return paras, []
    except Exception:
        pass
    try:
        from pypdf import PdfReader
    except Exception:
        from PyPDF2 import PdfReader  # type: ignore
    reader = PdfReader(io.BytesIO(data))
    for page in reader.pages:
        txt = page.extract_text() or ""
        for line in txt.split("\n"):
            line = line.strip()
            if line:
                paras.append(line)
    return paras, []


def extract(data: bytes, filename: str):
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        return _read_pdf(data)
    return _read_docx(data)


# --------------------------------------------------------------------------- #
# 2. KẾT CẤU & BỐI CẢNH
# --------------------------------------------------------------------------- #
HEADING_PATTERNS = [
    ("phan",    re.compile(r"^(PHẦN|PART)\s+[0-9IVX]+", re.IGNORECASE)),
    ("chuong",  re.compile(r"^(CHƯƠNG|CHAPTER|SECTION)\s+[0-9IVX]+", re.IGNORECASE)),
    ("phu_luc", re.compile(r"^(PHỤ\s*LỤC|APPENDIX|SCHEDULE|ANNEX)", re.IGNORECASE)),
    ("dieu",    re.compile(r"^(Điều\s+\d+|Article\s+\d+|Clause\s+\d+)\s*[\.:–\-]?", re.IGNORECASE)),
]
RECITAL = re.compile(r"^(WHEREAS|XÉT RẰNG|NOW IT IS HEREBY AGREED|NAY CÁC BÊN)", re.IGNORECASE)
CHUNG_RIENG = re.compile(
    r"(ĐIỀU KIỆN CHUNG|ĐIỀU KIỆN RIÊNG|ĐIỀU KIỆN CỤ THỂ|"
    r"GENERAL CONDITIONS|PARTICULAR CONDITIONS|SPECIFIC CONDITIONS)", re.IGNORECASE)
PRIORITY_HINT = re.compile(
    r"(thứ tự ưu tiên|ưu tiên áp dụng|order of precedence|shall prevail|takes precedence)",
    re.IGNORECASE)

# Heuristic nguồn vốn
PUBLIC_FUND = re.compile(
    r"(vốn (đầu tư công|ngân sách|nhà nước)|ngân sách nhà nước|đầu tư công|ppp|"
    r"vốn ngân sách|kho bạc nhà nước)", re.IGNORECASE)
PRIVATE_FUND = re.compile(
    r"(vốn (tư nhân|doanh nghiệp|fdi|nước ngoài)|nhà đầu tư nước ngoài|"
    r"100% vốn|foreign (invest|capital))", re.IGNORECASE)


def _is_caps_heading(t):
    letters = [c for c in t if c.isalpha()]
    if not (8 <= len(t) <= 80) or len(letters) < 6:
        return False
    if t.endswith("."):
        return False
    upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
    return upper_ratio > 0.85 and not t.startswith("(")


def detect_structure(paras):
    headings = []
    for txt in paras:
        matched = False
        for kind, pat in HEADING_PATTERNS:
            if pat.match(txt):
                headings.append({"kind": kind, "text": txt[:120]})
                matched = True
                break
        if not matched and _is_caps_heading(txt):
            headings.append({"kind": "muc", "text": txt[:120]})
    return headings


def detect_context(paras, headings, full_text):
    langs = {}
    for txt in paras:
        l = _lang_of(txt)
        langs[l] = langs.get(l, 0) + 1
    content_langs = [l for l in ("vi", "en", "zh") if langs.get(l, 0) >= 3]
    so_dieu = sum(1 for h in headings if h["kind"] == "dieu")
    so_muc = sum(1 for h in headings if h["kind"] == "muc")
    has_recital = any(RECITAL.match(t) for t in paras)
    co_en = langs.get("en", 0) >= 3

    if has_recital or (co_en and so_dieu == 0):
        kieu = "Thông luật / quốc tế (common-law, FIDIC...)"
    elif so_dieu >= 3:
        kieu = "Dân luật VN — đánh số 'Điều N'"
    elif so_muc >= 4:
        kieu = "Dân luật VN — đề mục IN HOA"
    else:
        kieu = "Không xác định rõ"

    # Đoán nguồn vốn
    pub = len(PUBLIC_FUND.findall(full_text))
    pri = len(PRIVATE_FUND.findall(full_text))
    if pri > pub and pri > 0:
        von = "Tư nhân / FDI (đoán)"
        tran_phat = "8% (Luật Thương mại) — áp dụng khi ngoài vốn nhà nước"
        tt02 = "Mẫu TT02 chỉ để THAM KHẢO — dùng làm đòn bẩy đàm phán."
    elif pub > 0:
        von = "Vốn công / nhà nước / PPP (đoán)"
        tran_phat = "12% (Luật Xây dựng, Điều 146) — bắt buộc với vốn nhà nước"
        tt02 = "Mẫu TT02 BẮT BUỘC áp dụng — viện dẫn để buộc tuân thủ."
    else:
        von = "Chưa xác định — cần hỏi CĐT"
        tran_phat = "8% (ngoài vốn NN) hoặc 12% (vốn NN) — xác định theo nguồn vốn"
        tt02 = "Xác định nguồn vốn trước để biết mẫu TT02 bắt buộc hay tham khảo."

    return {
        "languages": langs,
        "content_languages": content_langs,
        "song_ngu": len(content_langs) >= 2,
        "kieu_ket_cau": kieu,
        "co_dieu_kien_chung_rieng": bool(CHUNG_RIENG.search(full_text)),
        "co_thu_tu_uu_tien": bool(PRIORITY_HINT.search(full_text)),
        "so_dieu": so_dieu,
        "so_muc": so_muc,
        "so_phu_luc": sum(1 for h in headings if h["kind"] == "phu_luc"),
        "nguon_von": von,
        "tran_phat": tran_phat,
        "ghi_chu_tt02": tt02,
    }


# --------------------------------------------------------------------------- #
# 3. QUÉT RỦI RO & ĐỘ PHỦ
# --------------------------------------------------------------------------- #
def _find_sentence(paras, pattern):
    """Trả về câu đầu tiên khớp pattern (để trích dẫn)."""
    rx = re.compile(pattern, re.IGNORECASE)
    for txt in paras:
        if rx.search(txt):
            return txt.strip()
    return None


def _fill(text, label):
    """Điền nhãn Bên B theo vai trò vào chỗ giữ {TV}."""
    return text.replace("{TV}", label) if isinstance(text, str) else text


def scan_findings(paras, label, primary_role=None):
    findings = []
    for rule in RISK_RULES:
        # Bỏ qua rule không áp dụng cho vai trò hiện tại (vd 'thẩm tra thiết kế' là việc
        # đúng vai trò của đơn vị thẩm tra/thiết kế, không phải cờ đỏ).
        if primary_role and primary_role in rule.get("skip_roles", []):
            continue
        sentence = _find_sentence(paras, rule["pattern"])
        if sentence:
            findings.append({
                "id": rule["id"],
                "topic": rule["topic"],
                "level": rule["level"],
                "label": _fill(rule["label"], label),
                "quote": sentence[:300],
                "problem": _fill(rule["problem"], label),
                "basis": _fill(rule["basis"], label),
                "suggest": _fill(rule["suggest"], label),
            })
    findings.sort(key=lambda f: (LEVEL_ORDER[f["level"]], f["topic"]))
    return findings


def scan_coverage(full_text_lower, label):
    coverage = []
    for topic in TOPICS:
        present = any(k.lower() in full_text_lower for k in topic["keywords"])
        coverage.append({
            "id": topic["id"],
            "name": _fill(topic["name"], label),
            "present": present,
            "missing_risk": topic["missing_risk"],
            "missing_note": _fill(topic["missing_note"], label),
        })
    return coverage


def scan_en_warnings(full_text_lower, label=""):
    out = []
    for term, note in EN_WARN_TERMS.items():
        if term in full_text_lower:
            out.append({"term": term, "note": _fill(note, label)})
    return out


# --------------------------------------------------------------------------- #
# 4. ĐIỂM VÀO CHÍNH
# --------------------------------------------------------------------------- #
def analyze(data: bytes, filename: str):
    paras, comments = extract(data, filename)
    if not paras:
        raise ValueError(
            "Không trích xuất được nội dung. Nếu là PDF scan (ảnh), cần bản có chữ "
            "(text), hoặc chuyển sang .docx trước."
        )
    full_text = "\n".join(paras)
    full_lower = full_text.lower()

    headings = detect_structure(paras)
    context = detect_context(paras, headings, full_text)
    roles = detect_roles(full_text)
    label = party_label(roles.get("primary"))
    roles["party_label"] = label
    findings = scan_findings(paras, label, roles.get("primary"))
    coverage = scan_coverage(full_lower, label)
    en_warnings = scan_en_warnings(full_lower, label)

    missing_topics = [c for c in coverage if not c["present"]]
    summary = {
        DO: sum(1 for f in findings if f["level"] == DO),
        CAM: sum(1 for f in findings if f["level"] == CAM),
        "missing": len(missing_topics),
        "missing_do": sum(1 for c in missing_topics if c["missing_risk"] == DO),
    }

    return {
        "meta": {
            "filename": filename,
            "n_paragraphs": len(paras),
            "n_comments": len(comments),
            "n_headings": len(headings),
        },
        "context": context,
        "roles": roles,
        "structure": headings,
        "findings": findings,
        "coverage": coverage,
        "comments": comments,
        "en_warnings": en_warnings,
        "summary": summary,
    }
