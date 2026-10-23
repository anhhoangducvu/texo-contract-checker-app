# -*- coding: utf-8 -*-
"""
TEXO — Rà soát pháp lý Hợp đồng tư vấn xây dựng (phiên bản web).

Hai chế độ:
  • KHÔNG AI (mặc định): quét tự động theo quy tắc — miễn phí, riêng tư, chạy cục bộ.
  • CÓ AI ("bộ não"): người dùng tự dán API key (Claude/Gemini/OpenAI/tương thích OpenAI)
    để có báo cáo ĐẦY ĐỦ đúng tinh thần skill. AI bổ sung trên nền phân tích tự động.

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
import ui

APP_VERSION = "2.1"
TITLE = "Rà soát Hợp đồng tư vấn xây dựng"
ui.setup("TEXO · " + TITLE, "📑")

SECRETS_PATH = Path(__file__).with_name(".texo_secrets.json")


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
    """Thanh bên 'Trợ lý AI (tùy chọn)' – cùng bố cục với bộ app Phòng Kỹ thuật."""
    saved = load_secrets()
    sb = st.sidebar
    sb.markdown("### 🤖 Trợ lý AI (tùy chọn)")
    ids = list(llm.PROVIDERS.keys())
    last = saved.get("last_provider") if saved.get("keys", {}).get(saved.get("last_provider")) else None
    pid = sb.selectbox("Nhà cung cấp", ["(Không dùng AI)"] + ids,
                       index=(ids.index(last) + 1) if last in ids else 0,
                       format_func=lambda k: llm.PROVIDERS[k]["label"] if k in llm.PROVIDERS else k)
    if pid == "(Không dùng AI)":
        sb.caption("Đang chạy bằng bộ quy tắc – miễn phí, dữ liệu không rời máy. Báo cáo rút gọn.")
        return {"enabled": False}
    prov = llm.PROVIDERS[pid]

    api_key = sb.text_input("API key", value=saved.get("keys", {}).get(pid, ""), type="password")
    base_url = ""
    if prov["needs_base_url"]:
        base_url = sb.text_input("Base URL", value=saved.get("base_urls", {}).get(pid, ""),
                                 placeholder="https://openrouter.ai/api/v1",
                                 help="Bắt buộc cho loại tương thích OpenAI. OpenRouter: https://openrouter.ai/api/v1 "
                                      "– tên model dạng 'nhà_cung_cấp/model', vd 'openai/gpt-4o'.")
    if sb.button("Lấy danh sách model", disabled=not api_key or (prov["needs_base_url"] and not base_url.strip())):
        with sb:
            with st.spinner("Đang lấy danh sách model…"):
                ok, res = llm.list_models(pid, api_key, base_url or None)
        if ok and res:
            st.session_state[f"models_{pid}"] = res
        elif ok:
            sb.warning("Key hợp lệ nhưng không có model nào dùng được.")
        else:
            sb.error(f"Lỗi lấy model: {res}")

    fetched = st.session_state.get(f"models_{pid}")
    model = ""
    if fetched:
        saved_model = saved.get("models", {}).get(pid)
        prefer = ["flash-latest", "2.5-flash", "gpt-4o", "sonnet", "flash", "pro"]
        idx = 0
        if saved_model in fetched:
            idx = fetched.index(saved_model)
        else:
            for kw in prefer:
                hit = next((i for i, m in enumerate(fetched) if kw in m.lower()), None)
                if hit is not None:
                    idx = hit
                    break
        model = sb.selectbox("Model", fetched, index=idx)
        if sb.button("Kiểm tra kết nối"):
            with sb:
                with st.spinner("Đang gọi thử…"):
                    ok, msg = llm.test_connection(pid, model, api_key, base_url or None)
            (sb.success if ok else sb.error)(("Kết nối được: " if ok else "") + msg)
    sb.caption(prov.get("key_hint", ""))

    luu = sb.checkbox("Lưu key trên máy này", value=bool(saved.get("keys", {}).get(pid)))
    if luu and api_key:
        new = (api_key, model or saved.get("models", {}).get(pid, ""), base_url)
        old = (saved.get("keys", {}).get(pid), saved.get("models", {}).get(pid, ""), saved.get("base_urls", {}).get(pid, ""))
        if new != old or saved.get("last_provider") != pid:
            saved.setdefault("keys", {})[pid] = api_key
            saved.setdefault("models", {})[pid] = new[1]
            saved.setdefault("base_urls", {})[pid] = base_url
            saved["last_provider"] = pid
            save_secrets(saved)
    elif not luu and saved.get("keys", {}).get(pid):
        saved["keys"].pop(pid, None)
        if saved["keys"]:
            save_secrets(saved)
        else:
            forget_secrets()
    sb.caption("⚠️ Bật AI thì **toàn văn hợp đồng** được gửi tới nhà cung cấp đã chọn. Chỉ lưu key trên máy "
               "cá nhân, không dùng chung máy đã lưu key, không lưu trên Streamlit Cloud. Lộ key do cách sử dụng "
               "không phải lỗi phần mềm.")
    if not (api_key and model):
        sb.info("Nhập key và chọn model để bật AI.")
    return {"enabled": True, "provider": pid, "model": model, "base_url": base_url or None, "api_key": api_key}


# --------------------------------------------------------------------------- #
# HIỂN THỊ KẾT QUẢ RULE-BASED
# --------------------------------------------------------------------------- #
def flag(level):
    return ":red[●] " if level == DO else (":orange[●] " if level == CAM else ":green[●] ")


def render_rule_based(res):
    ctx = res["context"]; s = res["summary"]
    k = st.columns(4)
    ui.kpi(k[0], s[DO], "Rủi ro cao", "cần đàm phán sửa", "red" if s[DO] else "green")
    ui.kpi(k[1], s[CAM], "Rủi ro trung bình", "nên làm rõ", "orange" if s[CAM] else "green")
    ui.kpi(k[2], s["missing"], "Chủ đề còn thiếu", "so với khung chuẩn", "orange" if s["missing"] else "green")
    ui.kpi(k[3], res["meta"]["n_headings"], "Đề mục / Điều", "đã nhận diện", "blue")
    if s[DO]:
        ui.callout(f"🔴 Có <b>{s[DO]}</b> điểm rủi ro cao cho bên tư vấn – xem mục <i>Rủi ro phát hiện</i> và đưa vào "
                   "danh sách phải đạt khi đàm phán.", "red")
    elif s[CAM] or s["missing"]:
        ui.callout("🟠 Không có rủi ro cao; còn điểm cần làm rõ hoặc chủ đề chưa có trong hợp đồng.", "orange")
    else:
        ui.callout("🟢 Quét tự động không thấy rủi ro điển hình. Vẫn nên đọc lại các điều khoản thanh toán, phạt, "
                   "trách nhiệm.", "green")

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

    st.markdown("##### 🚩 Rủi ro phát hiện (quét tự động)")
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
        st.markdown("##### 📋 Chủ đề chuẩn còn thiếu")
        for c in missing:
            st.markdown(f"{flag(c['missing_risk'])} {c['id']}. {c['name']}")
            st.caption(c["missing_note"])


# --------------------------------------------------------------------------- #
# HIỂN THỊ KẾT QUẢ AI
# --------------------------------------------------------------------------- #
def render_ai(data, provider, model):
    st.success(f"Báo cáo đầy đủ do AI lập — {provider} / {model}")

    # ---- Thông tin hợp đồng ----
    hd = data.get("thong_tin_hop_dong") or {}
    if hd:
        st.markdown("#### 📋 Thông tin hợp đồng")
        labels = [
            ("ten_du_an",    "Tên dự án / Công trình"),
            ("ten_cdt",      "Chủ đầu tư (Bên A)"),
            ("ten_tu_van",   "Đơn vị tư vấn (Bên B)"),
            ("so_hop_dong",  "Số hiệu hợp đồng"),
            ("goi_thau",     "Gói thầu"),
            ("gia_hop_dong", "Giá trị hợp đồng"),
            ("thoi_han",     "Thời hạn thực hiện"),
            ("loai_hop_dong","Loại hợp đồng"),
        ]
        rows_hd = {lbl: hd.get(k, "—") for k, lbl in labels if hd.get(k)}
        if rows_hd:
            import pandas as pd
            df = pd.DataFrame(list(rows_hd.items()), columns=["Trường", "Giá trị"])
            st.dataframe(df, use_container_width=True, hide_index=True)
        st.divider()

    if data.get("vai_tro"):
        st.markdown(f"**Vai trò tư vấn:** {data['vai_tro']}")
    if data.get("nguon_von"):
        st.markdown(f"**Nguồn vốn & trần phạt:** {data['nguon_von']}")
    tqc = data.get("tong_quan_chung") or data.get("tom_tat_dieu_hanh")
    if tqc:
        st.markdown("**Tổng quan chung:**")
        st.info(tqc)

    rows = data.get("dieu_khoan") or []
    if rows:
        st.markdown(f"**Phân tích chi tiết ({len(rows)} chủ đề):**")
        for it in rows:
            lvl = str(it.get("muc_do", "CAM")).upper()
            dot = ":red[●]" if "Đ" in lvl or "DO" in lvl or "CAO" in lvl else (
                ":green[●]" if "XANH" in lvl else ":orange[●]")
            chu_de = it.get("chu_de", "")
            ref = it.get("ref", "(điều khoản)")
            title = f"{dot} **Chủ đề {chu_de}** — {ref} — {lvl}" if chu_de else f"{dot} {ref} — {lvl}"
            with st.expander(title):
                st.markdown(f"**Vấn đề & căn cứ:** {it.get('van_de','')}")
                st.markdown(f"**Đề xuất:** {it.get('de_xuat','')}")

    if data.get("dieu_khoan_co_loi"):
        st.markdown("**✅ Điều khoản có lợi cần bảo vệ:**")
        for x in data["dieu_khoan_co_loi"]:
            st.markdown(f"- {x}")
    if data.get("thieu_sot"):
        st.markdown("**⚠️ Nội dung còn thiếu:**")
        for x in data["thieu_sot"]:
            st.markdown(f"- {x}")
    pri = data.get("uu_tien_dam_phan") or {}
    if pri:
        st.markdown("**🎯 Ưu tiên đàm phán:**")
        for k, t in [("phai_dat", "🔴 Phải đạt"), ("nen_dat", "🟠 Nên đạt"), ("don_dep", "🟢 Dọn dẹp")]:
            for x in (pri.get(k) or []):
                st.markdown(f"- {t}: {x}")


# --------------------------------------------------------------------------- #
# MAIN
# --------------------------------------------------------------------------- #
def main():
    ui.gate("Rà soát Hợp đồng tư vấn")
    ui.header(TITLE, "Phòng Kỹ thuật · Góc nhìn đơn vị tư vấn (Bên B): TVGS, QLDA, thẩm tra, kiểm định, khảo sát, thiết kế")

    ai_cfg = sidebar_ai_config()
    ai_ready = ai_cfg["enabled"] and ai_cfg.get("api_key") and ai_cfg.get("model")
    with st.sidebar:
        st.divider()
        if ai_ready:
            ui.badge(f"AI sẵn sàng – {ai_cfg['model']}", "green")
        elif ai_cfg["enabled"]:
            ui.badge("Chưa đủ cấu hình AI → chạy bằng quy tắc", "orange")
        else:
            ui.badge("Chế độ quy tắc (không AI)", "grey")
        st.markdown("**Mức rủi ro:** :red[●] Cao · :orange[●] Trung bình · :green[●] Ổn/Có lợi")
        ui.logout_button()
        st.caption("⚖️ Rà soát văn bản pháp luật, tiêu chuẩn viện dẫn bằng TEXO Legal Reviewer trước khi trình ký.")
        st.caption(f"Rà soát hợp đồng v{APP_VERSION} · Xây dựng: Hoàng Đức Vũ")

    with st.expander("📘 Hướng dẫn sử dụng"):
        st.markdown("""
