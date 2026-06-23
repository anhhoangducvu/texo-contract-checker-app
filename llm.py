# -*- coding: utf-8 -*-
"""
Lớp "bộ não" AI (tùy chọn) cho app rà soát hợp đồng tư vấn xây dựng.

- Hỗ trợ 4 nhà cung cấp qua REST API (không cần SDK nặng): Anthropic (Claude),
  Google (Gemini), OpenAI (ChatGPT) và mọi endpoint TƯƠNG THÍCH OpenAI (base URL tùy ý).
- AI hoạt động theo cơ chế BỔ SUNG TRÊN NỀN RULE-BASED: kết quả quét rule-based (vai trò,
  21 chủ đề, cờ rủi ro) được đưa vào prompt làm ĐIỂM TỰA để AI xác minh, phân tích sâu và
  bổ sung — hạn chế bỏ sót và bịa.
- Trả về một dict có cấu trúc để render ra báo cáo Word đầy đủ.

LƯU Ý BẢO MẬT: khi bật AI, TOÀN VĂN hợp đồng được gửi tới nhà cung cấp đã chọn. Người dùng
tự chịu trách nhiệm về API key và dữ liệu gửi đi (xem cảnh báo trong app & README).
"""
import json
import re

import requests

# --------------------------------------------------------------------------- #
# Cấu hình nhà cung cấp
# --------------------------------------------------------------------------- #
PROVIDERS = {
    "anthropic": {
        "label": "Anthropic (Claude)",
        "default_model": "claude-sonnet-4-5",
        "needs_base_url": False,
        "key_hint": "Bắt đầu bằng 'sk-ant-...'",
        "models_note": "VD: claude-sonnet-4-5, claude-opus-4-1, claude-3-5-sonnet-latest",
    },
    "gemini": {
        "label": "Google (Gemini)",
        "default_model": "gemini-2.0-flash",
        "needs_base_url": False,
        "key_hint": "API key từ Google AI Studio",
        "models_note": "Free tier hay bị 429 với gemini-2.0-flash → thử gemini-2.0-flash-lite "
                       "hoặc gemini-1.5-flash. Bản trả phí: gemini-2.5-pro.",
    },
    "openai": {
        "label": "OpenAI (ChatGPT)",
        "default_model": "gpt-4o",
        "needs_base_url": False,
        "key_hint": "Bắt đầu bằng 'sk-...'",
        "models_note": "VD: gpt-4o, gpt-4o-mini, gpt-4.1",
    },
    "openai_compat": {
        "label": "API tương thích OpenAI (base URL tùy ý)",
        "default_model": "",
        "needs_base_url": True,
        "key_hint": "Key của dịch vụ tương thích (OpenRouter, Azure, nội bộ…)",
        "models_note": "Điền đúng tên model mà endpoint của bạn hỗ trợ.",
    },
}

DEFAULT_TIMEOUT = 120
MAX_CONTRACT_CHARS = 60000  # cắt bớt hợp đồng quá dài để vừa giới hạn token


