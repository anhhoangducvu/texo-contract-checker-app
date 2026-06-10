# -*- coding: utf-8 -*-
"""
TEXO — Rà soát pháp lý Hợp đồng tư vấn xây dựng (phiên bản web).

Hai chế độ:
  • KHÔNG AI (mặc định): quét rule-based — miễn phí, riêng tư, chạy cục bộ.
  • CÓ AI ("bộ não"): người dùng tự dán API key (Claude/Gemini/OpenAI/tương thích OpenAI)
    để có báo cáo ĐẦY ĐỦ đúng tinh thần skill. AI bổ sung trên nền rule-based.

Bảo mật: cổng mật khẩu (mặc định 'texo2026'). Khi bật AI, toàn văn hợp đồng được gửi tới
nhà cung cấp đã chọn — người dùng tự chịu trách nhiệm về key & dữ liệu.
"""
import os
import json
from pathlib import Path

import streamlit as st

from engine import analyze, extract
from report import build_report, build_ai_report
from knowledge import DO, CAM, XANH, LEVEL_LABEL, LEVEL_COLOR
import llm

st.set_page_config(page_title="TEXO – Rà soát Hợp đồng tư vấn xây dựng",
                   page_icon="📑", layout="wide")

SECRETS_PATH = Path(__file__).with_name(".texo_secrets.json")


# --------------------------------------------------------------------------- #
# CỔNG MẬT KHẨU
# --------------------------------------------------------------------------- #
def get_password():
    try:
        if "APP_PASSWORD" in st.secrets:
            return str(st.secrets["APP_PASSWORD"])
    except Exception:
        pass
    return os.environ.get("APP_PASSWORD", "texo2026")


def check_password():
    if st.session_state.get("auth_ok"):
        return True
    st.markdown("### 🔒 Đăng nhập")
    st.caption("Công cụ nội bộ TEXO — vui lòng nhập mật khẩu để tiếp tục.")
    pw = st.text_input("Mật khẩu", type="password", key="pw_input")
    if st.button("Vào", type="primary"):
        if pw == get_password():
            st.session_state["auth_ok"] = True
            st.rerun()
        else:
            st.error("Mật khẩu không đúng.")
    return False


# --------------------------------------------------------------------------- #
# LƯU / NẠP API KEY TẠI MÁY (tùy chọn)
# --------------------------------------------------------------------------- #
def load_secrets():
    try:
        if SECRETS_PATH.exists():
            return json.loads(SECRETS_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"keys": {}, "models": {}, "base_urls": {}, "last_provider": "anthropic"}


def save_secrets(d):
    try:
        SECRETS_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        st.sidebar.error(f"Không lưu được key: {e}")
        return False


