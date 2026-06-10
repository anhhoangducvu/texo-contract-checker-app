# -*- coding: utf-8 -*-
"""
Knowledge base RULE-BASED cho rà soát Hợp đồng {TV} (góc nhìn Bên B).

Toàn bộ tri thức pháp lý được mã hóa tĩnh ở đây — KHÔNG dùng AI. Gồm 2 phần:

  RISK_RULES  — danh sách "cờ đỏ/cam": mỗi rule là một mẫu (regex) câu chữ bất lợi,
                kèm mức rủi ro, mô tả vấn đề, căn cứ pháp lý, đề xuất đàm phán.
  TOPICS      — 21 chủ đề rủi ro chuẩn: dùng để kiểm tra ĐỘ PHỦ (hợp đồng có nhắc
                tới chủ đề đó không). Thiếu chủ đề = cũng là rủi ro cần cảnh báo.

Nguồn: checklist/tieu_chi_chung.md + reference/mau_TT02_2023.md của skill
texo-hopdong-checker (TEXO). Đối chiếu: TT 02/2023/TT-BXD (Phụ lục II), Điều 19
NĐ 06/2021, NĐ 175/2024, Luật Xây dựng, Luật Thương mại, BLDS, NĐ 13/2023.
"""

# Mức rủi ro
DO = "ĐỎ"      # cao
CAM = "CAM"    # trung bình
XANH = "XANH"  # ổn / có lợi (cần bảo vệ)

LEVEL_LABEL = {DO: "Cao", CAM: "Trung bình", XANH: "Ổn / Có lợi"}
LEVEL_COLOR = {DO: "#C00000", CAM: "#C45911", XANH: "#2E7D32"}
LEVEL_ORDER = {DO: 0, CAM: 1, XANH: 2}


