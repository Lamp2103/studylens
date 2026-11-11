# Định nghĩa chỉ số – StudyLens

> Công việc W1-B6 · Phiên bản 0.1 (bản nháp) · Trạng thái: **chờ hai thành viên xác nhận các điểm ở mục 9**
> Nguồn: bảng quy tắc nhóm đã chốt (xem cột "Nguồn" ở mục 3) và các đề xuất bổ sung do bản nháp này đưa ra.
> Bản cài đặt tham chiếu: `backend/tests/reference_metrics.py` · Hợp đồng API: [`openapi.yaml`](./openapi.yaml)

## 1. Cách dùng tài liệu này

Đây là **nguồn sự thật duy nhất** về cách tính mọi con số hiển thị trên StudyLens. Mã trong `backend/app/analytics/` (làm ở tuần 2–3) phải cho kết quả **giống hệt** bản tham chiếu trên dữ liệu mô phỏng.

Khi muốn đổi một quy tắc, làm theo thứ tự: sửa tài liệu này → sửa bản tham chiếu → sửa test → sửa mã. Không sửa ngược lại.

Những chỗ bảng quy tắc ban đầu chưa nói rõ đã được chọn một cách hiểu và liệt kê ở **mục 9** để hai bạn xác nhận.

## 2. Quy ước chung

| Quy ước | Nội dung |
|---|---|
| **Lần làm được tính** | Với mỗi (sinh viên, bài), chỉ **lần làm gần nhất** (`attempt_no` lớn nhất) được tính vào mọi chỉ số. Các lần cũ chỉ dùng để hiển thị lịch sử. Lần làm lại thấp hơn lần trước vẫn là lần được tính. |
| **Điểm % của một bài** | `score / max_score × 100` |
| **Làm tròn** | **1 chữ số thập phân, half-up** (74,95 → 75,0; không dùng làm tròn chẵn). Trước khi làm tròn, loại nhiễu số thực bằng `round(x, 9)`. Cài đặt: `Decimal(str(round(x, 9)))` rồi `quantize(0.1, ROUND_HALF_UP)`. |
| **So sánh ngưỡng** | Luôn so **giá trị đã làm tròn**, và tính chênh lệch bằng hiệu của hai số đã làm tròn (dùng `Decimal`, không dùng `float`). Nhờ vậy số hiển thị và nhãn luôn khớp nhau (NFR05) và `74,99999…` không bao giờ làm rơi nhãn. |
| **Không có dữ liệu** | Trả `null`, **không phải 0**. Điểm 0 là điểm thật (chủ đề yếu), khác hẳn "chưa làm bài". |
| **Múi giờ** | CSDL lưu UTC. "Hôm nay" và các tuần của môn tính theo **giờ Việt Nam (UTC+7)**, vì `courses.start_date` là ngày địa phương. |
| **Phạm vi** | Mọi chỉ số tính cho sinh viên đang đăng nhập, trên môn học duy nhất của MVP. |
| **Kết quả luôn thuộc bài đã giao** | API từ chối ghi kết quả cho bài chưa giao (409), nên không có trường hợp kết quả của bài chưa giao. |

## 3. Tham số

Đặt trong `backend/app/analytics/constants.py`. Không rải con số này khắp mã nguồn.

| Hằng số | Giá trị | Ý nghĩa | Nguồn |
|---|---|---|---|
| `STRONG_MIN_PCT` | 75 | Từ mức này trở lên: chủ đề **mạnh** | Nhóm chốt |
| `MEDIUM_MIN_PCT` | 50 | Từ mức này đến dưới 75: **trung bình**; dưới 50: **yếu** | Nhóm chốt |
| `MIN_ASSESSMENTS_FOR_LABEL` | 2 | Dưới số bài này thì "chưa đủ dữ liệu" | Nhóm chốt |
| `WEEK_TREND_THRESHOLD` | 5 | Chênh điểm % giữa hai tuần để gọi là tăng/giảm | Nhóm chốt |
| `TOPIC_TREND_THRESHOLD` | 10 | Như trên nhưng cho xu hướng **theo chủ đề** | **Đề xuất mới** (mục 9, điểm 7) |
| `WRONG_RATE_TRIGGER` | 40 | Tỷ lệ câu sai (%) từ mức này trở lên thì thêm lý do `many_wrong_answers` | **Đề xuất mới** (điểm 8) |
| `W_LOW_AVERAGE` | 0,5 | Trọng số thành phần điểm thấp trong điểm ưu tiên | **Đề xuất mới** (điểm 9) |
| `W_WRONG` | 0,3 | Trọng số thành phần câu sai | **Đề xuất mới** (điểm 9) |
| `W_DECLINE` | 0,2 | Trọng số thành phần xu hướng giảm | **Đề xuất mới** (điểm 9) |
| `DECLINE_CAP` | 30 | Mức giảm (điểm %) tối đa được tính vào điểm ưu tiên | **Đề xuất mới** (điểm 9) |
| `MAX_RECOMMENDATIONS` | 5 | Số gợi ý tối đa trả về | **Đề xuất mới** |