def forget_secrets():
    try:
        if SECRETS_PATH.exists():
            SECRETS_PATH.unlink()
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# SIDEBAR — CẤU HÌNH AI
# --------------------------------------------------------------------------- #
def sidebar_ai_config():
    saved = load_secrets()
    st.sidebar.header("🧠 Bộ não AI (tùy chọn)")
    enable = st.sidebar.checkbox(
        "Bật phân tích bằng AI", value=False,
        help="Tắt = chỉ dùng rule-based (miễn phí, cục bộ). Bật = cần API key của bạn.")

    cfg = {"enabled": enable}
    if not enable:
        st.sidebar.caption("Đang ở chế độ **KHÔNG AI** — báo cáo rút gọn, chạy hoàn toàn cục bộ.")
        return cfg

    ids = list(llm.PROVIDERS.keys())
    labels = [llm.PROVIDERS[i]["label"] for i in ids]
    last = saved.get("last_provider", "anthropic")
    idx = ids.index(last) if last in ids else 0
    pid = ids[st.sidebar.selectbox("Nhà cung cấp", range(len(ids)),
                                   format_func=lambda i: labels[i], index=idx)]
    prov = llm.PROVIDERS[pid]

    model = st.sidebar.text_input(
        "Model", value=saved.get("models", {}).get(pid, prov["default_model"]),
        help=prov["models_note"])
    base_url = ""
    if prov["needs_base_url"]:
        base_url = st.sidebar.text_input(
            "Base URL (BẮT BUỘC)", value=saved.get("base_urls", {}).get(pid, ""),
            placeholder="https://openrouter.ai/api/v1",
            help="Bắt buộc cho loại tương thích OpenAI. OpenRouter: https://openrouter.ai/api/v1 "
                 "— và đặt tên model dạng 'nhà_cung_cấp/model', vd 'openai/gpt-4o' hoặc "
                 "'anthropic/claude-3.5-sonnet'.")
        if not base_url.strip():
            st.sidebar.error("⚠️ Chưa điền Base URL → sẽ bị gọi nhầm sang OpenAI và báo lỗi key. "
                             "OpenRouter dùng: https://openrouter.ai/api/v1")
    api_key = st.sidebar.text_input(
        "API key", value=saved.get("keys", {}).get(pid, ""), type="password",
        help=prov["key_hint"])

    # Lấy danh sách model thực tế mà key này dùng được (tránh đoán sai tên model)
    if st.sidebar.button("🔄 Lấy danh sách model", use_container_width=True):
        if not api_key:
            st.sidebar.warning("Nhập API key trước đã.")
        elif prov["needs_base_url"] and not (base_url or "").strip():
            st.sidebar.warning("Điền Base URL trước đã.")
        else:
            with st.sidebar:
                with st.spinner("Đang hỏi danh sách model…"):
                    ok, res = llm.list_models(pid, api_key, base_url or None)
            if ok and res:
                st.session_state[f"models_{pid}"] = res
                st.sidebar.success(f"Tìm thấy {len(res)} model.")
            elif ok:
                st.sidebar.info("Key hợp lệ nhưng không có model nào dùng được.")
            else:
                st.sidebar.error(f"Lỗi lấy model: {res}")
    fetched = st.session_state.get(f"models_{pid}")
    if fetched:
        pick = st.sidebar.selectbox(
            "Model có sẵn (chọn để dùng)", ["(giữ ô Model ở trên)"] + fetched, index=0)
        if pick != "(giữ ô Model ở trên)":
            model = pick
            st.sidebar.caption(f"Đang dùng model: **{model}**")

    remember = st.sidebar.checkbox("Ghi nhớ key tại máy này", value=bool(saved.get("keys", {}).get(pid)))

    col1, col2 = st.sidebar.columns(2)
    if col1.button("💾 Lưu", use_container_width=True):
        if remember:
            saved.setdefault("keys", {})[pid] = api_key
            saved.setdefault("models", {})[pid] = model
            saved.setdefault("base_urls", {})[pid] = base_url
            saved["last_provider"] = pid
            if save_secrets(saved):
                st.sidebar.success("Đã lưu key tại máy.")
        else:
            # bỏ ghi nhớ provider này
            saved.get("keys", {}).pop(pid, None)
            save_secrets(saved)
            st.sidebar.info("Đã bỏ ghi nhớ key của nhà cung cấp này.")
    if col2.button("🧪 Kiểm tra", use_container_width=True):
        if not api_key:
            st.sidebar.warning("Chưa nhập key.")
        else:
            with st.sidebar:
                with st.spinner("Đang kiểm tra kết nối…"):
                    ok, msg = llm.test_connection(pid, model, api_key, base_url or None)
            (st.sidebar.success if ok else st.sidebar.error)(
                f"{'OK' if ok else 'Lỗi'}: {msg}")
    if st.sidebar.button("🗑️ Xoá key đã lưu tại máy", use_container_width=True):
        forget_secrets()
        st.sidebar.info("Đã xoá file key tại máy.")

    # CẢNH BÁO BẢO MẬT (theo yêu cầu)
    st.sidebar.warning(
        "⚠️ **Lưu ý về API key & bảo mật**\n\n"
        "- Khi bật AI, **toàn văn hợp đồng** sẽ được gửi tới nhà cung cấp bạn chọn để xử lý.\n"
        "- Tùy chọn *ghi nhớ key tại máy* lưu key vào tệp `.texo_secrets.json` ngay trên máy "
        "chạy app (tiện nhưng kém an toàn hơn). Chúng tôi đã cân nhắc kỹ và để **bạn tự chọn**.\n"
        "- **Khuyến nghị:** chỉ ghi nhớ key trên **máy cá nhân của bạn**; KHÔNG để người khác "
        "dùng chung tài khoản/máy đã lưu key; không deploy công khai kèm key.\n"
        "- Việc lộ key (nếu có) là do cách sử dụng của người dùng, **không phải lỗi phần mềm "
        "hay người phát triển**. Hãy bảo quản key như mật khẩu.")

    cfg.update({"provider": pid, "model": model, "base_url": base_url or None, "api_key": api_key})
    return cfg


# --------------------------------------------------------------------------- #
# HIỂN THỊ KẾT QUẢ RULE-BASED
# --------------------------------------------------------------------------- #
def flag(level):
    return ":red[●] " if level == DO else (":orange[●] " if level == CAM else ":green[●] ")