# =============================================================================
# RISK_RULES — phát hiện câu chữ bất lợi cho {TV} bằng mẫu (regex, không phân biệt hoa thường)
# Mỗi rule:
#   id        : mã ngắn
#   topic     : số chủ đề liên quan (1..25)
#   level     : DO / CAM
#   label     : tên ngắn của rủi ro (hiển thị)
#   pattern   : regex (str) — tìm trong toàn văn hợp đồng (EN + VI)
#   problem   : vì sao bất lợi cho {TV}
#   basis     : căn cứ pháp lý / đối chiếu mẫu TT02
#   suggest   : đề xuất đàm phán / sửa đổi
# =============================================================================
RISK_RULES = [
    # --- Chủ đề 2: Hồ sơ HĐ & thứ tự ưu tiên ---
    {
        "id": "interp_final",
        "topic": 2, "level": DO,
        "label": "CĐT giữ 'quyền giải thích cuối cùng'",
        "pattern": r"quyền giải thích (cuối cùng|sau cùng|chung thẩm)|final (right of )?interpretation|interpretation shall be (final|binding)",
        "problem": "Khi hồ sơ mâu thuẫn/không rõ, CĐT tự quyết nghĩa là vừa đá bóng vừa thổi còi, ép cách hiểu bất lợi cho {TV}.",
        "basis": "Nguyên tắc bình đẳng trong hợp đồng (BLDS 2015, Điều 3); mẫu TT02 không trao quyền giải thích tuyệt đối cho một bên.",
        "suggest": "Bất đồng giải thích thì thương lượng; không thống nhất thì đưa ra trọng tài/tòa án. Bỏ 'quyền giải thích cuối cùng' của một bên.",
    },
    # --- Chủ đề 3: Phạm vi (Điều 19 NĐ06) ---
    {
        "id": "scope_design_review",
        "topic": 3, "level": DO,
        "skip_roles": ["THAM_TRA_TK", "THAM_TRA_DT", "THIET_KE"],
        "label": "Gán {TV} 'thẩm tra / tối ưu hóa thiết kế'",
        "pattern": r"thẩm tra thiết kế|tối ưu (hóa|hoá) thiết kế|design (review|verification|optimi[sz]ation)|kiểm định thiết kế",
        "problem": "Thẩm tra thiết kế là năng lực RIÊNG, không thuộc phạm vi giám sát thi công; gán cho {TV} làm phình trách nhiệm vượt năng lực/giấy phép.",
        "basis": "Điều 104 NĐ 175/2024 (năng lực thẩm tra thiết kế) tách biệt với Điều 107 (giám sát); Điều 19 NĐ 06/2021 giới hạn phạm vi giám sát.",
        "suggest": "Sửa thành 'rà soát, phát hiện bất cập, báo cáo CĐT'; nếu cần thẩm tra phải tách hợp đồng/phụ lục và điều chỉnh phí.",
    },
    {
        "id": "scope_approve_method",
        "topic": 3, "level": DO,
        "label": "Gán {TV} 'phê duyệt' biện pháp/hồ sơ nhà thầu",
        "pattern": r"(tư vấn giám sát|tvgs|bên b).{0,40}phê duyệt|phê duyệt biện pháp (thi công|tổ chức)|approve.{0,30}(method statement|construction method)",
        "problem": "Giám sát chỉ 'kiểm tra, có ý kiến chấp thuận'; phê duyệt biện pháp thi công là việc của CĐT. Gán phê duyệt = nhận trách nhiệm thay CĐT.",
        "basis": "Điều 19.1.b/c NĐ 06/2021: {TV} kiểm tra và chấp thuận; biện pháp do nhà thầu lập, CĐT phê duyệt.",
        "suggest": "Sửa thành 'kiểm tra, xem xét và có ý kiến/chấp thuận'; quyền phê duyệt thuộc CĐT.",
    },
    {
        "id": "scope_open_ended",
        "topic": 3, "level": CAM,
        "label": "Phạm vi 'bao gồm nhưng không giới hạn'",
        "pattern": r"bao gồm nhưng không giới hạn|bao gồm và không giới hạn|including but not limited|without limitation",
        "problem": "Cụm này mở phạm vi vô hạn, cho phép CĐT yêu cầu thêm việc ngoài dự kiến mà không tăng phí.",
        "basis": "Điều 19 NĐ 06/2021 (phạm vi giám sát có giới hạn); mẫu TT02 gắn phạm vi với phụ lục công việc cụ thể.",
        "suggest": "Giới hạn phạm vi theo Phụ lục công việc; việc ngoài phạm vi phải lập phụ lục và điều chỉnh phí.",
    },
    {
        "id": "scope_acceptance_dossier",
        "topic": 3, "level": CAM,
        "label": "Gán {TV} 'lập/thu thập hồ sơ nghiệm thu, hoàn công'",
        "pattern": r"(lập|thu thập|sắp xếp|hoàn thiện).{0,30}hồ sơ (nghiệm thu|hoàn công|hoàn thành)|(tvgs|bên b).{0,30}hồ sơ hoàn công",
        "problem": "Lập hồ sơ nghiệm thu/hoàn công là việc của nhà thầu và CĐT; {TV} chỉ kiểm tra và ký xác nhận.",
        "basis": "Điều 13.17 (nhà thầu) và Điều 14.11 (CĐT) NĐ 06/2021; {TV} tham gia nghiệm thu, ký xác nhận.",
        "suggest": "Sửa: {TV} 'kiểm tra, tham gia nghiệm thu, ký xác nhận'; việc lập hồ sơ thuộc nhà thầu/CĐT.",
    },
    # --- Chủ đề 16: Phạt & bồi thường ---
    {
        "id": "penalty_total_value",
        "topic": 16, "level": DO,
        "label": "Phạt % tính trên TỔNG giá trị hợp đồng",
        "pattern": r"phạt.{0,40}(tổng giá trị hợp đồng|giá trị hợp đồng)|penalty.{0,30}total contract|(8|10|12)\s*%.{0,20}(tổng )?giá trị hợp đồng",
        "problem": "Phạt phải tính trên phần nghĩa vụ bị vi phạm, không phải tổng HĐ. Tính trên tổng HĐ làm mức phạt phình to bất hợp lý.",
        "basis": "Điều 146 Luật Xây dựng / Điều 301 Luật Thương mại: phạt trên giá trị phần nghĩa vụ bị vi phạm; trần 8% (Luật TM, ngoài vốn NN) / 12% (Luật XD, vốn NN).",
        "suggest": "Sửa: phạt tính trên 'giá trị phần nghĩa vụ bị vi phạm'; ấn định trần tổng phạt ≤ 8% (hoặc 12%).",
    },
    {
        "id": "penalty_no_cap",
        "topic": 16, "level": DO,
        "label": "Bồi thường 'toàn bộ thiệt hại' không có trần",
        "pattern": r"bồi thường (toàn bộ|mọi|tất cả).{0,40}thiệt hại|toàn bộ chi phí khắc phục|all (losses|damages|costs)|bồi thường.{0,20}gián tiếp",
        "problem": "Bồi thường 'toàn bộ thiệt hại trực tiếp VÀ gián tiếp' không trần = trách nhiệm vô hạn. Trần phạt thường KHÔNG tự động áp cho bồi thường.",
        "basis": "BLDS 2015 Điều 360, 419; thông lệ tư vấn quốc tế có liability cap. Mẫu TT02 cân bằng trách nhiệm.",
        "suggest": "Thêm trần TỔNG trách nhiệm (gồm bồi thường, tối đa = giá trị HĐ); loại trừ thiệt hại gián tiếp/mất lợi nhuận; gắn với mức bảo hiểm.",
    },
    {
        "id": "refund_all",
        "topic": 16, "level": DO,
        "label": "Buộc 'hoàn trả toàn bộ tiền đã thanh toán'",
        "pattern": r"hoàn (trả|lại) toàn bộ (số tiền|tiền|phí)|refund (of )?all|repay all (amounts|sums)",
        "problem": "Khi chấm dứt do lỗi/sự cố, buộc hoàn trả toàn bộ tiền đã nhận là phạt chồng phạt, phủ nhận phần dịch vụ đã thực hiện.",
        "basis": "BLDS 2015: chỉ hoàn phần chưa thực hiện; thiệt hại phải có chứng minh. Phạt vượt trần có thể vô hiệu.",
        "suggest": "Bỏ điều khoản hoàn trả toàn bộ; chỉ hoàn phần chưa thực hiện và bồi thường tương ứng phần lỗi có chứng minh.",
    },
    {
        "id": "joint_several",
        "topic": 16, "level": DO,
        "label": "Liên đới bồi thường cùng nhà thầu / gồm thiệt hại uy tín",
        "pattern": r"liên đới (bồi thường|chịu trách nhiệm)|joint and several|thiệt hại (về )?(uy tín|thương hiệu|danh tiếng)|reputational (loss|damage)",
        "problem": "Trách nhiệm liên đới buộc {TV} gánh cả phần lỗi của nhà thầu; khoản 'thiệt hại uy tín' rất khó định lượng và dễ bị thổi phồng.",
        "basis": "BLDS 2015 Điều 587 (mỗi bên chịu phần lỗi của mình); thiệt hại phải xác định được.",
        "suggest": "Chỉ chịu phần lỗi của {TV}; loại bỏ hoặc định lượng cụ thể khoản thiệt hại uy tín/thương hiệu.",
    },
    # --- Chủ đề 18: Tạm ngừng & chấm dứt ---
    {
        "id": "term_convenience",
        "topic": 18, "level": DO,
        "label": "CĐT chấm dứt 'vì thuận tiện / không cần lý do'",
        "pattern": r"chấm dứt.{0,40}(bất kỳ (thời điểm|lúc)|không cần (nêu )?lý do|theo nhu cầu|thuận tiện)|terminat\w*.{0,30}(for convenience|without (giving )?(any )?reason|at any time)",
        "problem": "Cho phép CĐT đơn phương chấm dứt tùy ý. Nếu không kèm nghĩa vụ thanh toán phần đã làm + chi phí huy động thì {TV} chịu thiệt.",
        "basis": "Mẫu TT02 và thông lệ: chấm dứt vì thuận tiện phải thanh toán phần đã thực hiện + chi phí không hủy được + đền bù hợp lý.",
        "suggest": "Bổ sung: khi CĐT chấm dứt vì thuận tiện phải thanh toán phần đã làm, chi phí huy động/giải thể và một khoản đền bù.",
    },
    {
        "id": "term_no_b_right",
        "topic": 18, "level": CAM,
        "label": "Thiếu quyền chấm dứt của {TV}",
        "pattern": r"(bên b|tư vấn|consultant).{0,40}(không được|no right to) (đơn phương )?chấm dứt|terminat",
        "problem": "Nếu chỉ CĐT có quyền chấm dứt, {TV} không có lối thoát khi CĐT chậm thanh toán hoặc vi phạm nghiêm trọng.",
        "basis": "Đối xứng quyền (mẫu TT02); BLDS 2015 Điều 428 (đơn phương chấm dứt khi bên kia vi phạm nghiêm trọng).",
        "suggest": "Bổ sung quyền {TV} chấm dứt khi CĐT chậm thanh toán/vi phạm trọng yếu, kèm quyền được thanh toán phần đã làm.",
    },
    # --- Chủ đề 8: Thanh toán ---
    {
        "id": "pay_refuse",
        "topic": 8, "level": DO,
        "label": "Thiếu hồ sơ thì CĐT 'từ chối thanh toán'",
        "pattern": r"từ chối thanh toán|from? chối thanh toán|refuse (to )?pay|withhold (the )?payment|không thanh toán nếu",
        "problem": "Cho CĐT quyền từ chối (mất quyền) thanh toán cả khoản chỉ vì thiếu một phần hồ sơ — giam tiền của {TV}.",
        "basis": "Mẫu TT02: chỉ tạm hoãn phần liên quan; phần còn lại trả đúng hạn. BLDS nguyên tắc thiện chí.",
        "suggest": "Sửa 'từ chối' → 'tạm hoãn phần liên quan đến khi bổ sung'; phần không tranh chấp vẫn trả đúng hạn.",
    },
    {
        "id": "pay_no_interest",
        "topic": 8, "level": CAM,
        "label": "Thiếu lãi chậm thanh toán cho {TV}",
        "pattern": r"lãi (chậm|do chậm) (thanh toán|trả)|interest on late payment|default interest|lãi suất quá hạn",
        "problem": "(Phát hiện khi CÓ nhắc) — cần kiểm tra lãi chậm thanh toán có ĐỐI XỨNG cho {TV} không, hay chỉ áp một chiều.",
        "basis": "Mẫu TT02 buộc CĐT chậm thanh toán phải trả lãi quá hạn; BLDS Điều 357.",
        "suggest": "Bảo đảm có lãi chậm thanh toán áp cho CĐT khi chậm trả {TV}; bỏ điều kiện 'mất quyền lãi nếu không thông báo trong X ngày'.",
    },
    # --- Chủ đề 10: Bảo hiểm ---
    {
        "id": "ins_professional",
        "topic": 10, "level": CAM,
        "label": "Buộc mua bảo hiểm trách nhiệm nghề nghiệp",
        "pattern": r"bảo hiểm trách nhiệm nghề nghiệp|professional indemnity insurance|bảo hiểm trách nhiệm (nghề|công việc)",
        "problem": "Kiểm tra theo VAI TRÒ: bảo hiểm trách nhiệm nghề nghiệp chỉ bắt buộc với một số hoạt động tư vấn (vd khảo sát, thiết kế); với giám sát thi công/QLDA/kiểm định thì KHÔNG bắt buộc — nếu {TV} thuộc nhóm không bắt buộc thì việc buộc mua làm tăng chi phí.",
        "basis": "Quy định về bảo hiểm bắt buộc trong hoạt động xây dựng (Luật XD & NĐ hướng dẫn): bảo hiểm TNN nghề nghiệp áp cho tư vấn khảo sát/thiết kế; với giám sát/QLDA không bắt buộc; BHXH đã gồm BH tai nạn LĐ.",
        "suggest": "Ghi 'mua bảo hiểm theo quy định pháp luật' hoặc bỏ yêu cầu bắt buộc; nếu CĐT muốn thì tính vào giá.",
    },
    # --- Chủ đề 13: Nhân lực ---
    {
        "id": "hr_replace_notice",
        "topic": 13, "level": CAM,
        "label": "Thay 'bất kỳ nhân sự' phải báo trước dài & CĐT chấp thuận",
        "pattern": r"thay (thế )?(bất kỳ )?nhân sự.{0,40}(30|ba mươi|15|mười lăm) ngày|báo trước.{0,20}(30|ba mươi) ngày|replace.{0,30}(30|thirty) days.{0,20}notice",
        "problem": "Báo trước dài (30 ngày) cho MỌI nhân sự là bất khả thi khi nhân sự nghỉ đột xuất, ốm đau.",
        "basis": "Mẫu TT02: chỉ ràng buộc nhân sự chủ chốt; bất khả kháng được thay ngay bằng người tương đương.",
        "suggest": "30 ngày chỉ áp cho nhân sự chủ chốt thay chủ động; trường hợp đột xuất thay ngay bằng người tương đương (báo 3 ngày).",
    },
    {
        "id": "hr_anytime",
        "topic": 13, "level": CAM,
        "label": "Buộc làm việc kể cả lễ/tết, bất kỳ thời điểm, không tính phí",
        "pattern": r"kể cả (ngày )?(nghỉ|lễ|tết)|bất kỳ thời điểm.{0,30}yêu cầu|including (weekends?|holidays?|public holidays?)|ngày nghỉ, lễ, tết",
        "problem": "Buộc {TV} làm ngoài giờ/ngày lễ không giới hạn và không bù chi phí, đẩy chi phí nhân công sang {TV}.",
        "basis": "Bộ luật Lao động (làm thêm giờ có giới hạn và phải trả lương thêm giờ); mẫu TT02 giới hạn hợp lý.",
        "suggest": "Giới hạn trong giờ làm việc; phần vượt mức/ngoài giờ có cơ chế bù chi phí hoặc nghỉ bù.",
    },
    # --- Chủ đề 7: Tạm ứng / giữ lại ---
    {
        "id": "retention_no_release",
        "topic": 7, "level": CAM,
        "label": "Giữ lại % nhưng không nêu thời điểm hoàn trả",
        "pattern": r"giữ lại\s*\d{1,2}\s*%|tiền giữ lại|retention( money)?|giữ lại (mỗi đợt|một phần)",
        "problem": "(Phát hiện khi CÓ giữ lại) — cần kiểm tra có nêu rõ thời điểm/điều kiện hoàn trả phần giữ lại không; thiếu = CĐT giam tiền vô hạn.",
        "basis": "Mẫu TT02 và NĐ 37/2015 (sửa NĐ 50/2021): quy định rõ điều kiện hoàn trả tiền giữ lại.",
        "suggest": "Quy định rõ thời điểm/điều kiện hoàn trả phần giữ lại (vd: sau nghiệm thu hoàn thành dịch vụ {TV}).",
    },
    # --- Chủ đề 9: Bảo lãnh ---
    {
        "id": "guarantee_unconditional",
        "topic": 9, "level": CAM,
        "label": "Bảo lãnh 'vô điều kiện, không hủy ngang', hiệu lực dài",
        "pattern": r"vô điều kiện.{0,20}không hủy ngang|không hủy ngang.{0,20}vô điều kiện|unconditional.{0,20}irrevocable|bảo lãnh.{0,30}(1|2|một|hai) năm",
        "problem": "Bảo lãnh vô điều kiện cho CĐT rút tiền không cần chứng minh vi phạm; hiệu lực dài + không gia hạn thì CĐT giữ tiền.",
        "basis": "Mẫu TT02: giá trị bảo lãnh giảm dần theo thu hồi; gắn việc rút bảo lãnh với vi phạm thực tế.",
        "suggest": "Giá trị bảo lãnh giảm dần theo tạm ứng đã thu hồi; gắn quyền rút với vi phạm thực tế; mốc hiệu lực khớp tiến độ.",
    },
    # --- Chủ đề 15: Bảo mật ---
    {
        "id": "confid_perpetuity",
        "topic": 15, "level": CAM,
        "label": "Nghĩa vụ bảo mật 'vĩnh viễn'",
        "pattern": r"bảo mật.{0,20}vĩnh viễn|vĩnh viễn.{0,20}bảo mật|in perpetuity|mãi mãi.{0,20}bảo mật",
        "problem": "Nghĩa vụ bảo mật vô thời hạn tạo rủi ro pháp lý kéo dài không cần thiết.",
        "basis": "Thông lệ: bảo mật có thời hạn hợp lý (vd 3 năm sau chấm dứt).",
        "suggest": "Đặt thời hạn bảo mật cụ thể (vd 3 năm sau khi chấm dứt hợp đồng); tránh 'vĩnh viễn'.",
    },
    # --- Chủ đề 20: Chuyển nhượng ---
    {
        "id": "assign_asym",
        "topic": 20, "level": CAM,
        "label": "Chuyển nhượng bất đối xứng (chỉ CĐT được chuyển)",
        "pattern": r"chuyển nhượng|chuyển giao hợp đồng|assign\w*|novat\w*",
        "problem": "(Phát hiện khi CÓ) — kiểm tra điều khoản chuyển nhượng có đối xứng không; thường CĐT được chuyển còn {TV} thì không.",
        "basis": "BLDS 2015 Điều 365 (chuyển giao quyền); thông lệ: bên nhận phải đủ năng lực.",
        "suggest": "Việc CĐT chuyển nhượng phải bảo đảm bên nhận đủ năng lực thanh toán và không làm giảm quyền lợi {TV}.",
    },
    # --- Chủ đề 25: Thông luật / quốc tế ---
    {
        "id": "indemnify",
        "topic": 25, "level": DO,
        "label": "Indemnify / hold harmless (bồi hoàn, gánh chịu thay)",
        "pattern": r"indemnif\w*|hold (the )?\w*\s*harmless|bồi hoàn|gánh chịu thay",
        "problem": "{TV} 'bồi hoàn và giữ CĐT vô hại' trước MỌI khiếu nại/tổn thất — phạm vi cực rộng, thường không trần, không loại trừ gián tiếp.",
        "basis": "Thông lệ tư vấn quốc tế giới hạn indemnity theo phần lỗi và có trần; BLDS chỉ bồi thường thiệt hại do lỗi.",
        "suggest": "Thêm trần trách nhiệm; loại trừ thiệt hại gián tiếp; giới hạn indemnity theo phần lỗi của {TV} và mức bảo hiểm.",
    },
    {
        "id": "best_endeavour",
        "topic": 25, "level": CAM,
        "label": "Chuẩn 'best / utmost endeavours' (nỗ lực cao nhất)",
        "pattern": r"best endeavou?rs?|utmost endeavou?rs?|nỗ lực (cao nhất|hết sức|tối đa)",
        "problem": "'Best/utmost endeavours' là chuẩn thực hiện rất cao, dễ bị quy chưa làm hết sức.",
        "basis": "Thông lệ tư vấn: 'reasonable skill, care and diligence' (kỹ năng và sự cẩn trọng hợp lý).",
        "suggest": "Đề nghị đổi thành 'reasonable skill, care and diligence' theo chuẩn tư vấn thông thường.",
    },
    {
        "id": "ip_assign",
        "topic": 14, "level": DO,
        "label": "Toàn bộ bản quyền 'assigned to the Employer'",
        "pattern": r"copyright .{0,30}(assigned|become the property)|assigned to the employer|chuyển (giao|nhượng).{0,20}(toàn bộ )?bản quyền|bản quyền .{0,20}(thuộc|sở hữu) (của )?(chủ đầu tư|bên a)",
        "problem": "Chuyển QUYỀN SỞ HỮU (không chỉ quyền sử dụng) tài liệu cho CĐT, kèm bảo đảm/indemnity về SHTT — mất know-how riêng.",
        "basis": "Luật SHTT; thông lệ tư vấn giữ quyền sở hữu, chỉ cấp quyền sử dụng cho dự án.",
        "suggest": "Giữ quyền sở hữu, chỉ cấp quyền sử dụng cho dự án; gắn quyền sử dụng với điều kiện đã thanh toán; giới hạn indemnity SHTT theo phần lỗi.",
    },
    {
        "id": "lang_prevail_foreign",
        "topic": 21, "level": DO,
        "label": "Ngôn ngữ ưu tiên là tiếng nước ngoài",
        "pattern": r"(bản tiếng (anh|trung|nước ngoài)).{0,30}(ưu tiên|làm chuẩn|prevail)|english (version|language) shall prevail|shall prevail",
        "problem": "Khi hợp đồng song ngữ lấy bản tiếng nước ngoài làm chuẩn, mọi khác biệt câu chữ sẽ giải thích bất lợi cho {TV}, nhất là khi tố tụng tại VN.",
        "basis": "Khi luật áp dụng là VN và tố tụng tại VN, nên giữ tiếng Việt ưu tiên.",
        "suggest": "Giữ bản tiếng Việt ưu tiên (hoặc ít nhất ngang giá trị); đối chiếu kỹ câu chữ hai bản trước khi ký.",
    },
    {
        "id": "discretion",
        "topic": 25, "level": CAM,
        "label": "CĐT 'toàn quyền quyết định' (absolute / sole discretion)",
        "pattern": r"absolute discretion|sole discretion|toàn quyền (quyết định|định đoạt)|đánh giá đơn phương",
        "problem": "Trao CĐT quyền quyết định tuyệt đối (vd novate hợp đồng, thay nhân sự) khiến {TV} không có cơ sở phản đối.",
        "basis": "Nguyên tắc thiện chí, bình đẳng (BLDS Điều 3); thông lệ yêu cầu 'reasonable' thay vì 'absolute'.",
        "suggest": "Đổi 'absolute/sole discretion' → quyết định 'hợp lý' (reasonable) và phải thông báo lý do.",
    },
    {
        "id": "pdpa",
        "topic": 23, "level": CAM,
        "label": "Phụ lục bảo vệ dữ liệu cá nhân (PDPA)",
        "pattern": r"personal data protection|dữ liệu cá nhân|pdpa|bảo vệ dữ liệu",
        "problem": "(Phát hiện khi CÓ) — phụ lục PDPA quốc tế thường buộc {TV} xử lý/bảo vệ dữ liệu theo chuẩn CĐT kèm bồi thường vô hạn khi vi phạm.",
        "basis": "NĐ 13/2023/NĐ-CP về bảo vệ dữ liệu cá nhân.",
        "suggest": "Giới hạn phạm vi dữ liệu {TV} thực sự xử lý; gắn trách nhiệm với phần lỗi và mức bảo hiểm; tránh trách nhiệm vô hạn.",
    },
    {
        "id": "no_reduce_liability",
        "topic": 4, "level": CAM,
        "label": "'Phê duyệt của CĐT không làm giảm trách nhiệm {TV}'",
        "pattern": r"không làm giảm.{0,20}trách nhiệm|không (miễn|loại trừ).{0,20}trách nhiệm|shall not.{0,30}(reduce|relieve).{0,20}(liability|responsibility)",
        "problem": "Câu này khiến việc CĐT/cơ quan đã chấp thuận vẫn không giúp {TV} giảm trách nhiệm — chấp nhận được nhưng cần giới hạn.",
        "basis": "Thông lệ giám sát: trách nhiệm gắn với phạm vi và mức lỗi.",
        "suggest": "Chấp nhận nhưng gắn trách nhiệm với phạm vi công việc và mức lỗi của {TV}, không phải trách nhiệm tuyệt đối.",
    },
    {
        "id": "after_liquidation",
        "topic": 11, "level": CAM,
        "label": "Trách nhiệm/hỗ trợ sau thanh lý 'không thêm chi phí'",
        "pattern": r"sau (khi )?thanh lý|không (giới hạn bởi|bị giới hạn).{0,20}thanh lý|hỗ trợ.{0,30}không (thêm|tính) (chi )?phí|after (the )?liquidation",
        "problem": "Buộc {TV} tiếp tục trách nhiệm/hỗ trợ sau thanh lý mà không thêm chi phí, kéo dài nghĩa vụ vô thời hạn.",
        "basis": "Thời hiệu trách nhiệm theo pháp luật; công việc phát sinh đáng kể phải có phí.",
        "suggest": "Giới hạn trách nhiệm theo thời hiệu pháp luật; việc phát sinh đáng kể sau thanh lý có phí riêng.",
    },
]