## 4. Các chỉ số

### 4.1 Tuần hiện tại

```
ngày_đã_qua = hôm_nay − courses.start_date          (đơn vị: ngày)
tuần_hiện_tại = 0                                    nếu ngày_đã_qua < 0   (môn chưa bắt đầu)
              = min(ngày_đã_qua // 7 + 1, total_weeks)   nếu không
```

| Hôm nay (môn bắt đầu 12/10/2026, 6 tuần) | Tuần hiện tại |
|---|---|
| 11/10/2026 | 0 (chưa bắt đầu) |
| 12/10/2026 đến 18/10/2026 | 1 |
| 19/10/2026 | 2 |
| 12/11/2026 (cách 31 ngày) | 5 |
| Sau khi môn kết thúc | 6 (không vượt `total_weeks`) |

### 4.2 Điểm trung bình của chủ đề (`avg_pct`)

Trung bình cộng đơn giản của điểm % các **bài đã làm** trong chủ đề (mỗi bài một phiếu, không phụ thuộc số câu). Chủ đề chưa làm bài nào: `null`.

### 4.3 Nhãn chủ đề (`label`)

Kiểm tra theo thứ tự, dừng ở điều kiện đầu tiên đúng:

| Thứ tự | Điều kiện | Nhãn |
|---|---|---|
| 1 | 0 bài đã làm | `no_data` ("chưa có dữ liệu") |
| 2 | 1 bài đã làm (`< MIN_ASSESSMENTS_FOR_LABEL`) | `insufficient` ("chưa đủ dữ liệu") |
| 3 | `avg_pct ≥ 75` | `strong` |
| 4 | `avg_pct ≥ 50` | `medium` |
| 5 | còn lại | `weak` |

`avg_pct` ở đây là giá trị đã làm tròn (mục 2). Các ca biên đã có test:

| avg_pct (chưa làm tròn) | Số bài | Nhãn | Ghi chú |
|---|---|---|---|
| 75,0 | 2 | strong | Đúng ngưỡng: "từ 75% trở lên" |
| 74,96 | 2 | **strong** | Hiển thị 75,0 nên nhãn là mạnh |
| 74,94 | 2 | medium | |
| 50,0 | 2 | medium | Đúng ngưỡng: "từ 50% đến dưới 75%" |
| 49,95 | 2 | medium | Hiển thị 50,0 |
| 49,94 | 2 | weak | |
| 0,0 | 2 | weak | Điểm 0 là dữ liệu thật |
| 95,0 | 1 | insufficient | Ít hơn 2 bài, dù điểm cao |

### 4.4 Tỷ lệ câu sai (`wrong_rate_pct`)

```
wrong_total     = Σ wrong_count      của các bài đã làm (lần làm gần nhất)
total_questions = Σ total_questions  của các bài đã làm
wrong_rate_pct  = wrong_total / total_questions × 100      (null nếu total_questions = 0)
```

Tính theo **số câu**, nên khác `100 − avg_pct` khi các bài có số câu khác nhau (bài tập 10 câu, quiz 20 câu): bài dài có trọng số lớn hơn.

### 4.5 Tiến độ hoàn thành (`completion`)

```
assigned = số bài có week_no ≤ tuần_hiện_tại            (mọi chủ đề)
done     = số bài trong tập "assigned" có ít nhất một lần làm
pct      = done / assigned × 100                        (null nếu assigned = 0)
```

Cùng định nghĩa này áp dụng cho từng chủ đề (`assessments_done`, `assessments_assigned`). Bài tuần sau tuần hiện tại không nằm trong mẫu số.