def render_rule_based(res):
    ctx = res["context"]; s = res["summary"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rủi ro CAO", s[DO]); c2.metric("Rủi ro TRUNG BÌNH", s[CAM])
    c3.metric("Chủ đề THIẾU", s["missing"]); c4.metric("Đề mục/Điều", res["meta"]["n_headings"])

    roles = res.get("roles") or {}
    if roles.get("primary_meta"):
        pm = roles["primary_meta"]
        with st.expander(f"🧩 Vai trò tư vấn: **{pm['name']}**", expanded=True):
            if roles["multi_role"]:
                others = ", ".join(m["name"] for m in roles["present_meta"] if m["id"] != pm["id"])
                st.warning(f"Có thể GỘP NHIỀU vai trò (cũng thấy: {others}) → tách phạm vi & căn cứ.")
            st.markdown(f"**Phạm vi chuẩn:** {pm['scope']}")
            st.markdown(f"**Căn cứ pháp lý:** {pm['basis']}")
            if pm.get("independence"):
                st.info(f"**Yêu cầu độc lập:** {pm['independence']}")
            st.markdown(f"**Lưu ý rà soát:** {pm['review']}")
            for note in roles.get("cross_role_flags", []):
                st.error(f"⚠️ Vượt vai trò: {note}")

    with st.expander("ℹ️ Bối cảnh hợp đồng", expanded=False):
        st.write(f"**Kiểu kết cấu:** {ctx['kieu_ket_cau']}")
        langs = ", ".join(ctx["content_languages"]) or "vi"
        st.write(f"**Ngôn ngữ:** {langs}" + (" (song ngữ)" if ctx["song_ngu"] else ""))
        st.write(f"**Nguồn vốn (đoán):** {ctx['nguon_von']}")
        st.write(f"**Trần phạt:** {ctx['tran_phat']}")
        st.write(f"**Mẫu TT 02/2023:** {ctx['ghi_chu_tt02']}")

    st.subheader("🚩 Rủi ro phát hiện (rule-based)")
    if not res["findings"]:
        st.success("Không phát hiện mẫu câu rủi ro điển hình. Vẫn nên rà soát thủ công.")
    for f in res["findings"]:
        with st.expander(f"{flag(f['level'])} **[{LEVEL_LABEL[f['level']]}]** "
                         f"(Chủ đề {f['topic']}) {f['label']}"):
            st.markdown(f"**Vấn đề:** {f['problem']}")
            st.markdown(f"> _Trích:_ “{f['quote']}”")
            st.markdown(f"**Căn cứ:** {f['basis']}")
            st.markdown(f"**Đề xuất:** {f['suggest']}")

    missing = [c for c in res["coverage"] if not c["present"]]
    if missing:
        st.subheader("📋 Chủ đề chuẩn còn THIẾU")
        for c in missing:
            st.markdown(f"{flag(c['missing_risk'])} {c['id']}. {c['name']}")
            st.caption(c["missing_note"])


# --------------------------------------------------------------------------- #
# HIỂN THỊ KẾT QUẢ AI
# --------------------------------------------------------------------------- #
def render_ai(data, provider, model):
    st.success(f"Báo cáo đầy đủ do AI lập — {provider} / {model}")
    if data.get("vai_tro"):
        st.markdown(f"**Vai trò tư vấn:** {data['vai_tro']}")
    if data.get("nguon_von"):
        st.markdown(f"**Nguồn vốn & trần phạt:** {data['nguon_von']}")
    if data.get("tom_tat_dieu_hanh"):
        st.markdown("**Tóm tắt điều hành:**")
        st.info(data["tom_tat_dieu_hanh"])

    rows = data.get("dieu_khoan") or []
    if rows:
        st.markdown(f"**Phân tích chi tiết ({len(rows)} điều khoản):**")
        for it in rows:
            lvl = str(it.get("muc_do", "CAM")).upper()
            dot = ":red[●]" if "Đ" in lvl or "DO" in lvl or "CAO" in lvl else (
                ":green[●]" if "XANH" in lvl else ":orange[●]")
            with st.expander(f"{dot} {it.get('ref','(điều khoản)')} — {lvl}"):
                st.markdown(f"**Vấn đề & căn cứ:** {it.get('van_de','')}")
                st.markdown(f"**Đề xuất:** {it.get('de_xuat','')}")

    if data.get("dieu_khoan_co_loi"):
        st.markdown("**Điều khoản có lợi cần bảo vệ:**")
        for x in data["dieu_khoan_co_loi"]:
            st.markdown(f"- {x}")
    if data.get("thieu_sot"):
        st.markdown("**Nội dung còn thiếu:**")
        for x in data["thieu_sot"]:
            st.markdown(f"- {x}")
    pri = data.get("uu_tien_dam_phan") or {}
    if pri:
        st.markdown("**Ưu tiên đàm phán:**")
        for k, t in [("phai_dat", "🔴 Phải đạt"), ("nen_dat", "🟠 Nên đạt"), ("don_dep", "🟢 Dọn dẹp")]:
            for x in (pri.get(k) or []):
                st.markdown(f"- {t}: {x}")


# --------------------------------------------------------------------------- #
# MAIN
# --------------------------------------------------------------------------- #
def main():
    st.title("📑 Rà soát pháp lý Hợp đồng tư vấn xây dựng — TEXO")
    st.caption("Góc nhìn ĐƠN VỊ TƯ VẤN (Bên B): TVGS, QLDA, thẩm tra, kiểm định, khảo sát, thiết kế.")

    if not check_password():
        st.stop()

    ai_cfg = sidebar_ai_config()
    with st.sidebar:
        st.divider()
        st.markdown("**Chú thích mức rủi ro:** :red[●] Cao · :orange[●] Trung bình · :green[●] Ổn/Có lợi")
        if st.button("Đăng xuất"):
            st.session_state.clear(); st.rerun()

    if ai_cfg["enabled"] and ai_cfg.get("api_key"):
        st.success("🧠 Chế độ **CÓ AI** đang bật — sẽ có nút tạo báo cáo đầy đủ sau khi rà soát.")
    elif ai_cfg["enabled"]:
        st.warning("Bạn đã bật AI nhưng **chưa nhập API key**. Hãy nhập key ở thanh bên, hoặc tắt AI để dùng bản rule-based.")
    else:
        st.info("Chế độ **KHÔNG AI** — báo cáo rút gọn, chạy cục bộ. Bật AI ở thanh bên nếu có API key.")

    up = st.file_uploader("Tải hợp đồng (.docx hoặc .pdf)", type=["docx", "pdf"])
    if not up:
        return

    data_bytes = up.getvalue()
    with st.spinner("Đang rà soát (rule-based)…"):
        try:
            res = analyze(data_bytes, up.name)
        except Exception as e:
            st.error(f"Lỗi khi đọc/phân tích file: {e}")
            return

    render_rule_based(res)

    st.divider()
    cols = st.columns(2)
    # Tải báo cáo rule-based
    try:
        with cols[0]:
            st.download_button("⬇️ Tải báo cáo rút gọn (rule-based, .docx)",
                data=build_report(res),
                file_name=f"BaoCao_RutGon_{os.path.splitext(up.name)[0]}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True)
    except Exception as e:
        st.error(f"Không tạo được báo cáo rút gọn: {e}")

    # Luồng AI
    if ai_cfg["enabled"] and ai_cfg.get("api_key"):
        with cols[1]:
            run_ai = st.button("🧠 Tạo báo cáo ĐẦY ĐỦ bằng AI", type="primary",
                               use_container_width=True)
        if run_ai:
            paras, _ = extract(data_bytes, up.name)
            full_text = "\n".join(paras)
            with st.spinner("AI đang phân tích hợp đồng… (có thể mất 20–60 giây)"):
                ai = llm.analyze_with_ai(res, full_text, ai_cfg["provider"],
                                         ai_cfg["model"], ai_cfg["api_key"], ai_cfg["base_url"])
            st.session_state["ai_result"] = ai
            st.session_state["ai_for_file"] = up.name

        ai = st.session_state.get("ai_result")
        if ai and st.session_state.get("ai_for_file") == up.name:
            st.divider()
            if not ai.get("ok"):
                st.error(f"AI lỗi: {ai.get('error')}")
                if ai.get("raw"):
                    with st.expander("Phản hồi thô từ AI"):
                        st.code(ai["raw"])
            else:
                st.subheader("🧠 Báo cáo đầy đủ (AI)")
                render_ai(ai["data"], ai["provider"], ai["model"])
                try:
                    st.download_button("⬇️ Tải báo cáo ĐẦY ĐỦ (AI, .docx)",
                        data=build_ai_report(res, ai),
                        file_name=f"BaoCao_DayDu_AI_{os.path.splitext(up.name)[0]}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        type="primary")
                except Exception as e:
                    st.error(f"Không tạo được báo cáo AI: {e}")


if __name__ == "__main__":
    main()
