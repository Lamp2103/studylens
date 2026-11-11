# Phạm vi MVP – StudyLens

> Trạng thái: **Đề xuất, chờ hai thành viên xác nhận tại buổi họp khởi động**
> Ngày chốt: ____/____/______
> Người tham gia: Thành viên 1: __________ | Thành viên 2: __________

## 1. Mục tiêu MVP

Một prototype web chạy được với dữ liệu mô phỏng, cho phép sinh viên:

1. Đăng nhập và xem dashboard tổng quan kết quả học tập.
2. Xem kết quả chi tiết theo từng chủ đề.
3. Biết chủ đề nào mạnh, chủ đề nào yếu.
4. Nhận gợi ý ôn tập **kèm lý do giải thích**.
5. So sánh tiến bộ giữa các tuần.
6. Nhập kết quả mới và thấy chỉ số, biểu đồ, gợi ý được cập nhật.

Điểm nổi bật cần bảo vệ trước hết: **gợi ý có giải thích** (FR05, FR06).

## 2. Trong phạm vi MVP (làm bắt buộc)

| Mã | Chức năng | Ưu tiên | Tiêu chí hoàn thành (Definition of Done) |
|---|---|---|---|
| FR01 | Đăng nhập | Cao | Đăng nhập đúng vào được hệ thống; sai mật khẩu hiện thông báo lỗi rõ; chưa đăng nhập thì không truy cập được các trang khác. |
| FR02 | Dashboard tổng quan | Cao | Hiển thị điểm trung bình, tiến độ hoàn thành bài tập, xu hướng kết quả. Số liệu khớp giá trị tham chiếu trong unit test. |
| FR03 | Xem kết quả theo chủ đề | Cao | Chọn một chủ đề thì thấy điểm, số bài đã làm và lịch sử kết quả của chủ đề đó. |
| FR04 | Phân tích điểm mạnh, điểm yếu | Cao | Mỗi chủ đề được gắn nhãn mạnh/trung bình/yếu theo quy tắc đã ghi trong `metrics-definition.md`. Nhãn không chỉ dựa vào màu sắc (NFR11). |
| FR05 | Gợi ý ôn tập cá nhân hóa | Cao | Hệ thống trả về danh sách gợi ý đã xếp thứ tự ưu tiên theo quy tắc xác định trước. |
| FR06 | Giải thích gợi ý | Cao | Mỗi gợi ý có ít nhất một lý do cụ thể, kiểm chứng được từ dữ liệu (NFR05). |
| FR07 | Theo dõi tiến bộ theo tuần | Cao | Xem và so sánh kết quả giữa các tuần bằng biểu đồ. |
| FR08 | Cập nhật dữ liệu học tập | Cao | Nhập kết quả mới thì dashboard, biểu đồ và gợi ý liên quan được làm mới. Dữ liệu không hợp lệ bị từ chối kèm thông báo (NFR08). |
| FR12 | Đăng xuất | Cao | Đăng xuất kết thúc phiên, quay về trang đăng nhập, không quay lại được bằng nút Back mà vẫn thấy dữ liệu. |

## 3. Hoãn lại (làm sau nếu còn thời gian)

| Mã | Chức năng | Ưu tiên | Cách xử lý trong MVP |
|---|---|---|---|
| FR09 | Ghi nhận thời gian học | Trung bình | Schema **vẫn có** bảng `study_sessions` và dữ liệu mô phỏng có sẵn thời gian học. Không làm giao diện ghi nhận phiên học. Thẻ "thời gian học" trên dashboard đọc từ dữ liệu mô phỏng, hiển thị nhãn "dữ liệu thử nghiệm". |
| FR10 | Lọc dữ liệu | Trung bình | MVP chỉ có **một môn học** và hiển thị theo tuần mặc định, không có bộ lọc. API thiết kế sẵn tham số `topic_id`, `from`, `to` để thêm sau không phải sửa lớn. |
| FR11 | Tùy chỉnh gợi ý (chấp nhận, bỏ qua, hoàn thành) | Trung bình | Bảng `recommendations` **vẫn có** cột `status` (mặc định `pending`). Giao diện chỉ hiển thị gợi ý, chưa có nút thao tác. |

## 4. Ngoài phạm vi dự án

- Ứng dụng di động, giao diện responsive cho điện thoại. NFR09 chỉ yêu cầu trình duyệt máy tính (Chrome, Edge).
- Nhiều môn học cùng lúc.
- Đăng ký tài khoản, quên mật khẩu, phân quyền nhiều vai trò. MVP dùng tài khoản sinh viên tạo sẵn từ script seed.
- Mô hình học máy. Gợi ý dùng quy tắc có thể giải thích.
- Tích hợp với hệ thống học tập thật (LMS).

## 5. Thứ tự cắt giảm nếu trễ tiến độ

Cắt từ trên xuống, dừng lại khi kịp:

1. So sánh A/B giữa giao diện chỉ thống kê và giao diện có gợi ý (phần đánh giá, báo cáo ghi "nếu đủ điều kiện").
2. Hoàn thiện FR09, FR10, FR11 (nếu đã làm dở thì dừng ở mức hiển thị).
3. Rút số trang xuống còn: Đăng nhập, Dashboard, Gợi ý (gộp Chi tiết chủ đề và Tiến bộ theo tuần vào Dashboard).

**Không cắt:** FR05, FR06 (điểm nổi bật), FR08 (chứng minh dữ liệu cập nhật được) và FR01/FR12 (nền tảng bảo mật).

## 6. Mốc kiểm soát

| Mốc | Thời điểm | Điều kiện đạt |
|---|---|---|
| M1 – Nền tảng | Cuối tuần 1 | Repo, `openapi.yaml`, schema, dữ liệu mô phỏng, wireframe low-fi xong. |
| M2 – Prototype | Cuối tuần 2 | Prototype Figma bấm thử được. API đăng nhập và dashboard chạy. |
| M3 – Luồng chính | Cuối tuần 4 | Chạy trọn từ đăng nhập đến nhận gợi ý có giải thích. |
| M4 – Đóng băng tính năng | Cuối tuần 5 | Không thêm tính năng mới sau mốc này. |
| M5 – Có dữ liệu đánh giá | Cuối tuần 6 | Hoàn tất usability test và kiểm thử kỹ thuật. |
| M6 – Nộp bài | Cuối tuần 7 | Báo cáo, demo, video dự phòng. |

## 7. Quy tắc thay đổi phạm vi

- Muốn thêm hoặc bớt một mục: cả hai cùng đồng ý, ghi lại ngày, lý do vào bảng dưới.
- Sau M4, chỉ được bớt, không được thêm.

| Ngày | Thay đổi | Lý do | Người đề xuất |
|---|---|---|---|
| | | | |