### 4.6 Điểm trung bình theo tuần và xu hướng theo tuần (`trend`)

```
avg_tuần(w) = trung bình điểm % các bài đã làm có week_no = w          (r1)
```

Kết quả được xếp vào **tuần giao của bài** (`assessments.week_no`), không phải ngày nộp.

Xu hướng so **hai tuần gần nhất có dữ liệu**:

```
tuần_gần_nhất, tuần_trước = hai tuần lớn nhất trong các tuần có dữ liệu
delta = avg_tuần(tuần_gần_nhất) − avg_tuần(tuần_trước)       (hiệu của hai số đã làm tròn)
```

| Điều kiện | `status` |
|---|---|
| Có ít hơn 2 tuần có dữ liệu | `insufficient` (`delta_pct = null`) |
| `delta ≥ +5` | `up` |
| `delta ≤ −5` | `down` |
| còn lại | `stable` |

Chênh **đúng** ±5 được tính là tăng/giảm ("từ ±5 trở lên"). Đây là xu hướng của **cả môn** (hiển thị ở dashboard và trang tiến bộ theo tuần).

### 4.7 Xu hướng theo chủ đề (`topic trend`)

Dùng cho lý do `declining_trend` của gợi ý. Vì mỗi chủ đề chỉ có khoảng một bài mỗi tuần nên so theo bài thay vì theo tuần:

```
Xếp các bài đã làm của chủ đề theo (week_no, assessment_id).
Cần ≥ 2 bài, nếu không: status = insufficient.
delta = điểm%(bài cuối) − điểm%(bài liền trước)        (cả hai đã làm tròn)
```

Ngưỡng là `TOPIC_TREND_THRESHOLD = 10`, **lớn hơn** ngưỡng 5 của xu hướng tuần. Lý do: mỗi bài chỉ có 10 hoặc 20 câu nên điểm nhảy theo bậc 10% hoặc 5%; một câu làm sai thêm đã đủ tạo ra chênh 5 điểm, nên ngưỡng 5 bắt nhầm nhiễu. Thử trên dữ liệu mô phỏng: với ngưỡng 5, `sv05` (điểm ổn định, không có chủ đề yếu) nhận 4 gợi ý; với ngưỡng 10, chỉ còn 2 gợi ý, đều do tỷ lệ sai cao.

### 4.8 Điểm trung bình tổng (`average_pct`)

Trung bình cộng điểm % của **mọi bài đã làm** (mỗi bài một phiếu). Không phải trung bình của các điểm trung bình chủ đề: hai cách cho kết quả khác nhau khi các chủ đề có số bài khác nhau. `null` nếu chưa làm bài nào.

### 4.9 Thời gian học (`study_time`)

```
total_minutes        = (Σ duration_seconds của mọi phiên học) // 60
current_week_minutes = (Σ duration_seconds của các phiên có started_at nằm trong tuần hiện tại) // 60
```

Tuần hiện tại bắt đầu từ 00:00 thứ Hai theo giờ Việt Nam. Cộng giây trước rồi mới chia, không cộng các số phút đã làm tròn. Ở MVP dữ liệu này là dữ liệu mô phỏng (FR09 làm sau).

### 4.10 Chủ đề thấp nhất, cao nhất; đếm theo nhãn

- `lowest_topic` / `highest_topic`: trong các chủ đề có nhãn `strong`, `medium`, `weak` (đủ dữ liệu), chủ đề có `avg_pct` nhỏ nhất / lớn nhất. Bằng điểm thì chủ đề có `order_no` nhỏ hơn thắng (cả hai trường hợp). `null` nếu chưa chủ đề nào đủ dữ liệu.
- `label_counts`: số chủ đề theo từng nhãn; tổng luôn bằng số chủ đề của môn.

## 5. Gợi ý ôn tập (FR05, FR06)

### 5.1 Chủ đề nào được xét, và vì sao

Chỉ xét chủ đề có nhãn `strong`, `medium` hoặc `weak`. Chủ đề `insufficient` và `no_data` **không** được gợi ý vì chưa đủ bằng chứng.

Một chủ đề được gợi ý khi thỏa **ít nhất một** lý do:

