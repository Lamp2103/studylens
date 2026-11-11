-- =====================================================================
-- StudyLens – SQLite schema (bản tham chiếu, phiên bản 1.0)
-- Bản chính thức được sinh bằng Alembic từ model SQLAlchemy (W1-B3).
-- File này dùng để: đọc, đối chiếu với model, và chạy thử nhanh:
--     sqlite3 studylens.db < schema.sql
--
-- Quy ước:
--   * Thời gian lưu dạng chuỗi ISO 8601 UTC: 2026-11-09T08:30:00.000Z
--     (so sánh chuỗi cho kết quả đúng thứ tự thời gian).
--   * Ngày lưu dạng YYYY-MM-DD.
--   * Boolean lưu INTEGER 0/1.
--   * Điểm lưu điểm thô (score). Phần trăm = score / max_score * 100
--     được TÍNH khi truy vấn, không lưu để tránh sai lệch (NFR03).
-- =====================================================================

-- BẮT BUỘC chạy ở MỖI kết nối (SQLite mặc định TẮT khóa ngoại).
PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- 1. users – tài khoản sinh viên
-- ---------------------------------------------------------------------
CREATE TABLE users (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    username       TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash  TEXT    NOT NULL,                       -- bcrypt, không lưu mật khẩu thô
    display_name   TEXT    NOT NULL,                       -- tên hiển thị, có thể là biệt danh (NFR07)
    role           TEXT    NOT NULL DEFAULT 'student'
                   CHECK (role IN ('student', 'admin')),
    is_synthetic   INTEGER NOT NULL DEFAULT 1              -- 1 = tài khoản/dữ liệu mô phỏng
                   CHECK (is_synthetic IN (0, 1)),
    is_active      INTEGER NOT NULL DEFAULT 1
                   CHECK (is_active IN (0, 1)),
    created_at     TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    last_login_at  TEXT
);