1. **Tải hợp đồng** `.docx` hoặc `.pdf` (có lớp chữ) vào ô bên dưới – app quét ngay bằng bộ quy tắc.
2. Xem **ô tổng hợp**, vai trò tư vấn, các **rủi ro phát hiện** (có trích dẫn, căn cứ, đề xuất) và **chủ đề còn thiếu**.
3. Bấm **Tải báo cáo rút gọn** để lấy file Word.
4. **(Tuỳ chọn) Trợ lý AI** ở thanh bên: chọn nhà cung cấp → dán API key → *Lấy danh sách model* → *Kiểm tra kết nối*,
   rồi bấm **Tạo báo cáo đầy đủ bằng AI** (20–60 giây).

Kết quả chỉ hỗ trợ rà soát – người rà soát vẫn đọc lại hợp đồng và chịu trách nhiệm về ý kiến cuối cùng.
""")
    st.markdown("##### 📥 Tải hợp đồng cần rà soát")
    up = st.file_uploader("Chọn hoặc kéo thả file hợp đồng (.docx, .pdf)", type=["docx", "pdf"])
    if not up:
        return

    data_bytes = up.getvalue()
    with st.spinner("Đang rà soát tự động…"):
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
            st.download_button("⬇️ Tải báo cáo rút gọn (tự động, .docx)",
                data=build_report(res),
                file_name=f"BaoCao_RutGon_{os.path.splitext(up.name)[0]}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True)
    except Exception as e:
        st.error(f"Không tạo được báo cáo rút gọn: {e}")

    # Luồng AI
    if ai_ready:
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
                st.markdown("#### 🧠 Báo cáo đầy đủ (AI)")
                if ai.get("truncated"):
                    st.warning("Phản hồi AI dài và có thể bị cắt cụt — báo cáo đã được vá để "
                               "đọc được nhưng có thể thiếu phần cuối. Thử model có giới hạn "
                               "đầu ra lớn hơn (vd gemini-2.5-pro) hoặc rà soát hợp đồng ngắn hơn.")
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
