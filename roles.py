# -*- coding: utf-8 -*-
"""
Nhận diện VAI TRÒ tư vấn của hợp đồng + tri thức phạm vi/căn cứ/độc lập từng vai trò.

Nguồn: reference/cac_vai_tro_tu_van.md (skill texo-hopdong-checker).
Mỗi vai trò tư vấn có PHẠM VI CHUẨN và CĂN CỨ PHÁP LÝ riêng. Khi rà soát:
  (1) xác định vai trò chính;
  (2) đối chiếu phạm vi hợp đồng với phạm vi chuẩn;
  (3) cảnh báo nếu gán việc của vai trò KHÁC (scope creep chéo vai trò).
"""
import re

# Nhãn ngắn của ĐƠN VỊ TƯ VẤN (Bên B) theo vai trò — dùng để điền vào báo cáo thay cho
# chữ "TVGS" gán cứng. Nhờ vậy báo cáo linh hoạt theo loại hợp đồng.
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
    """Nhãn ngắn của Bên B theo vai trò; mặc định 'đơn vị tư vấn (Bên B)'."""
    return PARTY_LABEL.get(role_id, PARTY_LABEL_DEFAULT)


# id, name, keywords(regex), scope, basis, independence(optional), review
ROLES = [
    {
        "id": "TVGS",
        "name": "Tư vấn giám sát thi công (TVGS)",
        "pattern": r"giám sát thi công|tư vấn giám sát|giám sát xây dựng|construction supervision|tvgs",
        "scope": "Kiểm tra năng lực nhà thầu; kiểm tra biện pháp thi công so với thiết kế đã duyệt; "
                 "xem xét & chấp thuận; kiểm tra vật liệu/thiết bị; đôn đốc tiến độ; giám sát an toàn; "
                 "đề nghị điều chỉnh thiết kế khi phát hiện sai sót; yêu cầu tạm dừng khi mất an toàn; "
                 "kiểm tra/xác nhận bản vẽ hoàn công; nghiệm thu & xác nhận khối lượng.",
        "basis": "Phạm vi: Điều 19 NĐ 06/2021. Năng lực: chứng chỉ giám sát thi công, Điều 107 NĐ 175/2024.",
        "independence": "Tổ chức giám sát KHÔNG được tham gia kiểm định công trình do MÌNH giám sát "
                        "(Điều 19.7.b NĐ 06/2021, công trình vốn nhà nước).",
        "review": "Cờ đỏ nếu hợp đồng gán TVGS 'thẩm tra thiết kế', 'phê duyệt biện pháp', "
                  "'lập hồ sơ nghiệm thu' → vượt vai trò, đòi năng lực khác.",
    },
    {
        "id": "QLDA",
        "name": "Tư vấn quản lý dự án (QLDA)",
        "pattern": r"quản lý dự án|tvqlda|qlda|project management|pmc\b",
        "scope": "Lập kế hoạch & mục tiêu; quản lý tiến độ; quản lý chi phí/khối lượng (QS, claim, EOT, "
                 "dòng tiền, đánh giá thanh toán nhà thầu); quản lý đấu thầu; quản lý hợp đồng & pháp lý; "
                 "quản lý thiết kế (tổ chức thẩm tra); tổ chức công trường; quản lý chất lượng; "
                 "chạy thử & bàn giao; quản lý HSE/môi trường.",
        "basis": "Quản lý dự án theo Luật Xây dựng & NĐ 175/2024 (hình thức tổ chức QLDA, năng lực tổ chức "
                 "tư vấn QLDA); trách nhiệm quản lý thi công theo NĐ 06/2021.",
        "independence": None,
        "review": "QLDA gánh trách nhiệm RỘNG (chi phí, đấu thầu, hợp đồng) → soi kỹ giới hạn trách nhiệm; "
                  "QLDA thường THAY MẶT CĐT trong giới hạn ủy quyền → cần rõ ranh giới ủy quyền, phê duyệt "
                  "cuối cùng vẫn của CĐT; phí phải tương xứng phạm vi.",
    },
    {
        "id": "THAM_TRA_TK",
        "name": "Tư vấn thẩm tra thiết kế",
        "pattern": r"thẩm tra thiết kế|thẩm tra hồ sơ thiết kế|design appraisal|design (check|review)|thẩm tra .{0,10}(tkkt|tkbvtc|bản vẽ thi công|thiết kế kỹ thuật)",
        "scope": "Thẩm tra sự phù hợp của thiết kế bước sau so với bước trước; tuân thủ quy chuẩn/tiêu chuẩn "
                 "& vật liệu; AN TOÀN công trình (kiểm tra thuyết minh tính toán kết cấu, KIỂM TÍNH ĐỘC LẬP "
                 "để đối chiếu — cốt lõi); hợp lý công nghệ; PCCC & môi trường.",
        "basis": "Thẩm tra TK cơ sở: K6 Đ71 Luật XD + Mẫu 02 PL I NĐ 175/2024. Thẩm tra TKKT/TKBVTC: Điều 87a "
                 "Luật XD + K6 Đ82 + K4 Đ46 NĐ 175/2024 (Mẫu 09 PL I). Năng lực: Điều 104 NĐ 175/2024.",
        "independence": "Phải ĐỘC LẬP pháp lý & tài chính với nhà thầu lập thiết kế; có quyền bảo lưu kết quả "
                        "và từ chối yêu cầu làm sai lệch.",
        "review": "Nêu RÕ loại & giai đoạn thẩm tra (cơ sở / TKKT / TKBVTC) vì căn cứ & mẫu báo cáo khác nhau; "
                  "trách nhiệm gắn với kết quả thẩm tra trong phạm vi yêu cầu, KHÔNG gánh trách nhiệm của "
                  "người thiết kế hay người thẩm định/phê duyệt.",
    },
    {
        "id": "THAM_TRA_DT",
        "name": "Tư vấn thẩm tra dự toán / tổng mức đầu tư",
        "pattern": r"thẩm tra dự toán|thẩm tra tổng mức|thẩm tra .{0,15}chi phí|thẩm tra .{0,10}dự toán",
        "scope": "Phù hợp khối lượng dự toán với khối lượng thiết kế; đúng đắn/hợp lý của định mức, đơn giá; "
                 "xác định giá trị dự toán sau thẩm tra; phân tích tăng/giảm.",
        "basis": "K4 Đ82 Luật XD 2014; phạm vi tại Điểm a & d K1 Đ84 NĐ 175/2024 (gắn chứng chỉ ĐỊNH GIÁ "
                 "xây dựng); nội dung dẫn chiếu K7 Đ83 Luật XD.",
        "independence": "Độc lập với nhà thầu lập dự toán/thiết kế.",
        "review": "Cần năng lực ĐỊNH GIÁ xây dựng (khác năng lực thẩm tra thiết kế); trách nhiệm theo kết quả "
                  "thẩm tra chi phí, không bao trùm trách nhiệm người lập dự toán.",
    },
    {
        "id": "KIEM_DINH",
        "name": "Tư vấn kiểm định chất lượng công trình",
        "pattern": r"kiểm định chất lượng|kiểm định công trình|kiểm định kết cấu|kiểm định xây dựng|inspection of quality",
        "scope": "Khảo sát hiện trạng, kiểm tra hư hỏng; dò cốt thép & đường kính; kiểm tra cường độ bê tông "
                 "(siêu âm + súng bật nẩy); thí nghiệm/kiểm định kết cấu, đánh giá an toàn chịu lực; lập báo "
                 "cáo kiểm định.",
        "basis": "Kiểm định & thí nghiệm đối chứng theo Điều 5 NĐ 06/2021; năng lực tổ chức kiểm định theo "
                 "NĐ 175/2024.",
        "independence": "Tổ chức GIÁM SÁT không được kiểm định công trình do mình giám sát (Điều 19.7.b NĐ "
                        "06/2021) — tránh xung đột lợi ích giám sát ↔ kiểm định.",
        "review": "Rõ phương pháp/khối lượng thí nghiệm & đơn giá; trách nhiệm theo kết quả kiểm định, KHÔNG "
                  "bao trùm chất lượng thi công của nhà thầu.",
    },
    {
        "id": "KHAO_SAT",
        "name": "Tư vấn khảo sát xây dựng",
        "pattern": r"khảo sát xây dựng|khảo sát địa chất|khảo sát địa hình|khảo sát .{0,10}công trình",
        "scope": "Lập phương án & nhiệm vụ khảo sát; thực hiện khảo sát (địa hình, địa chất…); bảo đảm chất "
                 "lượng khảo sát; lập báo cáo kết quả khảo sát.",
        "basis": "Trách nhiệm & chất lượng khảo sát theo Luật XD; NĐ 06/2021; NĐ 175/2024.",
        "independence": None,
        "review": "Trách nhiệm gắn với nhiệm vụ & phương án khảo sát đã duyệt; làm rõ khối lượng & đơn giá "
                  "khảo sát.",
    },
    {
        "id": "THIET_KE",
        "name": "Tư vấn thiết kế xây dựng",
        "pattern": r"tư vấn thiết kế|nhà thầu thiết kế|đơn vị thiết kế|hợp đồng .{0,10}thiết kế|design consultant",
        "scope": "Lập hồ sơ thiết kế theo bước (TK cơ sở / TKKT / TKBVTC); chịu trách nhiệm về chất lượng "
                 "thiết kế; giám sát tác giả.",
        "basis": "Nhà thầu thiết kế chịu trách nhiệm chất lượng thiết kế; việc thẩm tra/thẩm định/phê duyệt "
                 "KHÔNG thay thế & không giảm trách nhiệm người thiết kế (Luật XD; NĐ 175/2024).",
        "independence": None,
        "review": "Phân biệt giám sát tác giả (của nhà thầu thiết kế) với TVGS thi công; trách nhiệm thiết kế "
                  "không bị mở rộng sang thi công.",
    },
    {
        "id": "LAP_DA",
        "name": "Tư vấn lập dự án / Báo cáo NCKT / KT-KT",
        "pattern": r"báo cáo nghiên cứu khả thi|lập dự án đầu tư|báo cáo kinh tế.{0,3}kỹ thuật|bcnckt|lập báo cáo",
        "scope": "Lập Báo cáo nghiên cứu khả thi / Báo cáo kinh tế-kỹ thuật / hồ sơ dự án đầu tư.",
        "basis": "Tư vấn lập dự án theo Luật Xây dựng & NĐ 175/2024.",
        "independence": None,
        "review": "Làm rõ phạm vi sản phẩm và trách nhiệm theo giai đoạn lập dự án.",
    },
]