| Mã lý do | Điều kiện | Ý nghĩa |
|---|---|---|
| `low_average` | nhãn là `weak` (`avg_pct < 50`) | Điểm trung bình thấp |
| `many_wrong_answers` | `wrong_rate_pct ≥ 40` | Sai nhiều câu |
| `declining_trend` | xu hướng chủ đề là `down` **và** nhãn khác `strong` | Đang đi xuống |

Chủ đề `strong` không được gợi ý vì xu hướng giảm: một chủ đề đang đạt 85% không cần ôn gấp chỉ vì giảm vài điểm. (Ví dụ: nếu dùng ngưỡng 5 điểm và chưa có quy tắc này, `sv03` có điểm 80–92% ở mọi chủ đề vẫn nhận một gợi ý chỉ vì một bài giảm 5 điểm.)

### 5.2 Điểm ưu tiên

```
A = 100 − avg_pct                                     (thành phần "điểm thấp")
W = wrong_rate_pct                                    (thành phần "câu sai")
D = min(−delta, 30) / 30 × 100   nếu có lý do declining_trend, ngược lại 0
priority_score = làm tròn( 0,5 × A + 0,3 × W + 0,2 × D )
```

Điểm ưu tiên nằm trong 0–100. Lưu ý `A` và `W` cùng đo độ chính xác (`A` tính theo bài, `W` tính theo câu) nên trọng số thực tế dành cho "làm sai" là 0,8; hai bạn có thể gộp lại nếu thấy trùng lặp (mục 9, điểm 9).

### 5.3 Xếp hạng

Sắp theo `priority_score` giảm dần. Bằng điểm thì `avg_pct` thấp hơn xếp trước; vẫn bằng thì `order_no` nhỏ hơn xếp trước. Lấy tối đa `MAX_RECOMMENDATIONS = 5` gợi ý; `rank` là 1, 2, 3...

### 5.4 Câu giải thích (`reason_text`, `reasons[].detail`)

Mỗi lý do sinh một câu, **chỉ chứa số liệu có trong dữ liệu** (NFR05). `reason_text` là các câu ghép bằng một dấu cách, theo thứ tự bên dưới. Số hiển thị dùng dấu phẩy thập phân kiểu Việt Nam và bỏ ",0" thừa (45,0 → `45`; 78,3 → `78,3`).

| Mã | Mẫu câu |
|---|---|
| `low_average` | `Điểm trung bình của chủ đề là {avg}%, thuộc mức yếu (dưới 50%).` |
| `many_wrong_answers` | `Bạn trả lời sai {wrong_total}/{total_questions} câu ({wrong_rate}%) ở các bài đã làm.` |
| `declining_trend` | `Bài gần nhất ({title}) đạt {latest}%, giảm {abs(delta)} điểm % so với bài trước ({previous}%).` |

### 5.5 Dữ liệu căn cứ (`evidence_json`)

Lưu cùng gợi ý để kiểm chứng sau này; CSDL bắt buộc có ít nhất một lý do. Khuôn dạng trùng với `reasons` và `metrics` trong API:

```json
{
  "reasons": [
    {"code": "low_average", "detail": "Điểm trung bình của chủ đề là 25%, thuộc mức yếu (dưới 50%)."}
  ],
  "metrics": {
    "avg_pct": 25.0, "done": 2, "wrong_total": 15, "total_questions": 20, "wrong_rate_pct": 75.0,
    "trend": {"status": "down", "delta_pct": -10.0, "latest_pct": 20.0, "previous_pct": 30.0}
  }
}
```

### 5.6 Vòng đời

1. `GET /recommendations`: nếu sinh viên chưa có gợi ý hiện hành (`is_current = 1`) nào thì tính, lưu, rồi trả.
2. `POST /results`: trong **cùng một giao dịch**, lưu kết quả, đặt gợi ý cũ `is_current = 0`, chèn gợi ý mới. Lịch sử gợi ý cũ được giữ.
3. Bản MVP chỉ sinh loại `review_topic`, `status` luôn là `pending`, `resource_url` luôn `null`. Hai loại `retry_assessment`, `practice_more` và việc đổi `status` (FR11) để dành.

### 5.7 Khi không có gợi ý (`empty_reason`)

