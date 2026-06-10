# -*- coding: utf-8 -*-
"""Kiểm thử logic linh hoạt theo vai trò: party_label, skip_roles, _fill, cross-role."""
import re
from roles import detect_roles, party_label

# stub nhỏ thay cho knowledge.py (chỉ để test logic, không phải dữ liệu thật)
RISK_RULES = [
    {"id": "scope_design_review", "topic": 3, "level": "ĐỎ",
     "skip_roles": ["THAM_TRA_TK", "THAM_TRA_DT", "THIET_KE"],
     "label": "Gán {TV} 'thẩm tra thiết kế'",
     "pattern": r"thẩm tra thiết kế",
     "problem": "Gán cho {TV} làm phình trách nhiệm.", "basis": "Điều 104 NĐ175.", "suggest": "Tách phạm vi."},
    {"id": "penalty_no_cap", "topic": 16, "level": "ĐỎ",
     "label": "Bồi thường toàn bộ không trần",
     "pattern": r"bồi thường toàn bộ",
     "problem": "Trách nhiệm vô hạn cho {TV}.", "basis": "BLDS.", "suggest": "Thêm trần cho {TV}."},
]
LEVEL_ORDER = {"ĐỎ": 0, "CAM": 1, "XANH": 2}


def _fill(t, label):
    return t.replace("{TV}", label) if isinstance(t, str) else t


def scan_findings(paras, label, primary_role=None):
    out = []
    for rule in RISK_RULES:
        if primary_role and primary_role in rule.get("skip_roles", []):
            continue
        if any(re.search(rule["pattern"], p, re.IGNORECASE) for p in paras):
            out.append({"id": rule["id"], "label": _fill(rule["label"], label),
                        "problem": _fill(rule["problem"], label), "suggest": _fill(rule["suggest"], label)})
    return out


cases = {
    "TVGS_creep": ["tư vấn giám sát thi công xây dựng", "bên b phải thẩm tra thiết kế và kiểm định chất lượng kết cấu", "bồi thường toàn bộ thiệt hại"],
    "THAM_TRA":   ["hợp đồng tư vấn thẩm tra thiết kế kỹ thuật", "bồi thường toàn bộ thiệt hại"],
    "QLDA":       ["tư vấn quản lý dự án project management", "bồi thường toàn bộ thiệt hại"],
    "KIEM_DINH":  ["tư vấn kiểm định chất lượng công trình", "bồi thường toàn bộ thiệt hại"],
}

ok = True
for name, paras in cases.items():
    full = "\n".join(paras)
    roles = detect_roles(full)
    label = party_label(roles["primary"])
    finds = scan_findings(paras, label, roles["primary"])
    ids = [f["id"] for f in finds]
    leftover = any("{TV}" in f[k] for f in finds for k in ("label", "problem", "suggest"))
    print(f"=== {name} | primary={roles['primary']} | label='{label}' | findings={ids} | cross={len(roles['cross_role_flags'])} | leftover={leftover}")
    for f in finds:
        print("    -", f["label"], "//", f["problem"])
    # kiểm chứng kỳ vọng
    if name == "THAM_TRA":
        assert "scope_design_review" not in ids, "THẨM TRA không được coi 'thẩm tra thiết kế' là cờ đỏ!"
        assert label == "đơn vị thẩm tra"
    if name == "TVGS_creep":
        assert "scope_design_review" in ids, "TVGS bị gán thẩm tra phải có cờ đỏ!"
        assert len(roles["cross_role_flags"]) >= 2, "Phải có 2 cờ vượt vai trò (thẩm tra + kiểm định)!"
        assert label == "TVGS"
    if name == "QLDA":
        assert label == "đơn vị QLDA"
    if name == "KIEM_DINH":
        assert label == "đơn vị kiểm định"
    if leftover:
        ok = False

print("\nALL ASSERTIONS PASSED" if ok else "\nFAILED: còn sót {TV}")
