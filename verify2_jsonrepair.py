# -*- coding: utf-8 -*-
"""Kiểm thử bộ vá JSON cắt cụt (verbatim từ llm.py)."""
import json, re


def _balance_json(s):
    i = s.find("{")
    if i == -1:
        return s
    s = s[i:]
    out, stack, in_str, esc = [], [], False, False
    for ch in s:
        if in_str:
            out.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True; out.append(ch)
        elif ch in "{[":
            stack.append(ch); out.append(ch)
        elif ch in "}]":
            if stack:
                stack.pop()
            out.append(ch)
        else:
            out.append(ch)
    res = "".join(out)
    if in_str:
        res += '"'
    res = res.rstrip()
    while res and res[-1] in ",:":
        res = res[:-1].rstrip()
    for ch in reversed(stack):
        res += "}" if ch == "{" else "]"
    return res


def _extract_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.find("{"); end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            pass
    try:
        return json.loads(_balance_json(text))
    except Exception:
        pass
    return None


# Mô phỏng phản hồi Gemini bị cắt cụt giống ảnh chụp của user:
truncated = '''```json
{
  "vai_tro": "Tư vấn thẩm tra thiết kế và dự toán (Bên B). Cảnh báo Scope Creep nghiêm trọng",
  "nguon_von": "Dự án Nhà ở xã hội cho lực lượng công an do Bộ Công An chấp thuận",
  "tom_tat_dieu_hanh": "Hợp đồng chứa nhiều điều khoản bất lợi cho Bên B (TEXO). Tiến độ thẩm tra quá ngắn",
  "dieu_khoan": [
    {"ref": "Điều 1.1", "muc_do": "ĐỎ", "van_de": "Phạm vi quá rộng, vượt thẩm tra", "de_xuat": "Giới hạn phạm vi"},
    {"ref": "Điều 5.4", "muc_do": "CAM", "van_de": "Không tạm ứng nên bất lợi dòng tiền cho Bên'''

r = _extract_json(truncated)
assert r is not None, "Không vá được JSON cắt cụt!"
print("OK — vá được JSON cắt cụt.")
print("  vai_tro:", r["vai_tro"][:40], "...")
print("  số điều khoản giữ được:", len(r["dieu_khoan"]))
print("  điều khoản cuối (bị cắt) van_de:", r["dieu_khoan"][-1]["van_de"][:40], "...")
# JSON bình thường vẫn parse đúng
assert _extract_json('{"a":1,"b":[1,2]}') == {"a": 1, "b": [1, 2]}
print("OK — JSON đầy đủ vẫn parse đúng.")