| Tình huống | `empty_reason` |
|---|---|
| Có ít nhất một chủ đề đủ dữ liệu nhưng không chủ đề nào thỏa lý do nào | `no_topic_needs_review` |
| Chưa chủ đề nào đủ dữ liệu (mọi chủ đề là `insufficient` hoặc `no_data`) | `insufficient_data` |
| Có gợi ý | `null` |

## 6. Các trường hợp biên

| Tình huống | Kết quả |
|---|---|
| Sinh viên chưa làm bài nào | `average_pct = null`; tiến độ `0/assigned`; xu hướng `insufficient`; mọi chủ đề `no_data`; gợi ý rỗng với `insufficient_data` |
| Môn chưa bắt đầu (tuần 0) | `assigned = 0` nên `completion.pct = null`; mọi tuần là `future` |
| Môn đã kết thúc | Tuần hiện tại = `total_weeks`; mọi bài đều đã giao |
| Chỉ có dữ liệu của một tuần | Xu hướng tuần `insufficient` |
| Sinh viên bỏ trống một tuần giữa chừng | Xu hướng so hai tuần **có dữ liệu** gần nhất, không nhất thiết là hai tuần liền kề |
| Làm lại bài và điểm thấp hơn lần trước | Lần làm gần nhất vẫn là lần được tính |
| Điểm 0 | Điểm thật; chủ đề thành `weak` nếu đủ 2 bài |
| Hai bài cùng chủ đề cùng tuần | Sắp theo `assessment_id` khi xác định "bài gần nhất" |
| `total_questions = 0` hoặc `assigned = 0` | Không chia; trả `null` |
| Ghi kết quả cho bài chưa giao | API trả 409 `assessment_not_assigned` |

## 7. Ví dụ tính tay (dữ liệu mô phỏng, hạt giống mặc định)

### 7.1 `sv02` – chủ đề "Đồ thị": cả ba lý do cùng xuất hiện

| Bài | Tuần | Điểm | % | Số câu sai |
|---|---|---|---|---|
| Đồ thị – Bài tập 1 | 4 | 3/10 | 30,0 | 7/10 |
| Đồ thị – Bài tập 2 | 5 | 2/10 | 20,0 | 8/10 |

- Điểm TB = (30,0 + 20,0) / 2 = **25,0** → dưới 50 → nhãn `weak` → lý do `low_average`.
- Câu sai = (7 + 8) / (10 + 10) = 15/20 = **75,0%** ≥ 40 → lý do `many_wrong_answers`.
- Xu hướng chủ đề = 20,0 − 30,0 = **−10,0** ≤ −10 và nhãn khác `strong` → `down` → lý do `declining_trend`.
- Điểm ưu tiên: `A = 75`, `W = 75`, `D = min(10, 30)/30 × 100 = 33,333…`
  → 0,5 × 75 + 0,3 × 75 + 0,2 × 33,333 = 37,5 + 22,5 + 6,667 = 66,667 → **66,7** → xếp hạng 1.

Câu giải thích: *"Điểm trung bình của chủ đề là 25%, thuộc mức yếu (dưới 50%). Bạn trả lời sai 15/20 câu (75%) ở các bài đã làm. Bài gần nhất (Đồ thị – Bài tập 2) đạt 20%, giảm 10 điểm % so với bài trước (30%)."*

### 7.2 `sv02` – chủ đề "Sắp xếp và tìm kiếm": ca biên của `many_wrong_answers`

| Bài | Tuần | Điểm | % | Số câu sai |
|---|---|---|---|---|
| Bài tập 1 (10 câu) | 1 | 8/10 | 80,0 | 2/10 |
| Quiz (20 câu) | 5 | 10/20 | 50,0 | 10/20 |

- Điểm TB = (80,0 + 50,0) / 2 = **65,0** → `medium` (không có `low_average`).
- Câu sai = 12/30 = **40,0%**, đúng ngưỡng → có `many_wrong_answers`. (Chú ý: 12/30 chứ không phải `100 − 65 = 35`, vì quiz 20 câu có trọng số lớn hơn.)
- Xu hướng chủ đề = 50,0 − 80,0 = −30,0 → `down` → có `declining_trend`.
- Ưu tiên: `A = 35`, `W = 40`, `D = min(30, 30)/30 × 100 = 100` → 17,5 + 12,0 + 20,0 = **49,5**, xếp hạng 3.

### 7.3 `sv05` – điểm đúng ngưỡng

