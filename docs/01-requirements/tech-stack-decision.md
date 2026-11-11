# Quyết định công nghệ – StudyLens

> Trạng thái: **Đề xuất, chờ xác nhận tại buổi họp khởi động**
> Ngày chốt: ____/____/______
> Thay thế mục 5 "Công nghệ dự kiến" trong báo cáo tuần 1 (ghi "sẽ chốt sau").

## 1. Nguyên tắc chọn

1. **Giữ nguyên danh sách trong báo cáo tuần 1** nếu không có lý do mạnh để đổi, vì báo cáo đã nộp.
2. Ưu tiên công nghệ **ít cấu hình, nhiều tài liệu**, phù hợp 2 người trong 7 tuần.
3. Mỗi công nghệ phải phục vụ ít nhất một yêu cầu trong `mvp-scope.md`.
4. Không thêm thư viện chỉ vì "có thể sẽ cần".

## 2. Công nghệ chính thức

### Frontend

| Hạng mục | Chọn | Phục vụ yêu cầu | Lý do |
|---|---|---|---|
| Framework | **React** + **TypeScript** | Toàn bộ giao diện | Đã nêu trong báo cáo. TypeScript giúp khớp kiểu dữ liệu với API. |
| Công cụ build | **Vite** | NFR10 | Khởi động nhanh, ít cấu hình. |
| Biểu đồ | **Recharts** | FR02, FR03, FR07 | Đã nêu trong báo cáo. Cho phép tùy biến nhãn, trục, tooltip để đáp ứng NFR11. |
| Định tuyến | **React Router** | 5 trang | Chuẩn phổ biến. |
| Gọi API và trạng thái tải | **TanStack Query** | NFR08 | Có sẵn trạng thái loading, error, retry, giúp hiển thị thông báo lỗi đúng chuẩn mà không tự viết nhiều. |
| Giao diện | **CSS Modules** + biến CSS (design tokens) | NFR04, NFR11 | Kiểm soát màu, độ tương phản, font thống nhất giữa các trang. Không thêm framework CSS. |
| Kiểm thử | **Vitest** + React Testing Library | NFR01, NFR04 | Chạy cùng Vite. |
| Chất lượng mã | **ESLint** + **Prettier** | NFR10 | Thống nhất phong cách mã giữa hai người. |

### Backend

| Hạng mục | Chọn | Phục vụ yêu cầu | Lý do |
|---|---|---|---|
| Ngôn ngữ, framework | **Python** + **FastAPI** | API | Đã nêu trong báo cáo. Tự sinh Swagger (`/docs`), khớp với `openapi.yaml`. |
| Xác thực dữ liệu | **Pydantic** | NFR08 | Đi kèm FastAPI, từ chối dữ liệu không hợp lệ. |
| ORM | **SQLAlchemy** | Toàn bộ DB | Mô hình hóa 7 bảng, dễ đổi sang DB khác sau này. |
| Migration | **Alembic** | NFR10 | Mỗi người tạo lại DB giống nhau từ lệnh. |
| Cơ sở dữ liệu | **SQLite** | Lưu trữ | Đã nêu trong báo cáo. Một file, không cần cài server. Đủ cho prototype. |
| Phân tích | **Pandas**, **NumPy** | FR02, FR04, FR07 | Đã nêu trong báo cáo. Tính trung bình, xu hướng theo tuần. |
| Xác thực người dùng | **JWT** (Bearer token) + băm mật khẩu **bcrypt** | FR01, FR12, NFR06 | Đơn giản, đủ cho prototype. |
| Kiểm thử | **pytest** + `httpx` (TestClient của FastAPI) | NFR03, NFR08 | Viết unit test cho công thức và test API. |
| Chất lượng mã | **Ruff** (lint + format) | NFR10 | Một công cụ thay cho nhiều công cụ. |

### Thiết kế và quản lý

