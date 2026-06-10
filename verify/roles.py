# -*- coding: utf-8 -*-
"""Bản verify của roles.py (giống hệt module gốc) — chỉ để chạy kiểm thử."""
import re

PARTY_LABEL = {
    "TVGS": "TVGS",
    "QLDA": "đơn vị QLDA",
    "THAM_TRA_TK": "đơn vị thẩm tra",
    "THAM_TRA_DT": "đơn vị thẩm tra dự toán",
    "KIEM_DINH": "đơn vị kiểm định",
    "KHAO_SAT": "đơn vị khảo sát",
    "THIET_KE": "đơn vị thiết kế",
    "LAP_DA": "đơn vị tư vấn lập dự án",
}
PARTY_LABEL_DEFAULT = "đơn vị tư vấn (Bên B)"


def party_label(role_id):
    return PARTY_LABEL.get(role_id, PARTY_LABEL_DEFAULT)


ROLES = [
    {"id": "TVGS", "name": "Tư vấn giám sát thi công (TVGS)",
     "pattern": r"giám sát thi công|tư vấn giám sát|giám sát xây dựng|construction supervision|tvgs",
     "scope": "Kiểm tra năng lực nhà thầu; kiểm tra biện pháp thi công; chấp thuận vật liệu; đôn đốc tiến độ; nghiệm thu.",
     "basis": "Phạm vi: Điều 19 NĐ 06/2021. Năng lực: Điều 107 NĐ 175/2024.",
     "independence": "Tổ chức giám sát KHÔNG được kiểm định công trình do mình giám sát (Điều 19.7.b NĐ 06/2021).",
     "review": "Cờ đỏ nếu gán TVGS 'thẩm tra thiết kế', 'phê duyệt biện pháp', 'lập hồ sơ nghiệm thu'."},
    {"id": "QLDA", "name": "Tư vấn quản lý dự án (QLDA)",
     "pattern": r"quản lý dự án|tvqlda|qlda|project management|pmc\b",
     "scope": "Quản lý tiến độ, chi phí, đấu thầu, hợp đồng, thiết kế, công trường, chất lượng, bàn giao.",
     "basis": "Luật Xây dựng & NĐ 175/2024; trách nhiệm quản lý thi công theo NĐ 06/2021.",
     "independence": None,
     "review": "Trách nhiệm RỘNG → soi giới hạn trách nhiệm; rõ ranh giới ủy quyền, phê duyệt cuối của CĐT."},
    {"id": "THAM_TRA_TK", "name": "Tư vấn thẩm tra thiết kế",
     "pattern": r"thẩm tra thiết kế|thẩm tra hồ sơ thiết kế|design appraisal|design (check|review)|thẩm tra .{0,10}(tkkt|tkbvtc|bản vẽ thi công|thiết kế kỹ thuật)",
     "scope": "Thẩm tra phù hợp bước thiết kế; an toàn (kiểm tính kết cấu độc lập); PCCC & môi trường.",
     "basis": "TK cơ sở: K6 Đ71 Luật XD (Mẫu 02). TKKT/TKBVTC: Điều 87a + K4 Đ46 NĐ 175/2024 (Mẫu 09). Năng lực Điều 104.",
     "independence": "ĐỘC LẬP pháp lý & tài chính với nhà thầu thiết kế; quyền bảo lưu kết quả.",
     "review": "Nêu RÕ loại & giai đoạn thẩm tra; không gánh trách nhiệm người thiết kế/thẩm định."},
    {"id": "THAM_TRA_DT", "name": "Tư vấn thẩm tra dự toán / tổng mức đầu tư",
     "pattern": r"thẩm tra dự toán|thẩm tra tổng mức|thẩm tra .{0,15}chi phí|thẩm tra .{0,10}dự toán",
     "scope": "Phù hợp khối lượng; định mức, đơn giá; giá trị dự toán sau thẩm tra.",
     "basis": "K4 Đ82 Luật XD; Điểm a&d K1 Đ84 NĐ 175/2024 (chứng chỉ ĐỊNH GIÁ).",
     "independence": "Độc lập với nhà thầu lập dự toán/thiết kế.",
     "review": "Cần năng lực ĐỊNH GIÁ; trách nhiệm theo kết quả thẩm tra chi phí."},
    {"id": "KIEM_DINH", "name": "Tư vấn kiểm định chất lượng công trình",
     "pattern": r"kiểm định chất lượng|kiểm định công trình|kiểm định kết cấu|kiểm định xây dựng|inspection of quality",
     "scope": "Khảo sát hiện trạng; thí nghiệm/kiểm định kết cấu; đánh giá an toàn chịu lực; lập báo cáo.",
     "basis": "Điều 5 NĐ 06/2021; năng lực tổ chức kiểm định theo NĐ 175/2024.",
     "independence": "Tổ chức GIÁM SÁT không được kiểm định công trình do mình giám sát (Điều 19.7.b NĐ 06/2021).",
     "review": "Rõ phương pháp/khối lượng thí nghiệm; trách nhiệm theo kết quả kiểm định."},
    {"id": "KHAO_SAT", "name": "Tư vấn khảo sát xây dựng",
     "pattern": r"khảo sát xây dựng|khảo sát địa chất|khảo sát địa hình|khảo sát .{0,10}công trình",
     "scope": "Phương án & nhiệm vụ khảo sát; thực hiện khảo sát; báo cáo kết quả.",
     "basis": "Luật XD; NĐ 06/2021; NĐ 175/2024.",
     "independence": None,
     "review": "Trách nhiệm gắn nhiệm vụ khảo sát đã duyệt; rõ khối lượng & đơn giá."},
    {"id": "THIET_KE", "name": "Tư vấn thiết kế xây dựng",
     "pattern": r"tư vấn thiết kế|nhà thầu thiết kế|đơn vị thiết kế|hợp đồng .{0,10}thiết kế|design consultant",
     "scope": "Lập hồ sơ thiết kế theo bước; chịu trách nhiệm chất lượng thiết kế; giám sát tác giả.",
     "basis": "Nhà thầu thiết kế chịu trách nhiệm; thẩm tra/thẩm định không giảm trách nhiệm người thiết kế.",
     "independence": None,
     "review": "Phân biệt giám sát tác giả với TVGS thi công."},
    {"id": "LAP_DA", "name": "Tư vấn lập dự án / Báo cáo NCKT / KT-KT",
     "pattern": r"báo cáo nghiên cứu khả thi|lập dự án đầu tư|báo cáo kinh tế.{0,3}kỹ thuật|bcnckt|lập báo cáo",
     "scope": "Lập BCNCKT / BC KT-KT / hồ sơ dự án đầu tư.",
     "basis": "Luật Xây dựng & NĐ 175/2024.",
     "independence": None,
     "review": "Rõ phạm vi sản phẩm theo giai đoạn lập dự án."},
]