# --------------------------------------------------------------------------- #
# Tri thức skill nhúng vào prompt (điểm tựa cho AI) — bản cô đọng
# --------------------------------------------------------------------------- #
SKILL_SYSTEM = """Bạn là CHUYÊN GIA PHÁP LÝ hợp đồng xây dựng của Công ty CP TEXO Tư vấn và
Đầu tư, rà soát hợp đồng tư vấn dưới góc nhìn ĐƠN VỊ TƯ VẤN (Bên B) để BẢO VỆ QUYỀN LỢI
Bên B. Áp dụng cho mọi vai trò tư vấn: giám sát thi công (TVGS), quản lý dự án (QLDA), thẩm
tra thiết kế/dự toán, kiểm định, khảo sát, thiết kế.

⚠️ QUAN TRỌNG — CĂN CỨ PHÁP LÝ: CHỈ được trích dẫn các căn cứ có trong bảng dưới đây.
TUYỆT ĐỐI KHÔNG tự sinh căn cứ từ kiến thức huấn luyện — pháp luật xây dựng VN vừa thay đổi
lớn từ 01/7/2026, mọi căn cứ cũ (NĐ 06/2021, NĐ 175/2024, Luật XD 2014) đã hết hiệu lực.

BẢNG CĂN CỨ PHÁP LÝ HIỆN HÀNH (hiệu lực từ 01/7/2026):
• Luật XD 135/2025/QH15 (thay Luật XD 50/2014):
  - Điều 56.2.c: nguyên tắc khách quan trong giám sát thi công
  - Điều 86: phạt vi phạm hợp đồng — tính trên GIÁ TRỊ PHẦN NGHĨA VỤ vi phạm;
    trần 12% (vốn đầu tư công/PPP, Khoản 3 Điều 86);
    vốn tư nhân/FDI: Luật XD không quy định trần → áp Luật TM Điều 301
  - Điều 10: bảo hiểm TNNN chỉ bắt buộc KS + TK từ cấp II; TVGS KHÔNG bắt buộc
• NĐ 207/2026/NĐ-CP (thay NĐ 06/2021):
  - Điều 20: 13 nhiệm vụ TVGS (điểm a→m): kiểm tra – chấp thuận – đề nghị – yêu cầu – nghiệm thu
  - Điều 20.5.b: vốn NN/PPP cấm tuyệt đối TVGS tham gia kiểm định công trình do mình giám sát
  - Điều 8: kiểm định chất lượng công trình
• NĐ 212/2026/NĐ-CP (thay NĐ 175/2024 hết hiệu lực 01/7/2026):
  - Điều 37: năng lực cá nhân giám sát thi công
  - Điều 41: năng lực tổ chức tự kê khai trên csdlhdxd.gov.vn — không bắt buộc chứng chỉ tổ chức
• Luật Thương mại 2005: Điều 301 — trần phạt 8% nếu cả hai bên là thương nhân (áp cho vốn tư nhân/FDI)
• BLDS 2015: Điều 360 (bồi thường thiệt hại); Điều 419 (loại trừ thiệt hại); Điều 428 (đơn phương chấm dứt)
• TT 02/2023/TT-BXD Phụ lục II: mẫu hợp đồng tư vấn chuẩn (bắt buộc vốn NN; tham khảo vốn tư nhân)
• NĐ 13/2023/NĐ-CP: bảo vệ dữ liệu cá nhân (PDPA)
LƯU Ý: Phạt ≠ Bồi thường — hai nghĩa vụ độc lập; trần phạt KHÔNG tự động áp cho bồi thường.

NGUYÊN TẮC CỐT LÕI:
1. Luôn đứng về phía Bên B: tìm mọi điều khoản đẩy rủi ro/chi phí/trách nhiệm sang Bên B.
2. Rà theo CHỦ ĐỀ RỦI RO, không theo số điều. Quét ĐỦ 21 chủ đề bắt buộc (liệt kê bên dưới).
   Chủ đề THIẾU cũng là rủi ro — phải ghi nhận.
3. Xác định NGUỒN VỐN: vốn công/PPP → trần phạt 12% Khoản 3 Điều 86 Luật XD 135, mẫu TT02
   BẮT BUỘC; tư nhân/FDI → trần phạt 8% Điều 301 Luật TM (nếu cả hai bên là thương nhân), TT02
   là đòn bẩy đàm phán.
4. Xác định đúng VAI TRÒ tư vấn, đối chiếu phạm vi chuẩn; cảnh báo gán việc ngoài vai trò.
5. Soi tính ĐỐI XỨNG: mỗi chế tài áp lên Bên B thì CĐT có chế tài tương ứng không?
6. Soi TRẦN trách nhiệm & loại thiệt hại: có trần phạt VÀ trần bồi thường không? Có loại trừ
   thiệt hại gián tiếp không? 'Hoàn trả toàn bộ' là cờ đỏ.
7. Phạt tính trên GIÁ TRỊ PHẦN NGHĨA VỤ BỊ VI PHẠM, không phải tổng hợp đồng.

PHẠM VI THEO VAI TRÒ (chỉ dùng căn cứ từ bảng trên):
- TVGS: Điều 20 NĐ 207/2026 (13 điểm a→m). KHÔNG thẩm tra thiết kế; KHÔNG phê duyệt biện
  pháp thi công (nhà thầu lập, CĐT duyệt); KHÔNG lập hồ sơ nghiệm thu/hoàn công.
  Độc lập kiểm định: vốn NN/PPP cấm tuyệt đối (Điều 20.5.b NĐ 207/2026); vốn tư nhân không
  cấm cứng nhưng vi phạm nguyên tắc khách quan (Điều 56.2.c Luật XD 135/2025).
  Năng lực: cá nhân Điều 37 NĐ 212/2026; tổ chức tự kê khai Điều 41 NĐ 212/2026.
- QLDA: phạm vi rộng; thường thay mặt CĐT trong giới hạn ủy quyền — cần rõ ranh giới.
- Thẩm tra thiết kế: phải ĐỘC LẬP với nhà thầu thiết kế; không gánh trách nhiệm người TK.
- Thẩm tra dự toán: cần năng lực ĐỊNH GIÁ xây dựng (NĐ 212/2026).
- Kiểm định: Điều 8 NĐ 207/2026; yêu cầu độc lập theo Điều 20.5.b NĐ 207/2026.

21 CHỦ ĐỀ BẮT BUỘC (phải có entry trong "dieu_khoan" cho MỖI chủ đề, kể cả khi không tìm
thấy điều khoản tương ứng — lúc đó ref = "Thiếu", muc_do = "CAM" hoặc "ĐỎ"):
1) Định nghĩa & diễn giải; 2) Hồ sơ HĐ & thứ tự ưu tiên; 3) Phạm vi công việc;
4) Chất lượng/tiêu chuẩn; 5) Thời gian/tiến độ; 6) Giá & điều chỉnh giá;
7) Tạm ứng/thu hồi/giữ lại; 8) Thanh toán & quyết toán (thời hạn, lãi chậm trả);
9) Bảo lãnh; 10) Bảo hiểm; 11) Nghĩa vụ Bên B (sau thanh lý); 12) Nghĩa vụ & chế tài CĐT;
13) Nhân lực; 14) Bản quyền/SHTT; 15) Bảo mật; 16) Phạt vi phạm & bồi thường thiệt hại;
17) Liêm chính/chống hối lộ; 18) Tạm ngừng & chấm dứt hợp đồng; 19) Bất khả kháng;
20) Chuyển nhượng; 21) Luật áp dụng, tranh chấp, ngôn ngữ.
Bổ sung nếu gặp: 22) PDPA/bảo vệ dữ liệu cá nhân; 23) Thuế GTGT; 24) Điều khoản thông luật
(indemnify/hold harmless, novation, best endeavours, ngôn ngữ ưu tiên nước ngoài).

YÊU CẦU ĐẦU RA: chỉ trả về DUY NHẤT một JSON hợp lệ (không kèm giải thích, không ```).
Schema:
{
  "thong_tin_hop_dong": {
    "ten_du_an": "tên dự án/công trình (trích từ hợp đồng)",
    "ten_cdt": "tên Chủ đầu tư / Bên A",
    "ten_tu_van": "tên đơn vị tư vấn / Bên B",
    "so_hop_dong": "số hiệu hợp đồng",
    "gia_hop_dong": "giá trị hợp đồng (số + đơn vị tiền tệ)",
    "thoi_han": "thời hạn thực hiện",
    "goi_thau": "tên gói thầu (nếu có)",
    "loai_hop_dong": "loại hợp đồng (trọn gói / theo thời gian / khác)"
  },
  "vai_tro": "nhận định vai trò tư vấn (kèm cảnh báo gán việc ngoài vai trò nếu có)",
  "nguon_von": "vốn công/PPP hay tư nhân/FDI, trần phạt áp dụng và căn cứ cụ thể",
  "tong_quan_chung": "3–6 câu tóm tắt rủi ro trọng yếu (thay 'tom_tat_dieu_hanh')",
  "dieu_khoan": [
    {
      "chu_de": "số chủ đề (1–21)",
      "ref": "Điều/Điểm thực tế hoặc 'Thiếu' nếu không có",
      "muc_do": "ĐỎ|CAM|XANH",
      "van_de": "vấn đề & rủi ro cho Bên B — CHỈ trích dẫn căn cứ từ bảng pháp lý đã cung cấp",
      "de_xuat": "đề xuất đàm phán/sửa đổi cụ thể"
    }
  ],
  "dieu_khoan_co_loi": ["điều khoản CÓ LỢI cho Bên B cần bảo vệ — ghi rõ điều/điểm"],
  "thieu_sot": ["nội dung THIẾU so với mẫu TT02 cần bổ sung"],
  "uu_tien_dam_phan": {
    "phai_dat": ["ưu tiên 1 — mô tả ngắn gọn"],
    "nen_dat": ["ưu tiên 2"],
    "don_dep": ["ưu tiên 3 — sửa câu chữ nhỏ"]
  }
}
Phân tích kỹ, bằng tiếng Việt. ĐỦ 21 chủ đề trong dieu_khoan. CHỈ dùng căn cứ từ bảng trên."""


