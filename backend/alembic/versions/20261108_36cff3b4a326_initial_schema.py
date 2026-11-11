"""initial schema

Revision ID: 36cff3b4a326
Revises: 
Create Date: 2026-11-08 10:53:08.625846

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '36cff3b4a326'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    op.create_table('courses',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('code', sa.Text(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('start_date', sa.Text(), nullable=False),
    sa.Column('total_weeks', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.Text(), server_default=sa.text("(strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))"), nullable=False),
    sa.CheckConstraint('total_weeks > 0', name=op.f('ck_courses_total_weeks_positive')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_courses')),
    sa.UniqueConstraint('code', name=op.f('uq_courses_code')),
    sqlite_autoincrement=True
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('username', sa.Text(collation='NOCASE'), nullable=False),
    sa.Column('password_hash', sa.Text(), nullable=False),
    sa.Column('display_name', sa.Text(), nullable=False),
    sa.Column('role', sa.Text(), server_default='student', nullable=False),
    sa.Column('is_synthetic', sa.Boolean(create_constraint=True, name='is_synthetic_bool'), server_default=sa.text('1'), nullable=False),
    sa.Column('is_active', sa.Boolean(create_constraint=True, name='is_active_bool'), server_default=sa.text('1'), nullable=False),
    sa.Column('created_at', sa.Text(), server_default=sa.text("(strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))"), nullable=False),
    sa.Column('last_login_at', sa.Text(), nullable=True),
    sa.CheckConstraint("role IN ('student', 'admin')", name=op.f('ck_users_role')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('username', name=op.f('uq_users_username')),
    sqlite_autoincrement=True
    )
    op.create_table('topics',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('course_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('order_no', sa.Integer(), nullable=False),
    sa.CheckConstraint('order_no >= 1', name=op.f('ck_topics_order_no_min')),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], name=op.f('fk_topics_course_id_courses'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_topics')),
    sa.UniqueConstraint('course_id', 'name', name='uq_topics_course_name'),
    sa.UniqueConstraint('course_id', 'order_no', name='uq_topics_course_order'),
    sqlite_autoincrement=True
    )
    op.create_table('assessments',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('topic_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.Text(), nullable=False),
    sa.Column('type', sa.Text(), server_default='exercise', nullable=False),
    sa.Column('week_no', sa.Integer(), nullable=False),
    sa.Column('total_questions', sa.Integer(), nullable=False),
    sa.Column('max_score', sa.REAL(), server_default=sa.text('(10)'), nullable=False),
    sa.Column('due_date', sa.Text(), nullable=True),
    sa.Column('created_at', sa.Text(), server_default=sa.text("(strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))"), nullable=False),
    sa.CheckConstraint("type IN ('exercise', 'quiz', 'exam')", name=op.f('ck_assessments_type')),
    sa.CheckConstraint('max_score > 0', name=op.f('ck_assessments_max_score_positive')),
    sa.CheckConstraint('total_questions > 0', name=op.f('ck_assessments_total_questions_positive')),
    sa.CheckConstraint('week_no >= 1', name=op.f('ck_assessments_week_no_min')),
    sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], name=op.f('fk_assessments_topic_id_topics'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_assessments')),
    sa.UniqueConstraint('topic_id', 'title', name='uq_assessments_topic_title'),
    sqlite_autoincrement=True
    )
    with op.batch_alter_table('assessments', schema=None) as batch_op:
        batch_op.create_index('idx_assessments_topic_week', ['topic_id', 'week_no'], unique=False)

    op.create_table('study_sessions',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('course_id', sa.Integer(), nullable=False),
    sa.Column('topic_id', sa.Integer(), nullable=True),
    sa.Column('started_at', sa.Text(), nullable=False),
    sa.Column('duration_seconds', sa.Integer(), nullable=False),
    sa.Column('source', sa.Text(), server_default='seed', nullable=False),
    sa.Column('created_at', sa.Text(), server_default=sa.text("(strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))"), nullable=False),
    sa.CheckConstraint("source IN ('seed', 'manual', 'timer')", name=op.f('ck_study_sessions_source')),
    sa.CheckConstraint('duration_seconds > 0 AND duration_seconds <= 86400', name=op.f('ck_study_sessions_duration_range')),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], name=op.f('fk_study_sessions_course_id_courses'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], name=op.f('fk_study_sessions_topic_id_topics'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_study_sessions_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_study_sessions')),
    sqlite_autoincrement=True
    )
    with op.batch_alter_table('study_sessions', schema=None) as batch_op:
        batch_op.create_index('idx_sessions_user_started', ['user_id', 'started_at'], unique=False)

    op.create_table('recommendations',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('topic_id', sa.Integer(), nullable=False),
    sa.Column('assessment_id', sa.Integer(), nullable=True),
    sa.Column('type', sa.Text(), nullable=False),
    sa.Column('rank', sa.Integer(), nullable=False),
    sa.Column('priority_score', sa.REAL(), nullable=False),
    sa.Column('reason_text', sa.Text(), nullable=False),
    sa.Column('evidence_json', sa.Text(), nullable=False),
    sa.Column('resource_url', sa.Text(), nullable=True),
    sa.Column('status', sa.Text(), server_default='pending', nullable=False),
    sa.Column('is_current', sa.Boolean(create_constraint=True, name='is_current_bool'), server_default=sa.text('1'), nullable=False),
    sa.Column('generated_at', sa.Text(), server_default=sa.text("(strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))"), nullable=False),
    sa.Column('status_updated_at', sa.Text(), nullable=True),
    sa.CheckConstraint("CASE WHEN json_valid(evidence_json) THEN COALESCE(json_array_length(evidence_json, '$.reasons'), 0) >= 1 ELSE 0 END", name=op.f('ck_recommendations_evidence_has_reason')),
    sa.CheckConstraint("status IN ('pending', 'accepted', 'dismissed', 'completed')", name=op.f('ck_recommendations_status')),
    sa.CheckConstraint("type IN ('review_topic', 'retry_assessment', 'practice_more')", name=op.f('ck_recommendations_type')),
    sa.CheckConstraint('priority_score >= 0', name=op.f('ck_recommendations_priority_score_min')),
    sa.CheckConstraint('rank >= 1', name=op.f('ck_recommendations_rank_min')),
    sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], name=op.f('fk_recommendations_assessment_id_assessments'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], name=op.f('fk_recommendations_topic_id_topics'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_recommendations_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_recommendations')),
    sqlite_autoincrement=True
    )
    with op.batch_alter_table('recommendations', schema=None) as batch_op:
        batch_op.create_index('idx_recs_user_current_rank', ['user_id', 'is_current', 'rank'], unique=False)

    op.create_table('results',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('assessment_id', sa.Integer(), nullable=False),
    sa.Column('attempt_no', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('score', sa.REAL(), nullable=False),
    sa.Column('wrong_count', sa.Integer(), nullable=False),
    sa.Column('started_at', sa.Text(), nullable=True),
    sa.Column('completed_at', sa.Text(), nullable=False),
    sa.Column('duration_seconds', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.Text(), server_default=sa.text("(strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))"), nullable=False),
    sa.CheckConstraint('attempt_no >= 1', name=op.f('ck_results_attempt_no_min')),
    sa.CheckConstraint('duration_seconds IS NULL OR duration_seconds >= 0', name=op.f('ck_results_duration_seconds_min')),
    sa.CheckConstraint('score >= 0', name=op.f('ck_results_score_min')),
    sa.CheckConstraint('started_at IS NULL OR started_at <= completed_at', name=op.f('ck_results_time_order')),
    sa.CheckConstraint('wrong_count >= 0', name=op.f('ck_results_wrong_count_min')),
    sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], name=op.f('fk_results_assessment_id_assessments'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_results_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_results')),
    sa.UniqueConstraint('user_id', 'assessment_id', 'attempt_no', name='uq_results_user_assessment_attempt'),
    sqlite_autoincrement=True
    )
    with op.batch_alter_table('results', schema=None) as batch_op:
        batch_op.create_index('idx_results_assessment', ['assessment_id'], unique=False)
        batch_op.create_index('idx_results_user_completed', ['user_id', 'completed_at'], unique=False)


    # Autogenerate bỏ qua chỉ mục dùng biểu thức (SQLite không đọc lại được), nên thêm tay.
    # Mỗi sinh viên chỉ có MỘT gợi ý hiện hành cho cùng (chủ đề, loại, bài).
    op.create_index(
        "uq_recs_current",
        "recommendations",
        ["user_id", "topic_id", "type", sa.text("COALESCE(assessment_id, 0)")],
        unique=True,
        sqlite_where=sa.text("is_current = 1"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    
    op.drop_index("uq_recs_current", table_name="recommendations")
    with op.batch_alter_table('results', schema=None) as batch_op:
        batch_op.drop_index('idx_results_user_completed')
        batch_op.drop_index('idx_results_assessment')

    op.drop_table('results')
    with op.batch_alter_table('recommendations', schema=None) as batch_op:
        batch_op.drop_index('idx_recs_user_current_rank')

    op.drop_table('recommendations')
    with op.batch_alter_table('study_sessions', schema=None) as batch_op:
        batch_op.drop_index('idx_sessions_user_started')

    op.drop_table('study_sessions')
    with op.batch_alter_table('assessments', schema=None) as batch_op:
        batch_op.drop_index('idx_assessments_topic_week')

    op.drop_table('assessments')
    op.drop_table('topics')
    op.drop_table('users')
    op.drop_table('courses')
