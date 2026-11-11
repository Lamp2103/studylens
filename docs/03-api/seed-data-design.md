# Thiết kế dữ liệu mô phỏng – StudyLens

> Công việc W1-B4 · Script: `backend/app/seed/seed_data.py`
> **Toàn bộ dữ liệu này là dữ liệu thử nghiệm, không phải dữ liệu học tập thật.** Tài khoản gắn cờ `users.is_synthetic = 1`, mô tả môn học ghi rõ như vậy (NFR07). Khi viết báo cáo, nhớ nêu rõ điều này.

## 1. Cách dùng

```bash
cd backend
alembic upgrade head                      # nếu chưa tạo DB
python -m app.seed.seed_data              # tạo dữ liệu
python -m app.seed.seed_data --reset      # xóa dữ liệu mô phỏng cũ rồi tạo lại
python -m app.seed.seed_data --today 2026-11-12 --seed 7   # tùy chọn
```

- Mật khẩu chung của 5 tài khoản demo: `Demo@123` (đổi bằng `--password`).
- Chạy lần hai mà không có `--reset` sẽ bị từ chối, không tạo trùng.
- `--reset` chỉ xóa dữ liệu mô phỏng (`is_synthetic = 1` và môn `DEMO101`). Tài khoản thật không bị đụng tới.
- **Dữ liệu xác định:** cùng `--seed` luôn ra cùng điểm số. Đổi `--today` chỉ đổi mốc thời gian, không đổi điểm.
- Script không tạo gợi ý (`recommendations`). Gợi ý do bộ gợi ý (FR05) sinh ra từ dữ liệu này.

## 2. Quy mô

| Yêu cầu | Thực tế |
|---|---|
| 1 môn | `DEMO101` – Cấu trúc dữ liệu và giải thuật |
| 5–6 chủ đề | 6 chủ đề |
| 4–6 tuần | Môn 6 tuần, kết quả trải đều tuần 1–5 |
| 3–5 sinh viên | 5 sinh viên (`sv01`…`sv05`) |
| Có cả mạnh và yếu | Có (xem mục 4) |

Tổng cộng: 18 bài, 77 lần làm bài, 67 phiên học.

**"Tuần hiện tại" luôn là tuần 5/6**, bất kể bạn chạy script vào ngày nào: `courses.start_date` được tính lùi từ ngày chạy. Vì vậy luôn có đúng 1 bài chưa giao (tuần 6) để thử quy tắc "tiến độ = bài đã làm / bài đã giao đến tuần hiện tại".

### Chủ đề và lịch bài

Mỗi chủ đề có 3 bài (bài thứ 3 là quiz). Quiz có 20 câu, thang 20 điểm; bài tập có 10 câu, thang 10 điểm, để kiểm tra việc quy đổi ra phần trăm.

| Chủ đề | Tuần giao 3 bài |
|---|---|
| 1. Mảng và chuỗi | 1, 2, 3 |
| 2. Danh sách liên kết | 1, 2, 4 |
| 3. Ngăn xếp và hàng đợi | 2, 3, 4 |
| 4. Cây nhị phân | 3, 4, 5 |
| 5. Đồ thị | 4, 5, **6** (chưa giao) |
| 6. Sắp xếp và tìm kiếm | 1, 3, 5 |

## 3. Năm sinh viên và mục đích thử nghiệm

| SV | Câu chuyện | Dùng để thử |
|---|---|---|
| `sv01` | Tiến bộ rõ, làm đủ mọi bài, làm lại 1 bài (50% → 70%) | Xu hướng **tăng**; **lần làm gần nhất** được tính |
| `sv02` | Yếu ở Cây nhị phân và Đồ thị, kết quả đi xuống, bỏ lỡ 2 bài | Chủ đề **yếu**, xu hướng **giảm**, câu sai nhiều → gợi ý ôn tập rõ nhất |
| `sv03` | Điểm cao, ổn định, mọi chủ đề đều mạnh | Trường hợp **không có gì để gợi ý** (bộ gợi ý phải xử lý được) |
| `sv04` | Bắt đầu muộn từ tuần 3 | **"Chưa có dữ liệu"**, **"chưa đủ dữ liệu"**, tiến độ thấp |
| `sv05` | Trung bình, ổn định; điểm đúng ngưỡng; làm lại 1 bài (40% → 60%) | **Điểm biên** 75% và 50%; xu hướng **ổn định** |

## 4. Kết quả mong đợi (theo bộ quy tắc đã chốt)

Đây là kết quả do bản tính tham chiếu (`tests/reference_metrics.py`) tính ra với hạt giống mặc định. Test tự động kiểm tra bảng này, nên nếu bạn đổi dữ liệu mà bảng sai thì test báo lỗi.

Ô hiển thị: điểm TB % của chủ đề và nhãn.