def _grounding_from_rule_based(result):
    """Tạo phần 'điểm tựa' từ kết quả rule-based để AI bám vào."""
    roles = result.get("roles") or {}
    pm = roles.get("primary_meta")
    lines = []
    lines.append("KẾT QUẢ QUÉT RULE-BASED (điểm tựa — hãy XÁC MINH lại trên văn bản, "
                 "phân tích sâu hơn và BỔ SUNG; sửa nếu phát hiện sai):")
    lines.append(f"- Vai trò chính (đoán): {pm['name'] if pm else 'chưa rõ'}; "
                 f"nhãn Bên B: {roles.get('party_label','')}.")
    for n in roles.get("cross_role_flags", []):
        lines.append(f"- [Cảnh báo vượt vai trò] {n}")
    ctx = result.get("context") or {}
    lines.append(f"- Nguồn vốn (đoán): {ctx.get('nguon_von','')}; trần phạt: {ctx.get('tran_phat','')}.")
    if result.get("findings"):
        lines.append("- Cờ rủi ro phát hiện tự động:")
        for f in result["findings"]:
            lines.append(f"    [{f['level']}] (chủ đề {f['topic']}) {f['label']} — trích: \"{f['quote'][:120]}\"")
    miss = [c for c in result.get("coverage", []) if not c["present"]]
    if miss:
        lines.append("- Chủ đề CHUẨN không thấy xuất hiện (thiếu cũng là rủi ro): "
                     + "; ".join(f"{m['id']}.{m['name']}" for m in miss))
    return "\n".join(lines)


