# TEXO — Rà soát pháp lý Hợp đồng TVGS (Web app, rule-based)

Công cụ web sàng lọc rủi ro hợp đồng tư vấn giám sát (TVGS) theo góc nhìn **Bên B**.
Chuyển từ skill `texo-hopdong-checker` sang dạng **Streamlit** để phổ cập cho nhiều người,
có **một lớp bảo mật bằng mật khẩu**, và **không cần đấu nối API AI**.

> ⚠️ **Khác biệt so với bản dùng AI:** bản này chạy bằng **quy tắc (rule-based)** — dò
> mẫu câu/từ khóa bất lợi và kiểm tra độ phủ 21 chủ đề chuẩn. Nó nhanh, miễn phí, riêng tư,
> nhưng **không suy luận ngữ cảnh** như AI: có thể bỏ sót cách diễn đạt lạ hoặc báo nhầm khi
> câu chữ trùng từ khóa. Hãy coi đây là **bước sàng lọc đầu tiên**, không thay thế luật sư.

---

## 1. Công cụ làm được gì (không cần AI)

- Đọc hợp đồng **.docx** và **.pdf** (PDF phải có chữ — không phải ảnh scan).
- **Đoán bối cảnh:** nguồn vốn (công/PPP vs tư nhân/FDI → trần phạt 12% hay 8%), ngôn ngữ,
  song ngữ, kiểu kết cấu (dân luật VN / common-law), có điều kiện chung-riêng / thứ tự ưu tiên.
- **Phát hiện ~30 loại điều khoản bất lợi** (cờ đỏ/cam): phạt trên tổng giá trị HĐ, bồi thường
  không trần, hoàn trả toàn bộ tiền, chấm dứt vì thuận tiện, indemnify/hold harmless,
  best endeavours, ngôn ngữ nước ngoài ưu tiên, chuyển toàn bộ bản quyền… kèm **căn cứ pháp lý**
  (Điều 19 NĐ 06/2021, NĐ 175/2024, Luật Xây dựng, Luật Thương mại, mẫu TT 02/2023/TT-BXD…)
  và **đề xuất đàm phán**.
- **Kiểm tra độ phủ 21 chủ đề chuẩn** — chủ đề THIẾU cũng được cảnh báo (vd thiếu chế tài
  với CĐT, thiếu điều khoản thanh toán/giải quyết tranh chấp).
- **Xuất báo cáo Word A4** (Times New Roman, bảng màu theo mức rủi ro) để mang đi đàm phán.
- Đọc cả **comment** có sẵn trong file .docx.

Toàn bộ tri thức nằm trong `knowledge.py` — bạn có thể **bổ sung quy tắc** dễ dàng (xem mục 5).

---

## 2. Cấu trúc dự án

```
texo-contract-checker-app/
├── app.py              # Giao diện Streamlit + cổng mật khẩu
├── engine.py           # Trích xuất + nhận diện kết cấu + quét rủi ro + độ phủ
├── knowledge.py        # Bộ quy tắc rủi ro & 21 chủ đề (CHỈNH Ở ĐÂY để nâng chất lượng)
├── report.py           # Sinh báo cáo Word A4
├── requirements.txt
├── .gitignore
└── .streamlit/
    ├── config.toml
    └── secrets.toml.example   # mẫu khai mật khẩu
```

---

## 3. Chạy thử trên máy (local)

Cần Python 3.9+.

```bash
cd texo-contract-checker-app
pip install -r requirements.txt
streamlit run app.py
```

Mở trình duyệt tại địa chỉ Streamlit in ra (mặc định http://localhost:8501).
Mật khẩu mặc định: **`texo2026`**.

---

## 4. Đưa lên web

### Cách A — Streamlit Community Cloud (miễn phí, khuyên dùng để phổ cập)

1. Tạo một repo **GitHub** (có thể để private) và đẩy toàn bộ thư mục này lên.
   **KHÔNG** đẩy file `.streamlit/secrets.toml` thật (đã có trong `.gitignore`).
2. Vào https://share.streamlit.io → **New app** → chọn repo, branch, file `app.py`.
3. Mục **Advanced settings → Secrets**, dán:
   ```toml
   APP_PASSWORD = "texo2026"
   ```
   (Đổi sang mật khẩu của bạn nếu muốn.)
4. **Deploy.** Sau ~1–2 phút bạn có một URL công khai để gửi cho mọi người.

### Cách B — Tự host bằng Docker (server/VPS công ty)

Tạo `Dockerfile` (mẫu):
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV APP_PASSWORD=texo2026
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```
```bash
docker build -t texo-checker .
docker run -p 8501:8501 -e APP_PASSWORD="matkhau_moi" texo-checker
```
Khuyến nghị đặt sau reverse proxy (Nginx) có HTTPS.

### Đổi mật khẩu
Theo thứ tự ưu tiên: `st.secrets["APP_PASSWORD"]` → biến môi trường `APP_PASSWORD` →
mặc định `texo2026`. Đổi ở Secrets (Cloud) hoặc biến môi trường (Docker) là an toàn nhất —
không nên sửa cứng trong code.

> 🔐 **Về mức bảo mật:** đây là lớp mật khẩu **cơ bản** (một mật khẩu chung). Phù hợp để chặn
> người ngoài, nhưng không phải hệ thống tài khoản riêng từng người. Nếu cần phân quyền theo
> người dùng hoặc nhật ký truy cập, cần nâng cấp thêm (xem mục 6).

---

## 5. Nâng chất lượng mà KHÔNG cần AI

Chất lượng phụ thuộc vào **độ giàu của bộ quy tắc** trong `knowledge.py`. Cách mở rộng:

- **Thêm cờ rủi ro:** thêm một mục vào `RISK_RULES` với `pattern` (regex EN+VI), `level`,
  `problem`, `basis`, `suggest`. Mỗi mẫu câu bất lợi mới bạn gặp ngoài thực tế → thêm 1 rule.
- **Thêm/đổi từ khóa độ phủ:** sửa `keywords` của từng mục trong `TOPICS` để bắt đúng cách
  diễn đạt của các CĐT khác nhau.
- **Mẹo viết regex:** dùng `|` để liệt kê nhiều cách diễn đạt; `.{0,40}` để cho phép vài chữ
  xen giữa; viết cả tiếng Việt lẫn tiếng Anh trong một mẫu.

Càng nhiều mẫu thực tế được nạp vào, công cụ càng "giống chuyên gia". Đây là cách tiệm cận
chất lượng cao nhất khi không dùng AI.

---

## 6. Hướng nâng cấp về sau (tùy chọn)

- **Phân quyền người dùng:** dùng `streamlit-authenticator` (nhiều tài khoản, mật khẩu băm).
- **OCR cho PDF scan:** thêm `pytesseract` + `pdf2image` để đọc hợp đồng dạng ảnh.
- **Kết hợp AI (khi sẵn sàng):** giữ nguyên engine rule-based làm lớp sàng lọc, chỉ gọi AI để
  diễn giải sâu các điều khoản đã được đánh dấu → tiết kiệm chi phí, vẫn nâng chất lượng.

---

## 7. Lưu ý pháp lý

Báo cáo là rà soát **nội bộ hỗ trợ đàm phán**, **không thay thế ý kiến luật sư chính thức**.
Mọi phát hiện cần người có chuyên môn kiểm chứng trên bản hợp đồng gốc trước khi ký.