-- ---------------------------------------------------------------------
-- 2. courses – môn học
-- ---------------------------------------------------------------------
CREATE TABLE courses (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    code         TEXT    NOT NULL UNIQUE,                  -- ví dụ 'DEMO101'
    name         TEXT    NOT NULL,
    description  TEXT,
    start_date   TEXT    NOT NULL,                         -- YYYY-MM-DD, đầu tuần 1
    total_weeks  INTEGER NOT NULL CHECK (total_weeks > 0),
    created_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- ---------------------------------------------------------------------
-- 3. topics – chủ đề kiến thức của một môn
-- ---------------------------------------------------------------------
CREATE TABLE topics (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id    INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    name         TEXT    NOT NULL,
    description  TEXT,
    order_no     INTEGER NOT NULL CHECK (order_no >= 1),   -- thứ tự hiển thị
    UNIQUE (course_id, name),
    UNIQUE (course_id, order_no)
);

-- ---------------------------------------------------------------------
-- 4. assessments – bài tập / bài kiểm tra (một bài thuộc một chủ đề)
--    Số bài của môn = số dòng thuộc các topic của môn → mẫu số của "tiến độ".
-- ---------------------------------------------------------------------
CREATE TABLE assessments (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id         INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    title            TEXT    NOT NULL,
    type             TEXT    NOT NULL DEFAULT 'exercise'
                     CHECK (type IN ('exercise', 'quiz', 'exam')),
    week_no          INTEGER NOT NULL CHECK (week_no >= 1), -- bài thuộc tuần học thứ mấy (FR07)
    total_questions  INTEGER NOT NULL CHECK (total_questions > 0),
    max_score        REAL    NOT NULL DEFAULT 10 CHECK (max_score > 0),
    due_date         TEXT,                                  -- YYYY-MM-DD, có thể để trống
    created_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (topic_id, title)
);

-- ---------------------------------------------------------------------
-- 5. results – một lần làm bài của một sinh viên
--    Cho phép làm lại: (user_id, assessment_id, attempt_no) là duy nhất.
-- ---------------------------------------------------------------------
CREATE TABLE results (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER NOT NULL REFERENCES users(id)       ON DELETE CASCADE,
    assessment_id     INTEGER NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    attempt_no        INTEGER NOT NULL DEFAULT 1 CHECK (attempt_no >= 1),
    score             REAL    NOT NULL CHECK (score >= 0),       -- điểm thô, ≤ max_score (kiểm tra ở API)
    wrong_count       INTEGER NOT NULL CHECK (wrong_count >= 0), -- số câu trả lời sai, ≤ total_questions (kiểm tra ở API)
    started_at        TEXT,
    completed_at      TEXT    NOT NULL,
    duration_seconds  INTEGER CHECK (duration_seconds IS NULL OR duration_seconds >= 0),
    created_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (user_id, assessment_id, attempt_no),
    CHECK (started_at IS NULL OR started_at <= completed_at)
);

-- ---------------------------------------------------------------------
-- 6. study_sessions – phiên học (FR09, giao diện ghi nhận làm sau MVP;
--    bảng và dữ liệu mô phỏng vẫn có để dashboard FR02 hiển thị thời gian học)
-- ---------------------------------------------------------------------
CREATE TABLE study_sessions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER NOT NULL REFERENCES users(id)   ON DELETE CASCADE,
    course_id         INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    topic_id          INTEGER          REFERENCES topics(id)  ON DELETE SET NULL, -- NULL = học chung
    started_at        TEXT    NOT NULL,
    duration_seconds  INTEGER NOT NULL CHECK (duration_seconds > 0 AND duration_seconds <= 86400),
    source            TEXT    NOT NULL DEFAULT 'seed'
                      CHECK (source IN ('seed', 'manual', 'timer')),
    created_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- ---------------------------------------------------------------------
-- 7. recommendations – gợi ý ôn tập (FR05, FR06; status phục vụ FR11)
--    Mỗi lần tính lại, gợi ý cũ đặt is_current = 0, gợi ý mới is_current = 1.
--    evidence_json giữ số liệu làm căn cứ để kiểm tra được lý do (NFR05):
--      {"reasons":[{"code":"low_average","detail":"TB 4.8/10, thấp nhất"}],
--       "metrics":{"avg_pct":48.0,"wrong_total":14,"trend_delta":-12.5}}
-- ---------------------------------------------------------------------
CREATE TABLE recommendations (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id            INTEGER NOT NULL REFERENCES users(id)       ON DELETE CASCADE,
    topic_id           INTEGER NOT NULL REFERENCES topics(id)      ON DELETE CASCADE,
    assessment_id      INTEGER          REFERENCES assessments(id) ON DELETE SET NULL, -- NULL = gợi ý cả chủ đề
    type               TEXT    NOT NULL
                       CHECK (type IN ('review_topic', 'retry_assessment', 'practice_more')),
    rank               INTEGER NOT NULL CHECK (rank >= 1),           -- 1 = ưu tiên cao nhất
    priority_score     REAL    NOT NULL CHECK (priority_score >= 0),
    reason_text        TEXT    NOT NULL,                             -- câu giải thích hiển thị cho sinh viên
    evidence_json      TEXT    NOT NULL
                       CHECK (CASE WHEN json_valid(evidence_json)
                                   THEN COALESCE(json_array_length(evidence_json, '$.reasons'), 0) >= 1
                                   ELSE 0 END),
    resource_url       TEXT,                                         -- tài liệu ôn tập, có thể để trống
    status             TEXT    NOT NULL DEFAULT 'pending'
                       CHECK (status IN ('pending', 'accepted', 'dismissed', 'completed')),
    is_current         INTEGER NOT NULL DEFAULT 1 CHECK (is_current IN (0, 1)),
    generated_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    status_updated_at  TEXT
);

-- ---------------------------------------------------------------------
-- Chỉ mục
-- ---------------------------------------------------------------------
-- Dashboard, kết quả theo chủ đề, lịch sử (FR02, FR03)
CREATE INDEX idx_results_user_completed   ON results (user_id, completed_at);
CREATE INDEX idx_results_assessment       ON results (assessment_id);
-- Gom theo chủ đề và theo tuần (FR03, FR07)
CREATE INDEX idx_assessments_topic_week   ON assessments (topic_id, week_no);
-- (Không cần chỉ mục riêng cho topics.course_id: UNIQUE (course_id, name) đã tạo sẵn chỉ mục.)
-- Thời gian học theo tuần (FR02, FR09)
CREATE INDEX idx_sessions_user_started    ON study_sessions (user_id, started_at);
-- Lấy gợi ý hiện hành theo thứ tự ưu tiên (FR05)
CREATE INDEX idx_recs_user_current_rank   ON recommendations (user_id, is_current, rank);
-- Mỗi sinh viên chỉ có một gợi ý hiện hành cho cùng (chủ đề, loại, bài)
CREATE UNIQUE INDEX uq_recs_current
    ON recommendations (user_id, topic_id, type, COALESCE(assessment_id, 0))
    WHERE is_current = 1;