def build_user_prompt(result, contract_text):
    txt = contract_text or ""
    truncated = False
    if len(txt) > MAX_CONTRACT_CHARS:
        txt = txt[:MAX_CONTRACT_CHARS]
        truncated = True
    grounding = _grounding_from_rule_based(result)
    note = ("\n\n[LƯU Ý: hợp đồng dài đã bị cắt bớt để vừa giới hạn — ưu tiên phân tích phần "
            "có sẵn và nêu rõ cần đọc thêm phần còn lại.]" if truncated else "")
    return (f"{grounding}\n\n===== TOÀN VĂN HỢP ĐỒNG CẦN RÀ SOÁT =====\n{txt}{note}\n\n"
            "Hãy trả về DUY NHẤT JSON theo schema đã nêu. Nhớ: (1) điền đủ thong_tin_hop_dong "
            "từ văn bản hợp đồng; (2) dieu_khoan phải có ĐÚNG 21 entry (một entry cho mỗi chủ "
            "đề); (3) CHỈ dùng căn cứ pháp lý từ bảng đã cung cấp trong system prompt.")


# --------------------------------------------------------------------------- #
# Gọi API từng nhà cung cấp
# --------------------------------------------------------------------------- #
MAX_OUTPUT_TOKENS = 32000  # đủ rộng để báo cáo dài không bị cắt cụt


def _call_anthropic(model, key, system, user, base_url=None):
    url = (base_url or "https://api.anthropic.com").rstrip("/") + "/v1/messages"
    r = requests.post(url, timeout=DEFAULT_TIMEOUT,
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": model, "max_tokens": 16000, "system": system,
              "messages": [{"role": "user", "content": user}]})
    r.raise_for_status()
    data = r.json()
    return "".join(b.get("text", "") for b in data.get("content", []))