| Hạng mục | Chọn | Lý do |
|---|---|---|
| Wireframe, prototype | **Figma** | Đã nêu trong báo cáo. |
| Mã nguồn | **Git** + **GitHub** (nhánh `main`, `develop`, `feature/*`) | Đã nêu trong báo cáo, đáp ứng NFR10. |
| Theo dõi công việc | **GitHub Projects** (bảng Kanban) hoặc Trello | Dùng chung với repo, không phải mở thêm công cụ. |
| Tài liệu | Markdown trong thư mục `docs/` | Nằm cùng mã nguồn, có lịch sử thay đổi. |

## 3. Phiên bản

Khóa phiên bản ngay khi dựng project để hai máy chạy giống nhau:

- **Node.js:** bản LTS đang hỗ trợ tại thời điểm cài. Ghi vào `frontend/.nvmrc`.
- **Python:** 3.12 hoặc 3.11. Ghi vào `backend/.python-version`.
- Frontend khóa bằng `package-lock.json`. Backend khóa bằng `requirements.txt` ghi rõ phiên bản (`pip freeze` sau khi cài xong).
- Cả hai người **cài cùng phiên bản Node và Python** trước khi bắt đầu code.

## 4. Kiến trúc tổng quát

```
Trình duyệt (React + TypeScript)
        │  HTTP/JSON, JWT
        ▼
FastAPI  ──►  services  ──►  analytics (Pandas/NumPy)
        │
        ▼
SQLAlchemy ──► SQLite
```

- Thư mục `analytics/` không phụ thuộc FastAPI, chỉ nhận dữ liệu và trả kết quả. Nhờ đó test được công thức độc lập (NFR03) và tách biệt logic phân tích (NFR10).
- Frontend chỉ nói chuyện với backend qua API đã mô tả trong `openapi.yaml`. Trong lúc backend chưa xong, frontend dùng JSON mẫu trong `src/mocks/`.

## 5. Các lựa chọn đã cân nhắc và không chọn

| Phương án | Lý do không chọn |
|---|---|
| Next.js | Cần server rendering, thêm độ phức tạp. Ứng dụng này là SPA sau đăng nhập, không cần SEO. |
| Tailwind CSS | Tốt, nhưng thêm một lớp học và cấu hình. CSS Modules + biến CSS đủ để kiểm soát nhất quán. |
| Chart.js, D3 | Chart.js phải bọc lại cho React. D3 quá thấp cấp so với thời gian có. |
| PostgreSQL | Cần cài và chạy server, không cần thiết cho prototype dữ liệu nhỏ. SQLAlchemy cho phép chuyển sau. |
| Django | Nặng hơn FastAPI, không tự sinh tài liệu OpenAPI sẵn như FastAPI. |
| Thư viện học máy (scikit-learn) | Báo cáo đã cam kết dùng quy tắc có thể giải thích để đáp ứng NFR05. |

## 6. Rủi ro công nghệ

| Rủi ro | Mức | Cách giảm |
|---|---|---|
| Thành viên chưa quen TypeScript, FastAPI | Trung bình | Dành 1–2 buổi đầu tuần 2 làm bài mẫu. Hỏi nhau và review chéo. |
| Lệch kiểu dữ liệu giữa frontend và backend | Cao | Mọi thay đổi API phải sửa `openapi.yaml` trước, thông báo người kia rồi mới code. |
| Máy hai người cài khác môi trường | Trung bình | Khóa phiên bản, có `scripts/setup.sh`, mỗi người chạy thử dự án của người kia ở cuối tuần 1. |
| SQLite xung đột khi hai người cùng dùng file DB | Thấp | File DB nằm trong `.gitignore`, mỗi người tự chạy migration và seed trên máy mình. |

## 7. Nội dung để thêm vào `README.md`

```markdown
## Công nghệ sử dụng
- Frontend: React, TypeScript, Vite, Recharts, React Router, TanStack Query
- Backend: Python, FastAPI, SQLAlchemy, Alembic, Pydantic, Pandas, NumPy
- Cơ sở dữ liệu: SQLite (prototype)
- Thiết kế: Figma
- Quản lý mã nguồn: Git, GitHub

Chi tiết và lý do lựa chọn: `docs/01-requirements/tech-stack-decision.md`
```