- "Danh sách liên kết": 70,0 + 80,0 + 75,0 → TB = 225,0 / 3 = **75,0** → `strong` (đúng ngưỡng, tính là mạnh).
- "Ngăn xếp và hàng đợi": 50,0 + 50,0 + 50,0 → TB = **50,0** → `medium` (đúng ngưỡng). Câu sai = 20/40 = 50,0% ≥ 40 → được gợi ý vì `many_wrong_answers`, điểm ưu tiên = 0,5 × 50 + 0,3 × 50 = **40,0**.
- "Đồ thị": 60,0 + 60,0, câu sai = 8/20 = **40,0%** đúng ngưỡng → vẫn được gợi ý; ưu tiên = 0,5 × 40 + 0,3 × 40 = **32,0**.

### 7.4 `sv01` – làm lại bài và xu hướng tuần

- "Ngăn xếp – Bài tập 1": lần 1 được 5/10 (50%), lần 2 được 7/10 (**70%**). Chỉ lần 2 được tính.
- Điểm TB tuần 4 gồm 4 bài: Danh sách liên kết – Quiz 80,0; Ngăn xếp và hàng đợi – Quiz 75,0; Cây nhị phân – Bài tập 2 80,0; Đồ thị – Bài tập 1 60,0 → (80 + 75 + 80 + 60) / 4 = 73,75 → **73,8** (làm tròn half-up).
- Điểm TB tuần 5 gồm 3 bài: Cây nhị phân – Quiz 85,0; Đồ thị – Bài tập 2 70,0; Sắp xếp và tìm kiếm – Quiz 95,0 → 250 / 3 = 83,33 → **83,3**.
- Xu hướng = 83,3 − 73,8 = **+9,5** (hiệu của hai số đã làm tròn; nếu dùng số chưa làm tròn sẽ ra 9,58) ≥ 5 → `up`.

### 7.5 `sv02` – dashboard

- 15 bài đã làm, tổng điểm % là 975,0 → điểm TB tổng = 975,0 / 15 = **65,0**.
- Tiến độ = 15 / 17 = **88,2%** (17 bài đã giao đến tuần 5; bài tuần 6 chưa tính).
- Điểm TB theo tuần: 90,0 / 80,0 / 65,0 / 50,0 / 35,0. Xu hướng = 35,0 − 50,0 = **−15,0** → `down`.

## 8. Bảng ánh xạ hiển thị (frontend)

Máy chủ chỉ trả mã. Chữ hiển thị lấy từ bảng này. Theo NFR11, **không dùng màu làm cách phân biệt duy nhất**: luôn kèm chữ hoặc biểu tượng.

| Mã | Hiển thị |
|---|---|
| `label`: `strong` | Mạnh |
| `label`: `medium` | Trung bình |
| `label`: `weak` | Yếu |
| `label`: `insufficient` | Chưa đủ dữ liệu |
| `label`: `no_data` | Chưa có dữ liệu |
| `trend`: `up` | Tăng |
| `trend`: `down` | Giảm |
| `trend`: `stable` | Ổn định |
| `trend`: `insufficient` | Chưa đủ dữ liệu |
| `state`: `past` / `current` / `future` | Đã qua / Tuần này / Sắp tới |
| `status`: `not_assigned` / `not_done` / `done` | Chưa giao / Chưa làm / Đã làm |
| `empty_reason`: `no_topic_needs_review` | Hiện chưa có chủ đề nào cần ôn gấp. Hãy tiếp tục duy trì! |
| `empty_reason`: `insufficient_data` | Chưa đủ dữ liệu để gợi ý. Hãy làm thêm bài tập. |

Khi `is_synthetic = true`, giao diện phải ghi rõ **"Dữ liệu thử nghiệm"** (NFR07).

## 9. Điểm cần hai bạn xác nhận

**A. Cách hiểu bảng quy tắc ban đầu** (đã dùng trong bản tham chiếu và dữ liệu mô phỏng):