| SV | Tiến độ | Xu hướng | Chủ đề 1 | Chủ đề 2 | Chủ đề 3 | Chủ đề 4 | Chủ đề 5 | Chủ đề 6 |
|---|---|---|---|---|---|---|---|---|
| sv01 | 17/17 | tăng (+9,5) | 70,0 TB | 70,0 TB | 71,7 TB | 78,3 **Mạnh** | 65,0 TB | 78,3 **Mạnh** |
| sv02 | 15/17 | giảm (−15,0) | 91,7 **Mạnh** | 80,0 **Mạnh** | 63,3 TB | 45,0 **YẾU** | 25,0 **YẾU** | 65,0 TB |
| sv03 | 17/17 | ổn định (+1,2) | 90,0 Mạnh | 90,0 Mạnh | 85,0 Mạnh | 80,0 Mạnh | 80,0 Mạnh | 91,7 Mạnh |
| sv04 | 9/17 | (không kiểm tra) | 70,0 *chưa đủ* | – *chưa có* | 57,5 TB | 63,3 TB | 55,0 TB | 75,0 *chưa đủ* |
| sv05 | 17/17 | ổn định (+1,2) | 68,3 TB | 75,0 **Mạnh** | 50,0 TB | 65,0 TB | 60,0 TB | 66,7 TB |

(TB = trung bình. *chưa đủ* = ít hơn 2 bài. *chưa có* = 0 bài.)

Xu hướng của `sv04` phụ thuộc nhiễu ngẫu nhiên (có thể ra "ổn định" hoặc "tăng" với hạt giống khác), nên test không kiểm tra nó. Với 40 hạt giống khác nhau, `sv02` luôn "giảm", `sv03` và `sv05` luôn "ổn định", `sv01` "tăng" ở 39/40 lần.

## 5. Các cách hiểu bộ quy tắc (đã chuyển sang `metrics-definition.md`)

Các cách hiểu dưới đây nay được ghi chính thức ở `metrics-definition.md` (mục 9, nhóm A) cùng các đề xuất mới. Bản tóm tắt để tiện đối chiếu:

| # | Chỗ chưa rõ | Cách hiểu đang dùng |
|---|---|---|
| 1 | "Tuần gần nhất" và "tuần trước" để tính xu hướng | **Hai tuần gần nhất có dữ liệu** của sinh viên. Không bắt buộc là tuần 5 và tuần 4 (sinh viên có thể bỏ trống một tuần). |
| 2 | Kết quả thuộc tuần nào | Tuần giao của bài (`assessments.week_no`), không phải ngày nộp. |
| 3 | Xu hướng tính trên đâu | Toàn bộ kết quả của sinh viên (điểm TB % mỗi tuần qua các chủ đề), không tính riêng từng chủ đề. Vì mỗi chủ đề chỉ có 1 bài mỗi tuần nên xu hướng theo chủ đề quá thưa. |
| 4 | Bài làm sau hạn / tuần hiện tại | "Đã giao" là mọi bài có `week_no ≤ tuần hiện tại`. Bài đã làm tính trong số bài đã giao. |
| 5 | Chênh đúng ±5 điểm % | Tính là tăng/giảm ("từ ±5 trở lên"). |
| 6 | Biên 75% và 50% | 75,0 là **mạnh**, 50,0 là **trung bình** (đúng chữ "từ … trở lên"). |

**Về làm tròn:** `7/10*100` hay `15/20*100` với số thực đôi khi ra `74.99999…`. Quy tắc chốt ở `metrics-definition.md` mục 2: làm tròn half-up 1 chữ số **trước** khi so với ngưỡng, và tính chênh lệch bằng hiệu của hai số đã làm tròn. Hệ quả: xu hướng tuần của `sv01` là 83,3 − 73,8 = **+9,5** (nếu dùng số chưa làm tròn sẽ ra 9,58). Dữ liệu của `sv05` được thiết kế chính xác tại 75,0 và 50,0 để bắt lỗi này.

## 5b. Gợi ý mong đợi (theo `metrics-definition.md` mục 5)

| SV | Gợi ý (chủ đề · điểm ưu tiên · lý do) |
|---|---|
| sv01 | Không có (`no_topic_needs_review`): đang tiến bộ, không chủ đề nào thỏa lý do nào |
| sv02 | 1) Đồ thị · 66,7 · điểm thấp + sai nhiều + giảm; 2) Cây nhị phân · 50,7 · cả ba lý do; 3) Sắp xếp và tìm kiếm · 49,5 · sai nhiều + giảm |
| sv03 | Không có (`no_topic_needs_review`): mọi chủ đề đều mạnh |
| sv04 | 1) Đồ thị · 42,7 · sai nhiều + giảm; 2) Ngăn xếp và hàng đợi · 34,2 · sai nhiều. Chủ đề chưa đủ/chưa có dữ liệu không được gợi ý |
| sv05 | 1) Ngăn xếp và hàng đợi · 40,0 · sai nhiều (50%); 2) Đồ thị · 32,0 · sai nhiều (đúng ngưỡng 40,0%) |

## 6. Cách sinh điểm (để giải thích trong báo cáo)

- Mỗi sinh viên có điểm % cơ sở cho từng chủ đề, cộng độ dốc theo tuần (`slope × (tuần − 3)`), cộng nhiễu ngẫu nhiên nhỏ (±2 đến ±4).
- Điểm % đổi thành số câu đúng theo số câu của bài; `score` và `wrong_count` luôn khớp nhau.
- Thời điểm làm bài nằm trong tuần của bài, theo giờ Việt Nam rồi đổi sang UTC. Không có dữ liệu nằm ở tương lai.
- Làm lại bài: lần 2 diễn ra 1–3 ngày sau lần 1.
- Phiên học: 2–4 phiên mỗi tuần, tổng thời lượng theo mức độ chăm chỉ của từng sinh viên (`sv04` ít nhất, `sv03` nhiều nhất).