# Cờ đỏ scope creep chéo vai trò: nếu vai trò chính là X mà hợp đồng gán việc của Y.
# (mỗi mục: vai trò chính 'primary' bị gán việc 'foreign' → cảnh báo)
CROSS_ROLE_FLAGS = [
    {
        "primary": "TVGS", "foreign_pattern": r"thẩm tra thiết kế",
        "note": "Hợp đồng giám sát (TVGS) lại gán việc THẨM TRA THIẾT KẾ — khác năng lực (Điều 104 vs 107 "
                "NĐ 175/2024). Tách phạm vi/phí hoặc bỏ; nếu giữ phải có chứng chỉ thẩm tra.",
    },
    {
        "primary": "TVGS", "foreign_pattern": r"kiểm định (chất lượng|công trình|kết cấu)",
        "note": "Hợp đồng TVGS gán cả KIỂM ĐỊNH — vi phạm yêu cầu độc lập: tổ chức giám sát không được kiểm "
                "định công trình do mình giám sát (Điều 19.7.b NĐ 06/2021).",
    },
    {
        "primary": "THAM_TRA_TK", "foreign_pattern": r"giám sát thi công",
        "note": "Hợp đồng thẩm tra thiết kế lại gán GIÁM SÁT THI CÔNG — hai năng lực khác nhau; tách phạm vi.",
    },
    {
        "primary": "KIEM_DINH", "foreign_pattern": r"giám sát thi công",
        "note": "Hợp đồng kiểm định gán cả GIÁM SÁT — cảnh báo xung đột lợi ích & yêu cầu độc lập.",
    },
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

    # scope creep chéo vai trò
    cross = []
    for f in CROSS_ROLE_FLAGS:
        if primary == f["primary"] and re.search(f["foreign_pattern"], full_text, re.IGNORECASE):
            cross.append(f["note"])

    role_meta = {r["id"]: r for r in ROLES}
    return {
        "counts": counts,
        "present_ids": present_ids,
        "primary": primary,
        "primary_meta": role_meta.get(primary),
        "multi_role": multi,
        "present_meta": [role_meta[i] for i in present_ids],
        "cross_role_flags": cross,
    }
