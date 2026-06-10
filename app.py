# -*- coding: utf-8 -*-
"""
TEXO — Rà soát pháp lý Hợp đồng TVGS (phiên bản web, rule-based, KHÔNG dùng AI).

Chạy:  streamlit run app.py
Bảo mật: nhập mật khẩu (mặc định 'texo2026', có thể đổi qua st.secrets hoặc biến môi trường).
"""
import os
import streamlit as st

from engine import analyze
from report import build_report
from knowledge import DO, CAM, XANH, LEVEL_LABEL, LEVEL_COLOR

st.set_page_config(page_title="TEXO – Rà soát Hợp đồng tư vấn xây dựng",
                   page_icon="📑", layout="wide")


# --------------------------------------------------------------------------- #
# CỔNG MẬT KHẨU (lớp bảo mật cơ bản)
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
# HIỂN THỊ KẾT QUẢ
# --------------------------------------------------------------------------- #
def flag(level):
    return f":red[●] " if level == DO else (":orange[●] " if level == CAM else ":green[●] ")


def render_result(res):
    ctx = res["context"]
    s = res["summary"]

    # Thẻ tổng quan
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rủi ro CAO", s[DO])
    c2.metric("Rủi ro TRUNG BÌNH", s[CAM])
    c3.metric("Chủ đề THIẾU", s["missing"])
    c4.metric("Đề mục/Điều", res["meta"]["n_headings"])

    # Vai trò tư vấn
    roles = res.get("roles") or {}
    if roles.get("primary_meta"):
        pm = roles["primary_meta"]
        with st.expander(f"🧩 Vai trò tư vấn: **{pm['name']}**", expanded=True):
            if roles["multi_role"]:
                others = ", ".join(m["name"] for m in roles["present_meta"]
                                   if m["id"] != pm["id"])
                st.warning(f"Hợp đồng có thể GỘP NHIỀU vai trò (cũng thấy: {others}). "
                           f"→ Tách phạm vi & căn cứ pháp lý từng phần.")
            st.markdown(f"**Phạm vi chuẩn:** {pm['scope']}")
            st.markdown(f"**Căn cứ pháp lý:** {pm['basis']}")
            if pm.get("independence"):
                st.info(f"**Yêu cầu độc lập:** {pm['independence']}")
            st.markdown(f"**Lưu ý rà soát:** {pm['review']}")
            for note in roles.get("cross_role_flags", []):
                st.error(f"⚠️ Vượt vai trò: {note}")
    else:
        st.info("Chưa nhận diện rõ vai trò tư vấn — nên xác định thủ công (TVGS / QLDA / "
                "thẩm tra / kiểm định / khảo sát / thiết kế).")

    with st.expander("ℹ️ Bối cảnh hợp đồng", expanded=True):
        st.write(f"**Kiểu kết cấu:** {ctx['kieu_ket_cau']}")
        langs = ", ".join(ctx["content_languages"]) or "vi"
        st.write(f"**Ngôn ngữ:** {langs}" + (" (song ngữ)" if ctx["song_ngu"] else ""))
        st.write(f"**Nguồn vốn (đoán):** {ctx['nguon_von']}")
        st.write(f"**Trần phạt áp dụng:** {ctx['tran_phat']}")
        st.write(f"**Mẫu TT 02/2023:** {ctx['ghi_chu_tt02']}")
        if ctx["co_dieu_kien_chung_rieng"]:
            st.warning("Có Điều kiện chung + riêng → phải đọc CẢ hai; phần riêng đè phần chung.")
        if ctx["co_thu_tu_uu_tien"]:
            st.info("Có điều khoản thứ tự ưu tiên hồ sơ → kiểm tra ai được ưu tiên.")

    # Bảng rủi ro
    st.subheader("🚩 Rủi ro phát hiện")
    findings = res["findings"]
    if not findings:
        st.success("Không phát hiện mẫu câu rủi ro điển hình. Vẫn nên rà soát thủ công.")
    for f in findings:
        color = LEVEL_COLOR[f["level"]]
        with st.expander(f"{flag(f['level'])} **[{LEVEL_LABEL[f['level']]}]** "
                         f"(Chủ đề {f['topic']}) {f['label']}"):
            st.markdown(f"**Vấn đề:** {f['problem']}")
            st.markdown(f"> _Trích trong hợp đồng:_ “{f['quote']}”")
            st.markdown(f"**Căn cứ:** {f['basis']}")
            st.markdown(f"**Đề xuất đàm phán:** {f['suggest']}")

    # Độ phủ
    st.subheader("📋 Độ phủ 21 chủ đề chuẩn")
    cov = res["coverage"]
    missing = [c for c in cov if not c["present"]]
    colA, colB = st.columns([1, 1])
    with colA:
        st.markdown("**Chủ đề CÓ trong hợp đồng:**")
        for c in cov:
            if c["present"]:
                st.markdown(f":green[✔] {c['id']}. {c['name']}")
    with colB:
        st.markdown("**Chủ đề THIẾU (cũng là rủi ro):**")
        if not missing:
            st.markdown("_Không thiếu chủ đề nào._")
        for c in missing:
            st.markdown(f"{flag(c['missing_risk'])} {c['id']}. {c['name']}")
            st.caption(c["missing_note"])

    # Cảnh báo thuật ngữ tiếng Anh
    if res["en_warnings"]:
        st.subheader("🔤 Thuật ngữ tiếng Anh cần lưu ý")
        for w in res["en_warnings"]:
            st.markdown(f"- **{w['term']}** — {w['note']}")

    # Comment trong file
    if res["comments"]:
        with st.expander(f"💬 {len(res['comments'])} ghi chú (comment) có sẵn trong file"):
            for c in res["comments"]:
                st.markdown(f"- **[{c['author']} – {c['date']}]** {c['text']}")


