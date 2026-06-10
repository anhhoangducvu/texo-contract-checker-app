# -*- coding: utf-8 -*-
"""Kiểm thử cú pháp/logic các hàm MỚI trong llm.py (bản chép verbatim, không mạng)."""
import requests


def _http_hint(code, provider):
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


if __name__ == "__main__":
    assert _http_hint("404", "gemini").startswith("Sai tên model")
    assert _http_hint("429", "gemini").startswith("Hết hạn mức (quota)")
    ok, res = list_models("openai_compat", "k", None)
    assert ok is False and "Base URL" in res
    ok2, res2 = list_models("openai_compat", "k", "   ")
    assert ok2 is False
    print("NEW FUNCS SYNTAX+LOGIC OK |", _http_hint("404", "x") or "(none)")
