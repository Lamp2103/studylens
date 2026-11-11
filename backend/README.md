# StudyLens – Backend

FastAPI + SQLAlchemy + SQLite. Yêu cầu: Python 3.12 (hoặc 3.11).

## Cài đặt (làm một lần)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env               # Windows: copy .env.example .env
```

## Tạo cơ sở dữ liệu

```bash
alembic upgrade head               # tạo file data/studylens.db với đủ 7 bảng
```

## Tạo dữ liệu mô phỏng

```bash
python -m app.seed.seed_data            # 1 môn, 6 chủ đề, 5 sinh viên giả (mật khẩu chung: Demo@123)
python -m app.seed.seed_data --reset    # xóa dữ liệu mô phỏng cũ rồi tạo lại
```

Dữ liệu này là dữ liệu thử nghiệm (`users.is_synthetic = 1`). Chi tiết 5 sinh viên và kết quả
mong đợi: `docs/03-api/seed-data-design.md`.

## Hợp đồng API và chỉ số

- `docs/03-api/openapi.yaml`: hợp đồng giữa frontend và backend (viết trước, mã làm theo). Sửa hợp đồng TRƯỚC, báo người kia, rồi mới viết mã.
- `docs/03-api/metrics-definition.md`: cách tính mọi chỉ số, ngưỡng, gợi ý.
- `docs/03-api/examples/*.json`: dữ liệu mẫu cho từng endpoint. Frontend chép vào `src/mocks/` để làm giao diện trước khi backend xong.
- `pytest` kiểm tra hợp đồng hợp lệ OpenAPI 3.1, mọi file mẫu khớp schema, các file mẫu nhất quán với quy tắc tính, và mọi route đã cài đặt có trong hợp đồng (test `test_implemented_routes_match_the_contract`).
- Khi thêm endpoint: thêm vào `openapi.yaml` trước, thêm file mẫu, rồi mới viết route.

## Chạy

```bash
uvicorn app.main:app --reload
```

- Kiểm tra nhanh: http://127.0.0.1:8000/health
- Tài liệu API (Swagger): http://127.0.0.1:8000/docs

## Kiểm thử và kiểm tra mã

```bash
pytest
ruff check .
ruff format .
```

## Migration (Alembic)

| Việc | Lệnh |
|---|---|
| Tạo/cập nhật DB lên bản mới nhất | `alembic upgrade head` |
| Xem bản hiện tại | `alembic current` |
| Lùi một bước | `alembic downgrade -1` |
| Xóa sạch DB rồi tạo lại (dữ liệu mô phỏng sẽ mất) | xóa `data/studylens.db`, rồi `alembic upgrade head` |
| Sinh migration mới sau khi sửa model | `alembic revision --autogenerate -m "mô tả ngắn"` |

**Quy trình khi sửa model:**

1. Sửa model trong `app/models/`.
2. Chạy `alembic revision --autogenerate -m "..."`.
3. **Đọc lại file sinh ra trong `alembic/versions/` trước khi commit.** Autogenerate không phải lúc nào cũng đúng
   (xem mục "Giới hạn" bên dưới).
4. `alembic upgrade head`, sau đó `pytest`. Test `test_models_and_migration_are_in_sync` sẽ báo nếu
   model và migration lệch nhau.
5. Commit model và file migration **cùng một lần**.

**Không sửa migration đã được người kia chạy rồi.** Cần đổi gì thì tạo migration mới.

**Giới hạn cần nhớ:**

- Autogenerate **không thấy chỉ mục dùng biểu thức** (như `uq_recs_current`). Loại này phải viết tay bằng `op.create_index`.
- Mọi ràng buộc cần có **tên** (`CheckConstraint(..., name="...")`, `UniqueConstraint(..., name="uq_...")`),
  vì SQLite sửa bảng bằng cách tạo lại bảng và chỉ xử lý được ràng buộc có tên.
- Migration chạy với khóa ngoại **tắt** (cố ý, xem `alembic/env.py`) để việc tạo lại bảng không xóa nhầm dữ liệu bảng con.
- Migration không được `import app...`. Dùng kiểu của SQLAlchemy (`sa.Text()`), không dùng kiểu tự định nghĩa.

## Model

7 model trong `app/models/`, mỗi file một bảng. Mô tả đầy đủ ở `docs/03-api/db-schema.md`.

- Thời gian lưu dạng chuỗi ISO 8601 UTC kết thúc bằng `Z`. **Luôn dùng `app.core.time.to_iso()` / `utc_now_iso()`**,
  không tự `isoformat()`, vì trộn `Z` với `+00:00` làm so sánh thứ tự thời gian sai.
- Các giá trị cố định (vai trò, loại bài, trạng thái gợi ý...) nằm ở `app/models/enums.py`.
- `Recommendation.evidence_json` đọc/ghi trực tiếp bằng dict Python.
- Ba ràng buộc liên bảng SQLite không kiểm tra được (`score ≤ max_score`, `wrong_count ≤ total_questions`,
  `week_no ≤ total_weeks`) phải kiểm tra ở tầng API.

## Cấu trúc

```
app/
├── main.py              # tạo app, CORS, gắn router
├── core/
│   ├── config.py        # cấu hình (đọc từ .env)
│   ├── database.py      # engine, session, Base, get_db
│   ├── security.py      # băm / kiểm tra mật khẩu (bcrypt)
│   └── time.py          # định dạng thời gian thống nhất
├── api/
│   ├── deps.py          # dependency dùng chung (DbSession)
│   └── routes/          # mỗi file một nhóm endpoint
├── schemas/             # Pydantic: dữ liệu vào/ra của API
├── models/              # SQLAlchemy: 7 bảng, enums
├── services/            # nghiệp vụ
├── analytics/           # tính chỉ số, gợi ý (không phụ thuộc FastAPI)
└── seed/                # seed_data.py: sinh dữ liệu mô phỏng
alembic/                 # migration (versions/ chứa các bản migration)
tests/
data/                    # file SQLite (không commit)
```

## Lưu ý

- SQLite mặc định tắt khóa ngoại. `core/database.py` đã bật `PRAGMA foreign_keys=ON`
  cho mỗi kết nối, **không xóa đoạn này**.
- File `.env` và `data/*.db` không được commit.
- Thêm endpoint mới: tạo file trong `api/routes/`, rồi gắn vào `api/routes/__init__.py`.