def _call_gemini(model, key, system, user, base_url=None):
    base = (base_url or "https://generativelanguage.googleapis.com").rstrip("/")
    url = f"{base}/v1beta/models/{model}:generateContent?key={key}"
    r = requests.post(url, timeout=DEFAULT_TIMEOUT,
        headers={"content-type": "application/json"},
        json={"systemInstruction": {"parts": [{"text": system}]},
              "contents": [{"role": "user", "parts": [{"text": user}]}],
              "generationConfig": {"temperature": 0.2, "maxOutputTokens": MAX_OUTPUT_TOKENS}})
    r.raise_for_status()
    data = r.json()
    cands = data.get("candidates", [])
    if not cands:
        fb = (data.get("promptFeedback") or {}).get("blockReason")
        raise RuntimeError(f"Gemini không trả về nội dung"
                           + (f" (bị chặn: {fb})." if fb else " (có thể bị chặn an toàn)."))
    parts = cands[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts)
    fr = cands[0].get("finishReason")
    if not text:
        # model 2.5 'thinking' có thể tiêu hết token đầu ra mà chưa kịp xuất text
        raise RuntimeError(
            f"Gemini không trả về văn bản (finishReason={fr}). Thử lại, đổi sang model "
            "không-thinking (vd gemini-2.0-flash-001) hoặc model 'flash' nhẹ hơn.")
    return text


def _call_openai(model, key, system, user, base_url=None):
    base = (base_url or "https://api.openai.com/v1").rstrip("/")
    url = base + "/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "content-type": "application/json",
               # Header thân thiện với OpenRouter (OpenAI bỏ qua nếu không cần):
               "HTTP-Referer": "https://texo.local", "X-Title": "TEXO Contract Checker"}
    r = requests.post(url, timeout=DEFAULT_TIMEOUT, headers=headers,
        json={"model": model, "temperature": 0.2,
              "messages": [{"role": "system", "content": system},
                           {"role": "user", "content": user}]})
    r.raise_for_status()
    data = r.json()
    if "choices" not in data:
        raise RuntimeError(f"Phản hồi không hợp lệ từ endpoint: {str(data)[:200]}")
    return data["choices"][0]["message"]["content"]


def call_llm(provider, model, key, system, user, base_url=None):
    if provider == "anthropic":
        return _call_anthropic(model, key, system, user, base_url)
    if provider == "gemini":
        return _call_gemini(model, key, system, user, base_url)
    if provider == "openai":
        return _call_openai(model, key, system, user, base_url)
    if provider == "openai_compat":
        if not base_url or not base_url.strip():
            raise ValueError(
                "Loại 'API tương thích OpenAI' BẮT BUỘC điền Base URL "
                "(vd OpenRouter: https://openrouter.ai/api/v1). "
                "Để trống sẽ bị gọi nhầm sang OpenAI và báo lỗi key.")
        return _call_openai(model, key, system, user, base_url)
    raise ValueError(f"Nhà cung cấp không hỗ trợ: {provider}")


# --------------------------------------------------------------------------- #
# Parse JSON từ phản hồi (chịu lỗi)
# --------------------------------------------------------------------------- #
def _balance_json(s):
    """Vá JSON bị CẮT CỤT: đóng chuỗi/ngoặc còn mở, bỏ phần tử dở ở cuối.
    Dùng khi model trả về vượt giới hạn token nên thiếu dấu đóng."""
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
    if in_str:                       # chuỗi bị cắt giữa chừng -> đóng lại
        res += '"'
    res = res.rstrip()
    while res and res[-1] in ",:":   # bỏ dấu phẩy/hai chấm thừa ở cuối
        res = res[:-1].rstrip()
    for ch in reversed(stack):       # đóng các ngoặc còn mở
        res += "}" if ch == "{" else "]"
    return res


def _extract_json(text):
    text = text.strip()
    # bỏ rào ```json ... ```
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    # tìm khối {...} lớn nhất
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            pass
    # vá JSON bị cắt cụt (vượt giới hạn token)
    try:
        return json.loads(_balance_json(text))
    except Exception:
        pass
    return None


def _http_hint(code, provider):
    """Gợi ý khắc phục theo mã lỗi HTTP."""
    c = str(code)
    if c == "401" or c == "403":
        return ("Key sai hoặc không có quyền. Với 'API tương thích OpenAI' (OpenRouter…) "
                "nhớ điền đúng Base URL — nếu để trống sẽ gọi nhầm OpenAI và báo key sai.")
    if c == "429":
        if provider == "gemini":
            return ("Hết hạn mức (quota) phía Google. Thử model 'gemini-2.0-flash-lite' hoặc "
                    "'gemini-1.5-flash', chờ quota reset, hoặc bật billing.")
        return "Hết hạn mức / quá nhiều request. Chờ một lúc, đổi model rẻ hơn, hoặc kiểm tra billing."
    if c == "404":
        return "Sai tên model hoặc sai Base URL. Kiểm tra lại tên model endpoint của bạn hỗ trợ."
    return ""


