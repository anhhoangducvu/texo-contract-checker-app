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
        "models_note": "VD: gemini-2.0-flash, gemini-1.5-pro, gemini-2.5-pro",
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

NGUYÊN TẮC CỐT LÕI:
1. Luôn đứng về phía Bên B: tìm mọi điều khoản đẩy rủi ro/chi phí/trách nhiệm sang Bên B.
2. Rà theo CHỦ ĐỀ RỦI RO, không theo số điều. Quét đủ 21 chủ đề chuẩn (dưới đây). Chủ đề
   THIẾU cũng là rủi ro.
3. Xác định NGUỒN VỐN: vốn công/PPP → trần phạt 12% (Luật Xây dựng), mẫu TT 02/2023/TT-BXD
   BẮT BUỘC; tư nhân/FDI → trần phạt 8% (Luật Thương mại), TT02 là đòn bẩy đàm phán.
4. Xác định đúng VAI TRÒ tư vấn và đối chiếu phạm vi chuẩn; cảnh báo nếu hợp đồng gán việc
   của vai trò KHÁC (scope creep) vì đòi năng lực/chứng chỉ khác và tăng trách nhiệm.
5. Soi tính ĐỐI XỨNG (mỗi chế tài áp lên Bên B thì CĐT có chế tài tương ứng không).
6. Soi TRẦN trách nhiệm & loại thiệt hại: có trần cho phạt VÀ bồi thường không? Có loại trừ
   thiệt hại gián tiếp không? 'Hoàn trả toàn bộ tiền đã thanh toán' là cờ đỏ.
7. Phạt tính trên GIÁ TRỊ PHẦN NGHĨA VỤ BỊ VI PHẠM, không phải tổng hợp đồng.

PHẠM VI THEO VAI TRÒ (đối chiếu):
- TVGS: Điều 19 NĐ 06/2021 (kiểm tra – xem xét & chấp thuận – đề nghị – yêu cầu – nghiệm
  thu). KHÔNG thẩm tra thiết kế (Điều 104 NĐ 175/2024), KHÔNG phê duyệt biện pháp thi công
  (nhà thầu lập, CĐT duyệt), KHÔNG lập hồ sơ nghiệm thu/hoàn công. Năng lực: Điều 107 NĐ175.
- QLDA: phạm vi rộng (tiến độ, chi phí, đấu thầu, hợp đồng, thiết kế, bàn giao); thường thay
  mặt CĐT trong giới hạn ủy quyền — cần rõ ranh giới, phê duyệt cuối vẫn của CĐT.
- Thẩm tra thiết kế: K6 Đ71 / Điều 87a Luật XD + NĐ 175/2024 (Mẫu 02/09 PL I); kiểm tính
  kết cấu độc lập. Phải ĐỘC LẬP với nhà thầu thiết kế; không gánh trách nhiệm người thiết kế.
- Thẩm tra dự toán: cần năng lực ĐỊNH GIÁ xây dựng (Điều 84 NĐ 175/2024).
- Kiểm định: Điều 5 NĐ 06/2021; tổ chức GIÁM SÁT không được kiểm định công trình do mình
  giám sát (Điều 19.7.b NĐ 06/2021).

21 CHỦ ĐỀ RỦI RO CHUẨN: 1) Định nghĩa & diễn giải; 2) Hồ sơ HĐ & thứ tự ưu tiên (+ quyền
giải thích); 3) Phạm vi (Điều 19 NĐ06; 'bao gồm không giới hạn'); 4) Chất lượng/tiêu chuẩn;
5) Thời gian/tiến độ/tạm ngừng; 6) Giá, loại HĐ & điều chỉnh giá; 7) Tạm ứng/thu hồi/giữ
lại; 8) Thanh toán & quyết toán (thời hạn, lãi chậm trả); 9) Bảo lãnh; 10) Bảo hiểm; 11)
Nghĩa vụ Bên B (sau thanh lý, báo cáo); 12) Nghĩa vụ & chế tài CĐT (đối xứng); 13) Nhân
lực; 14) Bản quyền/SHTT; 15) Bảo mật; 16) Phạt (trần, phần vi phạm) & bồi thường (trần,
loại trừ gián tiếp); 17) Liêm chính/chống hối lộ; 18) Tạm ngừng & chấm dứt (đối xứng, quyền
chấm dứt của Bên B, thanh toán khi chấm dứt); 19) Bất khả kháng; 20) Chuyển nhượng; 21)
Luật áp dụng, tranh chấp, ngôn ngữ. Bổ sung khi gặp: 23) PDPA (NĐ 13/2023); 24) Thuế GTGT;
25) Điều khoản kiểu thông luật (indemnify/hold harmless, novation, best endeavours, chuyển
toàn bộ bản quyền, ngôn ngữ ưu tiên nước ngoài).