# =============================================================================
# TOPICS — 21 chủ đề chuẩn để kiểm tra ĐỘ PHỦ (presence/absence)
#   keywords: nếu toàn văn có chứa ÍT NHẤT 1 keyword → coi như "có nhắc tới chủ đề"
#   missing_risk: cảnh báo khi chủ đề KHÔNG xuất hiện (thiếu cũng là rủi ro)
# =============================================================================
TOPICS = [
    {"id": 1, "name": "Định nghĩa & diễn giải",
     "keywords": ["định nghĩa", "diễn giải", "giải thích từ ngữ", "definition", "interpretation"],
     "missing_risk": CAM,
     "missing_note": "Không có mục định nghĩa/diễn giải — các thuật ngữ 'phạm vi', 'hoàn thành', 'chấp thuận' dễ bị hiểu rộng bất lợi cho {TV}."},

    {"id": 2, "name": "Hồ sơ hợp đồng & thứ tự ưu tiên",
     "keywords": ["thứ tự ưu tiên", "hồ sơ hợp đồng", "tài liệu hợp đồng", "order of precedence", "ưu tiên áp dụng"],
     "missing_risk": CAM,
     "missing_note": "Không quy định thứ tự ưu tiên hồ sơ — khi tài liệu mâu thuẫn sẽ tranh chấp cách hiểu."},

    {"id": 3, "name": "Phạm vi & nội dung công việc",
     "keywords": ["phạm vi", "nội dung công việc", "công việc tư vấn", "scope", "dịch vụ tư vấn", "nhiệm vụ giám sát"],
     "missing_risk": DO,
     "missing_note": "Không thấy mô tả phạm vi công việc rõ ràng — rủi ro bị suy diễn mở rộng nghĩa vụ. Đối chiếu Điều 19 NĐ 06/2021."},

    {"id": 4, "name": "Chất lượng sản phẩm / tiêu chuẩn",
     "keywords": ["chất lượng", "tiêu chuẩn", "quy chuẩn", "yêu cầu kỹ thuật", "quality", "standard"],
     "missing_risk": CAM,
     "missing_note": "Không nêu yêu cầu chất lượng/tiêu chuẩn sản phẩm tư vấn — khó xác định khi nào hoàn thành đạt yêu cầu."},

    {"id": 5, "name": "Thời gian, tiến độ, tạm ngừng",
     "keywords": ["thời gian thực hiện", "tiến độ", "thời hạn", "tạm ngừng", "thời gian hoàn thành", "duration", "schedule"],
     "missing_risk": CAM,
     "missing_note": "Không quy định rõ thời gian/tiến độ và cơ chế khi kéo dài ngoài lỗi {TV}."},

    {"id": 6, "name": "Giá hợp đồng & điều chỉnh giá",
     "keywords": ["giá hợp đồng", "giá trị hợp đồng", "điều chỉnh giá", "trọn gói", "đơn giá", "contract price", "lump sum"],
     "missing_risk": DO,
     "missing_note": "Không thấy giá hợp đồng/loại hợp đồng và cơ chế điều chỉnh giá — thiếu căn cứ thanh toán."},

    {"id": 7, "name": "Tạm ứng, thu hồi, giữ lại",
     "keywords": ["tạm ứng", "thu hồi tạm ứng", "giữ lại", "retention", "advance payment"],
     "missing_risk": CAM,
     "missing_note": "Không có điều khoản tạm ứng/giữ lại — bất lợi dòng tiền cho {TV} (mẫu TT02 thường có tạm ứng)."},

    {"id": 8, "name": "Thanh toán & quyết toán",
     "keywords": ["thanh toán", "quyết toán", "đợt thanh toán", "hồ sơ thanh toán", "payment", "invoice"],
     "missing_risk": DO,
     "missing_note": "Không quy định rõ thời hạn thanh toán, hồ sơ và lãi chậm trả — rủi ro bị giam tiền."},

    {"id": 9, "name": "Bảo lãnh (thực hiện HĐ / hoàn trả tạm ứng)",
     "keywords": ["bảo lãnh", "bảo đảm thực hiện", "performance security", "performance bond", "advance guarantee"],
     "missing_risk": XANH,
     "missing_note": "Không yêu cầu bảo lãnh — thường có lợi cho {TV} (giảm chi phí), nhưng kiểm tra lại."},

    {"id": 10, "name": "Bảo hiểm",
     "keywords": ["bảo hiểm", "insurance", "trách nhiệm nghề nghiệp"],
     "missing_risk": XANH,
     "missing_note": "Không có yêu cầu bảo hiểm — thường ổn với {TV}, nhưng xác nhận lại."},

    {"id": 11, "name": "Nghĩa vụ & trách nhiệm Bên B ({TV})",
     "keywords": ["nghĩa vụ của bên b", "trách nhiệm của bên b", "nghĩa vụ tư vấn", "quyền và nghĩa vụ", "obligations of the consultant"],
     "missing_risk": CAM,
     "missing_note": "Không tách rõ nghĩa vụ Bên B — khó khoanh vùng trách nhiệm."},

    {"id": 12, "name": "Nghĩa vụ & chế tài đối với CĐT (đối xứng)",
     "keywords": ["nghĩa vụ của bên a", "trách nhiệm của bên a", "nghĩa vụ chủ đầu tư", "obligations of the employer", "chế tài đối với chủ đầu tư"],
     "missing_risk": DO,
     "missing_note": "Không thấy nghĩa vụ/chế tài đối với CĐT — mất đối xứng, {TV} không có công cụ khi CĐT chậm tài liệu/mặt bằng/thanh toán."},

    {"id": 13, "name": "Nhân lực",
     "keywords": ["nhân sự", "nhân lực", "cán bộ giám sát", "personnel", "key staff", "thay thế nhân sự"],
     "missing_risk": CAM,
     "missing_note": "Không quy định về nhân lực/thay thế nhân sự — dễ tranh chấp khi điều chuyển người."},

    {"id": 14, "name": "Bản quyền / sở hữu trí tuệ",
     "keywords": ["bản quyền", "sở hữu trí tuệ", "quyền sử dụng tài liệu", "copyright", "intellectual property"],
     "missing_risk": CAM,
     "missing_note": "Không có điều khoản bản quyền/SHTT — kiểm tra để bảo lưu know-how của {TV}."},

    {"id": 15, "name": "Bảo mật thông tin",
     "keywords": ["bảo mật", "thông tin mật", "confidential", "non-disclosure", "nda"],
     "missing_risk": XANH,
     "missing_note": "Không có điều khoản bảo mật — thường không bất lợi cho {TV}, nhưng kiểm tra yêu cầu của dự án."},

    {"id": 16, "name": "Phạt vi phạm & bồi thường",
     "keywords": ["phạt vi phạm", "phạt hợp đồng", "bồi thường", "penalty", "liquidated damages", "phạt"],
     "missing_risk": CAM,
     "missing_note": "Không có điều khoản phạt/bồi thường rõ — nhưng cần chắc không bị dẫn chiếu mức phạt từ tài liệu khác."},

    {"id": 17, "name": "Liêm chính / chống hối lộ",
     "keywords": ["liêm chính", "chống hối lộ", "tham nhũng", "anti-bribery", "integrity", "anti-corruption"],
     "missing_risk": XANH,
     "missing_note": "Không có điều khoản liêm chính — bình thường; nếu có phụ lục quy chế thì phải đọc kỹ."},

    {"id": 18, "name": "Tạm ngừng & chấm dứt",
     "keywords": ["chấm dứt hợp đồng", "tạm ngừng", "đơn phương chấm dứt", "termination", "suspension"],
     "missing_risk": DO,
     "missing_note": "Không quy định điều kiện tạm ngừng/chấm dứt và thanh toán khi chấm dứt — rủi ro lớn khi quan hệ kết thúc."},

    {"id": 19, "name": "Bất khả kháng",
     "keywords": ["bất khả kháng", "force majeure", "sự kiện khách quan"],
     "missing_risk": CAM,
     "missing_note": "Không có điều khoản bất khả kháng — rủi ro khi xảy ra sự kiện ngoài tầm kiểm soát."},

    {"id": 20, "name": "Chuyển nhượng",
     "keywords": ["chuyển nhượng", "chuyển giao hợp đồng", "assignment", "novation"],
     "missing_risk": XANH,
     "missing_note": "Không có điều khoản chuyển nhượng — thường ổn; kiểm tra nếu CĐT là pháp nhân dự án (SPV)."},

    {"id": 21, "name": "Luật áp dụng, tranh chấp, ngôn ngữ",
     "keywords": ["luật áp dụng", "giải quyết tranh chấp", "trọng tài", "tòa án", "ngôn ngữ", "governing law", "dispute", "arbitration"],
     "missing_risk": DO,
     "missing_note": "Không quy định luật áp dụng/giải quyết tranh chấp/ngôn ngữ — đặc biệt rủi ro với hợp đồng FDI/song ngữ."},
]


# Thuật ngữ cảnh báo phụ (chỉ liệt kê khi gặp, không phải lỗi) — soi hợp đồng tiếng Anh
EN_WARN_TERMS = {
    "time is of the essence": "Thời hạn là yếu tố cốt yếu — siết tiến độ rất chặt, chậm nhẹ cũng coi là vi phạm cơ bản.",
    "set-off": "Khấu trừ — kiểm tra CĐT có được đơn phương khấu trừ khi đang tranh chấp không.",
    "entire agreement": "Thỏa thuận trọn vẹn — mọi cam kết miệng ngoài văn bản sẽ vô hiệu; đưa cam kết quan trọng vào HĐ.",
    "no oral variation": "Chỉ sửa bằng văn bản — bảo đảm các thống nhất sau này được lập thành văn bản.",
    "defects notification period": "Thời gian thông báo khiếm khuyết (bảo hành) — {TV} có