def list_models(provider, key, base_url=None):
    """Hỏi nhà cung cấp danh sách model mà key này dùng được.
    Trả về (ok, [model...] | thông_báo_lỗi)."""
    try:
        if provider == "gemini":
            base = (base_url or "https://generativelanguage.googleapis.com").rstrip("/")
            r = requests.get(f"{base}/v1beta/models?key={key}&pageSize=200", timeout=30)
            r.raise_for_status()
            out = []
            for m in r.json().get("models", []):
                if "generateContent" in (m.get("supportedGenerationMethods") or []):
                    out.append(m.get("name", "").split("/", 1)[-1])
            return True, sorted(set(x for x in out if x))
        if provider == "anthropic":
            base = (base_url or "https://api.anthropic.com").rstrip("/")
            r = requests.get(f"{base}/v1/models?limit=100", timeout=30,
                             headers={"x-api-key": key, "anthropic-version": "2023-06-01"})
            r.raise_for_status()
            return True, [m.get("id") for m in r.json().get("data", []) if m.get("id")]
        # openai / openai_compat
        if provider == "openai_compat" and (not base_url or not base_url.strip()):
            return False, "Cần điền Base URL trước khi lấy danh sách model."
        base = (base_url or "https://api.openai.com/v1").rstrip("/")
        r = requests.get(f"{base}/models", timeout=30,
                             headers={"Authorization": f"Bearer {key}"})
        r.raise_for_status()
        return True, sorted(m.get("id") for m in r.json().get("data", []) if m.get("id"))
    except requests.HTTPError as e:
        code = e.response.status_code if e.response is not None else "?"
        return False, f"HTTP {code}: {_http_hint(code, provider)}".strip()
    except Exception as e:
        return False, str(e)[:200]


def test_connection(provider, model, key, base_url=None):
    """Gọi thử ngắn để kiểm tra key/model. Trả về (ok, message)."""
    try:
        out = call_llm(provider, model, key,
                       "Bạn là trợ lý. Trả lời đúng một từ.",
                       "Trả lời chính xác: OK", base_url)
        return True, (out or "").strip()[:60] or "OK"
    except requests.HTTPError as e:
        code = e.response.status_code if e.response is not None else "?"
        detail = ""
        try:
            detail = e.response.text[:160]
        except Exception:
            pass
        hint = _http_hint(code, provider)
        return False, f"HTTP {code}: {detail}" + (f"\n👉 {hint}" if hint else "")
    except Exception as e:
        return False, str(e)[:240]


def analyze_with_ai(result, contract_text, provider, model, key, base_url=None):
    """Gọi LLM tạo báo cáo đầy đủ. Trả về dict:
       {ok, provider, model, data (parsed) | raw, error}."""
    user = build_user_prompt(result, contract_text)
    try:
        raw = call_llm(provider, model, key, SKILL_SYSTEM, user, base_url)
    except requests.HTTPError as e:
        code = e.response.status_code if e.response is not None else "?"
        try:
            detail = e.response.text[:300]
        except Exception:
            detail = ""
        hint = _http_hint(code, provider)
        return {"ok": False, "error": f"Lỗi API (HTTP {code}): {detail}"
                + (f"\n👉 {hint}" if hint else "")}
    except Exception as e:
        return {"ok": False, "error": f"Lỗi gọi AI: {e}"}

    parsed = _extract_json(raw)
    if not parsed:
        return {"ok": False, "error": "AI trả về không phải JSON hợp lệ.", "raw": raw[:4000]}
    # backward-compat: field cũ -> field mới
    if "tom_tat_dieu_hanh" in parsed and "tong_quan_chung" not in parsed:
        parsed["tong_quan_chung"] = parsed["tom_tat_dieu_hanh"]
    # thêm chu_de vào mỗi entry dieu_khoan nếu AI trả về dạng cũ (không có chu_de)
    for i, item in enumerate(parsed.get("dieu_khoan") or [], start=1):
        if "chu_de" not in item:
            item["chu_de"] = str(i)
    # nếu phải vá (raw không kết thúc bằng '}') -> phản hồi có thể bị cắt cụt
    truncated = not raw.strip().rstrip("`").rstrip().endswith("}")
    return {"ok": True, "provider": provider, "model": model,
            "data": parsed, "truncated": truncated}