# --------------------------------------------------------------------------- #
# MAIN
# --------------------------------------------------------------------------- #
def main():
    st.title("📑 Rà soát pháp lý Hợp đồng tư vấn xây dựng — TEXO")
    st.caption("Công cụ sàng lọc rủi ro hợp đồng theo góc nhìn ĐƠN VỊ TƯ VẤN (Bên B) — "
               "TVGS, QLDA, thẩm tra, kiểm định, khảo sát, thiết kế. "
               "Hoạt động bằng quy tắc (rule-based), **không dùng AI**.")

    if not check_password():
        st.stop()

    with st.sidebar:
        st.header("Hướng dẫn")
        st.markdown(
            "1. Tải lên hợp đồng **.docx** hoặc **.pdf** (PDF phải có chữ, không phải ảnh scan).\n"
            "2. Xem bảng rủi ro & độ phủ chủ đề.\n"
            "3. Tải **báo cáo Word** để đàm phán.\n\n"
            "**Lưu ý:** đây là bước sàng lọc đầu, không thay thế luật sư."
        )
        st.divider()
        st.markdown("**Chú thích mức rủi ro**")
        st.markdown(":red[●] Cao  ·  :orange[●] Trung bình  ·  :green[●] Ổn/Có lợi")
        if st.button("Đăng xuất"):
            st.session_state.clear()
            st.rerun()

    up = st.file_uploader("Tải hợp đồng (.docx hoặc .pdf)", type=["docx", "pdf"])
    if not up:
        st.info("Hãy tải lên một file hợp đồng để bắt đầu rà soát.")
        return

    with st.spinner("Đang rà soát hợp đồng…"):
        try:
            res = analyze(up.getvalue(), up.name)
        except Exception as e:
            st.error(f"Lỗi khi đọc/phân tích file: {e}")
            return

    render_result(res)

    st.divider()
    try:
        docx_bytes = build_report(res)
        st.download_button(
            "⬇️ Tải báo cáo Word (.docx)",
            data=docx_bytes,
            file_name=f"BaoCao_RaSoat_{os.path.splitext(up.name)[0]}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            type="primary",
        )
    except Exception as e:
        st.error(f"Không tạo được báo cáo Word: {e}")


if __name__ == "__main__":
    main()