CROSS_ROLE_FLAGS = [
    {"primary": "TVGS", "foreign_pattern": r"thẩm tra thiết kế",
     "note": "Hợp đồng giám sát (TVGS) lại gán THẨM TRA THIẾT KẾ — khác năng lực (Điều 104 vs 107 NĐ 175/2024)."},
    {"primary": "TVGS", "foreign_pattern": r"kiểm định (chất lượng|công trình|kết cấu)",
     "note": "Hợp đồng TVGS gán cả KIỂM ĐỊNH — vi phạm độc lập (Điều 19.7.b NĐ 06/2021)."},
    {"primary": "THAM_TRA_TK", "foreign_pattern": r"giám sát thi công",
     "note": "Hợp đồng thẩm tra thiết kế lại gán GIÁM SÁT THI CÔNG — tách phạm vi."},
    {"primary": "KIEM_DINH", "foreign_pattern": r"giám sát thi công",
     "note": "Hợp đồng kiểm định gán cả GIÁM SÁT — xung đột lợi ích."},
]


def detect_roles(full_text):
    counts = {}
    for r in ROLES:
        n = len(re.findall(r["pattern"], full_text, re.IGNORECASE))
        if n > 0:
            counts[r["id"]] = n
    primary = max(counts, key=counts.get) if counts else None
    present_ids = [rid for rid, c in sorted(counts.items(), key=lambda x: -x[1])]
    multi = sum(1 for c in counts.values() if c >= 2) > 1
    cross = []
    for f in CROSS_ROLE_FLAGS:
        if primary == f["primary"] and re.search(f["foreign_pattern"], full_text, re.IGNORECASE):
            cross.append(f["note"])
    role_meta = {r["id"]: r for r in ROLES}
    return {
        "counts": counts, "present_ids": present_ids, "primary": primary,
        "primary_meta": role_meta.get(primary), "multi_role": multi,
        "present_meta": [role_meta[i] for i in present_ids], "cross_role_flags": cross,
    }