CĂN CỨ PHÁP LÝ THƯỜNG DÙNG: Luật Xây dựng 2014 (sửa 2020), NĐ 06/2021/NĐ-CP (Điều 19, 13,
14), NĐ 175/2024/NĐ-CP (Điều 104, 107, 84, 87a; thay NĐ 15/2021), TT 02/2023/TT-BXD (Phụ
lục II), Bộ luật Dân sự 2015, Luật Thương mại 2005 (Điều 301 trần phạt 8%), NĐ 13/2023.

YÊU CẦU ĐẦU RA: chỉ trả về DUY NHẤT một JSON hợp lệ (không kèm giải thích, không ```), theo
schema:
{
  "vai_tro": "nhận định vai trò tư vấn của hợp đồng (kèm cảnh báo scope creep nếu có)",
  "nguon_von": "vốn công/PPP hay tư nhân/FDI và trần phạt áp dụng",
  "tom_tat_dieu_hanh": "3-6 câu tóm tắt rủi ro trọng yếu",
  "dieu_khoan": [
    {"ref":"Điều/Điểm thực tế","muc_do":"ĐỎ|CAM|XANH",
     "van_de":"vấn đề & rủi ro cho Bên B, KÈM căn cứ pháp lý cụ thể và đối chiếu mẫu TT02",
     "de_xuat":"đề xuất đàm phán/sửa đổi cụ thể"}
  ],
  "dieu_khoan_co_loi": ["các điều khoản CÓ LỢI cho Bên B cần bảo vệ"],
  "thieu_sot": ["nội dung còn THIẾU so với mẫu chuẩn cần đề nghị bổ sung"],
  "uu_tien_dam_phan": {"phai_dat":["..."], "nen_dat":["..."], "don_dep":["..."]}
}
Phân tích kỹ, nêu căn cứ pháp lý chính xác, bằng tiếng Việt. Liệt kê ĐẦY ĐỦ các điều khoản
rủi ro, không bỏ sót. Mức độ: ĐỎ = rủi ro cao, CAM = trung bình, XANH = ổn/có lợi."""


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
        lines.append("- Cờ rủi ro rule-based đã phát hiện:")
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
            "Hãy trả về DUY NHẤT JSON theo schema đã nêu.")


# --------------------------------------------------------------------------- #
# Gọi API từng nhà cung cấp
# --------------------------------------------------------------------------- #
def _call_anthropic(model, key, system, user, base_url=None):
    url = (base_url or "https://api.anthropic.com").rstrip("/") + "/v1/messages"
    r = requests.post(url, timeout=DEFAULT_TIMEOUT,
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": model, "max_tokens": 8000, "system": system,
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
              "generationConfig": {"temperature": 0.2, "maxOutputTokens": 8192}})
    r.raise_for_status()
    data = r.json()
    cands = data.get("candidates", [])
    if not cands:
        raise RuntimeError("Gemini không trả về nội dung (có thể bị chặn an toàn).")
    parts = cands[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts)


def _call_openai(model, key, system, user, base_url=None):
    base = (base_url or "https://api.openai.com/v1").rstrip("/")
    url = base + "/chat/completions"
    r = requests.post(url, timeout=DEFAULT_TIMEOUT,
        headers={"Authorization": f"Bearer {key}", "content-type": "application/json"},
        json={"model": model, "temperature": 0.2,
              "messages": [{"role": "system", "content": system},
                           {"role": "user", "content": user}]})
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]


def call_llm(provider, model, key, system, user, base_url=None):
    if provider == "anthropic":
        return _call_anthropic(model, key, system, user, base_url)
    if provider == "gemini":
        return _call_gemini(model, key, system, user, base_url)
    if provider in ("openai", "openai_compat"):
        return _call_openai(model, key, system, user, base_url)
    raise ValueError(f"Nhà cung cấp không hỗ trợ: {provider}")


# --------------------------------------------------------------------------- #
# Parse JSON từ phản hồi (chịu lỗi)
# --------------------------------------------------------------------------- #
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
    return None


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
            detail = e.response.text[:200]
        except Exception:
            pass
        return False, f"HTTP {code}: {detail}"
    except Exception as e:
        return False, str(e)[:200]


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
        return {"ok": False, "error": f"Lỗi API (HTTP {code}): {detail}"}
    except Exception as e:
        return {"ok": False, "error": f"Lỗi gọi AI: {e}"}

    parsed = _extract_json(raw)
    if not parsed:
        return {"ok": False, "error": "AI trả về không phải JSON hợp lệ.", "raw": raw[:4000]}
    return {"ok": True, "provider": provider, "model": model, "data": parsed}