| # | Chỗ chưa rõ | Cách hiểu đang dùng |
|---|---|---|
| 1 | "Tuần gần nhất" và "tuần trước" | Hai tuần gần nhất **có dữ liệu** của sinh viên, không bắt buộc là hai tuần liền kề |
| 2 | Kết quả thuộc tuần nào | Tuần giao của bài (`week_no`), không phải ngày nộp |
| 3 | Xu hướng tuần tính trên đâu | Toàn bộ kết quả của sinh viên, không tính riêng từng chủ đề |
| 4 | "Đã giao đến tuần hiện tại" | Mọi bài có `week_no ≤ tuần hiện tại` |
| 5 | Chênh đúng ±5 điểm % | Tính là tăng/giảm |
| 6 | Điểm đúng 75,0 hoặc 50,0 | 75,0 là mạnh; 50,0 là trung bình |

**B. Đề xuất mới** (bảng quy tắc ban đầu chưa nêu; cần quyết định):

| # | Đề xuất | Vì sao |
|---|---|---|
| 7 | Xu hướng theo **chủ đề** dùng ngưỡng **10** điểm % (xu hướng tuần vẫn là 5) | Điểm mỗi bài nhảy theo bậc 5–10%; ngưỡng 5 bắt nhầm nhiễu (mục 4.7) |
| 8 | Lý do `many_wrong_answers` khi tỷ lệ sai ≥ **40%**; chủ đề **mạnh** không bị gợi ý vì xu hướng giảm; chủ đề chưa đủ dữ liệu không được gợi ý | Tránh gợi ý ôn cho sinh viên đang học tốt (mục 5.1). Con số 40% là ước lượng, cần chỉnh theo thực tế |
| 9 | Trọng số điểm ưu tiên **0,5 / 0,3 / 0,2**, mức giảm tối đa **30** điểm | Chưa có cơ sở dữ liệu thật để hiệu chỉnh; hai thành phần điểm thấp và câu sai cùng đo độ chính xác nên có thể gộp |
| 10 | Làm tròn **trước** khi so với ngưỡng | Số hiển thị khớp nhãn; tránh `74,999…` (mục 2) |
| 11 | Bản MVP chỉ sinh gợi ý `review_topic` | Giảm phạm vi; FR05 vẫn đáp ứng ở mức chủ đề |
| 12 | Điểm trung bình tổng tính theo **bài**, không theo chủ đề | Đơn giản, dễ giải thích (mục 4.8) |

**C. Hợp đồng API** (bàn ở buổi họp W1-C4):

| # | Nội dung | Đề xuất |
|---|---|---|
| 13 | Có tiền tố `/api` không? | Không (khớp danh sách ban đầu); đổi sau sẽ phải sửa cả hai phía |
| 14 | Thêm `GET /auth/me` ngoài danh sách ban đầu | Có, để frontend khôi phục phiên khi tải lại trang |
| 15 | **Đăng xuất (FR12) không thu hồi được token** vì JWT không có trạng thái; token bị lấy trộm vẫn dùng được đến khi hết hạn (mặc định 60 phút) | Chấp nhận ở MVP, frontend xóa token và dữ liệu. Nếu cần thu hồi thật: danh sách token bị thu hồi trong bộ nhớ (mất khi khởi động lại) hoặc thêm bảng CSDL |
| 16 | `POST /results` có buộc `score` khớp `wrong_count` không? | Không, để cho phép chấm điểm từng phần. Dữ liệu mô phỏng thì luôn khớp (điểm = số câu đúng × điểm mỗi câu) |
| 17 | Gợi ý tạo khi nào | Tạo lười khi `GET` lần đầu, tính lại sau mỗi `POST /results` (mục 5.6) |

## 10. Kiểm thử độ chính xác (NFR03)

| Test | Kiểm tra |
|---|---|
| `tests/test_reference_metrics.py` | Các ca biên: làm tròn, nhãn, xu hướng, tuần hiện tại, ngưỡng câu sai, công thức ưu tiên, xếp hạng, và gợi ý mong đợi của 5 sinh viên mô phỏng |
| `tests/test_seed.py` | Dữ liệu mô phỏng cho ra đúng nhãn, tiến độ, xu hướng đã thiết kế |
| `tests/test_openapi_contract.py` | Các file JSON mẫu nhất quán với nhau và với quy tắc trong tài liệu này |

**Khi viết `app/analytics/`:** với từng sinh viên mô phỏng, kết quả của mã thật phải **khớp tuyệt đối** với `reference_metrics.compute()` và `recommend()` (mọi chủ đề, mọi tuần, mọi gợi ý, kể cả chuỗi giải thích). Tiêu chí chấp nhận cho NFR03: không có sai lệch nào.
