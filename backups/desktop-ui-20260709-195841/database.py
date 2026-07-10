from __future__ import annotations

import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "university_tracker.sqlite"


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    professor TEXT NOT NULL DEFAULT '',
    teacher_email TEXT NOT NULL DEFAULT '',
    schedule TEXT NOT NULL DEFAULT '',
    semester INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'studying', 'seen')),
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS grade_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    weight REAL NOT NULL CHECK (weight >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
    UNIQUE(subject_id, name)
);

CREATE TABLE IF NOT EXISTS homework (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL,
    category_id INTEGER,
    title TEXT NOT NULL,
    due_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'in progress', 'submitted', 'graded')),
    grade REAL CHECK (grade IS NULL OR (grade >= 1.0 AND grade <= 5.0)),
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES grade_categories(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS grades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL,
    assessment_name TEXT NOT NULL,
    assessment_type TEXT NOT NULL CHECK (
        assessment_type IN ('exam', 'quiz', 'homework', 'project', 'participation', 'other')
    ),
    weight REAL NOT NULL CHECK (weight >= 0),
    grade REAL NOT NULL CHECK (grade >= 1.0 AND grade <= 5.0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);
"""


SEED_SQL = """
INSERT INTO subjects (name, professor, teacher_email, schedule, semester)
VALUES
    ('Calculus I', 'Dr. Rivera', 'rivera@example.edu', 'Mon/Wed 8:00 AM', 2),
    ('Programming Fundamentals', 'Prof. Gomez', 'gomez@example.edu', 'Tue/Thu 10:00 AM', 1),
    ('Academic Writing', 'Prof. Martinez', 'martinez@example.edu', 'Friday 2:00 PM', 1);

INSERT INTO grade_categories (subject_id, name, weight)
VALUES
    (1, 'Exams', 50),
    (1, 'Problem sets', 30),
    (1, 'Quizzes', 20),
    (2, 'Programming', 40),
    (2, 'Quizzes', 25),
    (2, 'Final project', 35),
    (3, 'Essays', 60),
    (3, 'Participation', 20),
    (3, 'Final portfolio', 20);

INSERT INTO topics (subject_id, name, status, notes)
VALUES
    (1, 'Limits and continuity', 'studying', 'Review epsilon-delta examples.'),
    (1, 'Derivatives', 'pending', ''),
    (2, 'Python functions', 'seen', 'Practice with small exercises.'),
    (2, 'Lists and dictionaries', 'studying', ''),
    (3, 'Essay structure', 'seen', 'Keep intro and thesis concise.');

INSERT INTO homework (subject_id, category_id, title, due_date, status, grade, notes)
VALUES
    (1, 2, 'Problem set 2', date('now', '+3 days'), 'pending', NULL, 'Exercises 1-20.'),
    (2, 4, 'Mini project proposal', date('now', '+5 days'), 'in progress', NULL, 'Describe app idea and data model.'),
    (3, 7, 'Essay draft', date('now', '+8 days'), 'submitted', NULL, 'Waiting for feedback.');

INSERT INTO grades (subject_id, assessment_name, assessment_type, weight, grade)
VALUES
    (1, 'Quiz 1', 'quiz', 10, 4.2),
    (1, 'Homework 1', 'homework', 15, 4.5),
    (2, 'Lab 1', 'homework', 10, 4.8),
    (2, 'Quiz 1', 'quiz', 10, 4.6),
    (3, 'Essay outline', 'project', 20, 4.4);
"""


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(db_path: Path = DB_PATH) -> None:
    with connect(db_path) as connection:
        connection.executescript(SCHEMA)
        migrate_schema(connection)
        subject_count = connection.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
        if subject_count == 0:
            connection.executescript(SEED_SQL)
        ensure_default_categories(connection)


def migrate_schema(connection: sqlite3.Connection) -> None:
    subject_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(subjects)").fetchall()
    }
    if "semester" not in subject_columns:
        connection.execute("ALTER TABLE subjects ADD COLUMN semester INTEGER NOT NULL DEFAULT 1")
        connection.execute("UPDATE subjects SET semester = 2 WHERE lower(name) LIKE 'calculus i%'")
    if "teacher_email" not in subject_columns:
        connection.execute("ALTER TABLE subjects ADD COLUMN teacher_email TEXT NOT NULL DEFAULT ''")

    topic_sql = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'topics'"
    ).fetchone()
    if topic_sql and "'not started'" in topic_sql["sql"]:
        connection.executescript(
            """
            PRAGMA foreign_keys = OFF;
            DROP TABLE IF EXISTS topics_new;
            CREATE TABLE topics_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('pending', 'studying', 'seen')),
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );
            INSERT INTO topics_new (id, subject_id, name, status, notes, created_at)
            SELECT
                id,
                subject_id,
                name,
                CASE
                    WHEN status = 'not started' THEN 'pending'
                    WHEN status = 'done' THEN 'seen'
                    ELSE status
                END,
                notes,
                created_at
            FROM topics;
            DROP TABLE topics;
            ALTER TABLE topics_new RENAME TO topics;
            PRAGMA foreign_keys = ON;
            """
        )

    homework_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(homework)").fetchall()
    }
    if "category_id" not in homework_columns:
        connection.execute(
            "ALTER TABLE homework ADD COLUMN category_id INTEGER REFERENCES grade_categories(id) ON DELETE SET NULL"
        )


def ensure_default_categories(connection: sqlite3.Connection) -> None:
    subjects = connection.execute("SELECT id, name FROM subjects").fetchall()
    for subject in subjects:
        category_count = connection.execute(
            "SELECT COUNT(*) FROM grade_categories WHERE subject_id = ?",
            (subject["id"],),
        ).fetchone()[0]
        if category_count == 0:
            connection.executemany(
                "INSERT INTO grade_categories (subject_id, name, weight) VALUES (?, ?, ?)",
                [
                    (subject["id"], "Exams", 50),
                    (subject["id"], "Homework", 30),
                    (subject["id"], "Participation", 20),
                ],
            )

        first_category = connection.execute(
            """
            SELECT id FROM grade_categories
            WHERE subject_id = ?
            ORDER BY id
            LIMIT 1
            """,
            (subject["id"],),
        ).fetchone()
        if first_category:
            connection.execute(
                """
                UPDATE homework
                SET category_id = ?
                WHERE subject_id = ? AND category_id IS NULL
                """,
                (first_category["id"], subject["id"]),
            )


def fetch_all(table: str) -> list[sqlite3.Row]:
    if table not in {"subjects", "topics", "homework", "grades", "grade_categories"}:
        raise ValueError(f"Unsupported table: {table}")
    with connect() as connection:
        return list(connection.execute(f"SELECT * FROM {table} ORDER BY id DESC"))


def validate_grade(grade: float | None) -> None:
    if grade is not None and not 1.0 <= grade <= 5.0:
        raise ValueError("Grades must be between 1.0 and 5.0.")


def fetch_subjects() -> list[sqlite3.Row]:
    with connect() as connection:
        return list(connection.execute("SELECT * FROM subjects ORDER BY semester, name"))


def add_subject(name: str, professor: str, teacher_email: str, schedule: str, semester: int) -> None:
    with connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO subjects (name, professor, teacher_email, schedule, semester)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name.strip(), professor.strip(), teacher_email.strip(), schedule.strip(), semester),
        )
        subject_id = cursor.lastrowid
        connection.executemany(
            "INSERT INTO grade_categories (subject_id, name, weight) VALUES (?, ?, ?)",
            [
                (subject_id, "Exams", 50),
                (subject_id, "Homework", 30),
                (subject_id, "Participation", 20),
            ],
        )


def update_subject(
    subject_id: int,
    name: str,
    professor: str,
    teacher_email: str,
    schedule: str,
    semester: int,
) -> None:
    with connect() as connection:
        connection.execute(
            """
            UPDATE subjects
            SET name = ?, professor = ?, teacher_email = ?, schedule = ?, semester = ?
            WHERE id = ?
            """,
            (name.strip(), professor.strip(), teacher_email.strip(), schedule.strip(), semester, subject_id),
        )


def delete_subject(subject_id: int) -> None:
    with connect() as connection:
        connection.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))


def fetch_categories(subject_id: int | None = None) -> list[sqlite3.Row]:
    with connect() as connection:
        if subject_id is None:
            return list(
                connection.execute(
                    """
                    SELECT grade_categories.*, subjects.name AS subject_name
                    FROM grade_categories
                    JOIN subjects ON subjects.id = grade_categories.subject_id
                    ORDER BY subjects.name, grade_categories.name
                    """
                )
            )
        return list(
            connection.execute(
                """
                SELECT grade_categories.*, subjects.name AS subject_name
                FROM grade_categories
                JOIN subjects ON subjects.id = grade_categories.subject_id
                WHERE grade_categories.subject_id = ?
                ORDER BY grade_categories.name
                """,
                (subject_id,),
            )
        )


def add_category(subject_id: int, name: str, weight: float) -> None:
    with connect() as connection:
        connection.execute(
            "INSERT INTO grade_categories (subject_id, name, weight) VALUES (?, ?, ?)",
            (subject_id, name.strip(), weight),
        )


def update_category(category_id: int, name: str, weight: float) -> None:
    with connect() as connection:
        connection.execute(
            "UPDATE grade_categories SET name = ?, weight = ? WHERE id = ?",
            (name.strip(), weight, category_id),
        )


def delete_category(category_id: int) -> None:
    with connect() as connection:
        connection.execute("UPDATE homework SET category_id = NULL WHERE category_id = ?", (category_id,))
        connection.execute("DELETE FROM grade_categories WHERE id = ?", (category_id,))


def fetch_category_summary(subject_id: int | None = None) -> list[sqlite3.Row]:
    where_clause = "WHERE subjects.id = ?" if subject_id is not None else ""
    params = (subject_id,) if subject_id is not None else ()
    with connect() as connection:
        return list(
            connection.execute(
                f"""
                SELECT
                    grade_categories.id,
                    grade_categories.subject_id,
                    subjects.name AS subject_name,
                    grade_categories.name,
                    grade_categories.weight,
                    AVG(CASE WHEN homework.grade IS NOT NULL THEN homework.grade END) AS category_average,
                    COUNT(CASE WHEN homework.grade IS NOT NULL THEN 1 END) AS graded_items
                FROM subjects
                JOIN grade_categories ON grade_categories.subject_id = subjects.id
                LEFT JOIN homework ON homework.category_id = grade_categories.id
                {where_clause}
                GROUP BY grade_categories.id
                ORDER BY subjects.name, grade_categories.name
                """,
                params,
            )
        )


def fetch_topics(subject_id: int | None = None) -> list[sqlite3.Row]:
    where_clause = "WHERE topics.subject_id = ?" if subject_id is not None else ""
    params = (subject_id,) if subject_id is not None else ()
    with connect() as connection:
        return list(
            connection.execute(
                f"""
                SELECT topics.*, subjects.name AS subject_name
                FROM topics
                JOIN subjects ON subjects.id = topics.subject_id
                {where_clause}
                ORDER BY subjects.name, topics.status, topics.name
                """,
                params,
            )
        )


def add_topic(subject_id: int, name: str, status: str, notes: str) -> None:
    with connect() as connection:
        connection.execute(
            "INSERT INTO topics (subject_id, name, status, notes) VALUES (?, ?, ?, ?)",
            (subject_id, name.strip(), status, notes.strip()),
        )


def update_topic(topic_id: int, subject_id: int, name: str, status: str, notes: str) -> None:
    with connect() as connection:
        connection.execute(
            "UPDATE topics SET subject_id = ?, name = ?, status = ?, notes = ? WHERE id = ?",
            (subject_id, name.strip(), status, notes.strip(), topic_id),
        )


def delete_topic(topic_id: int) -> None:
    with connect() as connection:
        connection.execute("DELETE FROM topics WHERE id = ?", (topic_id,))


def fetch_homework(subject_id: int | None = None) -> list[sqlite3.Row]:
    where_clause = "WHERE homework.subject_id = ?" if subject_id is not None else ""
    params = (subject_id,) if subject_id is not None else ()
    with connect() as connection:
        return list(
            connection.execute(
                f"""
                SELECT
                    homework.*,
                    subjects.name AS subject_name,
                    grade_categories.name AS category_name,
                    grade_categories.weight AS category_weight
                FROM homework
                JOIN subjects ON subjects.id = homework.subject_id
                LEFT JOIN grade_categories ON grade_categories.id = homework.category_id
                {where_clause}
                ORDER BY date(homework.due_date), homework.status, homework.title
                """,
                params,
            )
        )


def add_homework(
    subject_id: int,
    title: str,
    due_date: str,
    status: str,
    grade: float | None,
    notes: str,
    category_id: int | None = None,
) -> None:
    validate_grade(grade)
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO homework (subject_id, category_id, title, due_date, status, grade, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (subject_id, category_id, title.strip(), due_date, status, grade, notes.strip()),
        )


def update_homework(
    homework_id: int,
    subject_id: int,
    title: str,
    due_date: str,
    status: str,
    grade: float | None,
    notes: str,
    category_id: int | None = None,
) -> None:
    validate_grade(grade)
    with connect() as connection:
        connection.execute(
            """
            UPDATE homework
            SET subject_id = ?, category_id = ?, title = ?, due_date = ?, status = ?, grade = ?, notes = ?
            WHERE id = ?
            """,
            (subject_id, category_id, title.strip(), due_date, status, grade, notes.strip(), homework_id),
        )


def delete_homework(homework_id: int) -> None:
    with connect() as connection:
        connection.execute("DELETE FROM homework WHERE id = ?", (homework_id,))


def fetch_grades() -> list[sqlite3.Row]:
    with connect() as connection:
        return list(
            connection.execute(
                """
                SELECT grades.*, subjects.name AS subject_name
                FROM grades
                JOIN subjects ON subjects.id = grades.subject_id
                ORDER BY subjects.name, grades.assessment_type, grades.assessment_name
                """
            )
        )


def add_grade(subject_id: int, name: str, assessment_type: str, weight: float, grade: float) -> None:
    validate_grade(grade)
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO grades (subject_id, assessment_name, assessment_type, weight, grade)
            VALUES (?, ?, ?, ?, ?)
            """,
            (subject_id, name.strip(), assessment_type, weight, grade),
        )


def update_grade(
    grade_id: int,
    subject_id: int,
    name: str,
    assessment_type: str,
    weight: float,
    grade: float,
) -> None:
    validate_grade(grade)
    with connect() as connection:
        connection.execute(
            """
            UPDATE grades
            SET subject_id = ?, assessment_name = ?, assessment_type = ?, weight = ?, grade = ?
            WHERE id = ?
            """,
            (subject_id, name.strip(), assessment_type, weight, grade, grade_id),
        )


def delete_grade(grade_id: int) -> None:
    with connect() as connection:
        connection.execute("DELETE FROM grades WHERE id = ?", (grade_id,))


def fetch_calculated_grades() -> list[sqlite3.Row]:
    with connect() as connection:
        return list(
            connection.execute(
                """
                WITH category_scores AS (
                    SELECT
                        subjects.id AS subject_id,
                        subjects.name AS subject_name,
                        grade_categories.weight,
                        AVG(CASE WHEN homework.grade IS NOT NULL THEN homework.grade END) AS category_average
                    FROM subjects
                    LEFT JOIN grade_categories ON grade_categories.subject_id = subjects.id
                    LEFT JOIN homework ON homework.category_id = grade_categories.id
                    GROUP BY subjects.id, grade_categories.id
                )
                SELECT
                    subject_id,
                    subject_name,
                    COALESCE(SUM(weight), 0) AS total_weight,
                    COALESCE(SUM(CASE WHEN category_average IS NOT NULL THEN weight ELSE 0 END), 0) AS graded_weight,
                    CASE
                        WHEN SUM(CASE WHEN category_average IS NOT NULL THEN weight ELSE 0 END) > 0
                        THEN SUM(category_average * weight)
                             / SUM(CASE WHEN category_average IS NOT NULL THEN weight ELSE 0 END)
                        ELSE NULL
                    END AS weighted_average
                FROM category_scores
                GROUP BY subject_id
                ORDER BY subject_name
                """
            )
        )


def fetch_dashboard() -> dict[str, list[sqlite3.Row]]:
    with connect() as connection:
        upcoming_homework = list(
            connection.execute(
                """
                SELECT
                    homework.title,
                    homework.due_date,
                    homework.status,
                    subjects.name AS subject_name,
                    grade_categories.name AS category_name
                FROM homework
                JOIN subjects ON subjects.id = homework.subject_id
                LEFT JOIN grade_categories ON grade_categories.id = homework.category_id
                WHERE homework.status IN ('pending', 'in progress')
                ORDER BY date(homework.due_date)
                LIMIT 8
                """
            )
        )
        deadlines = list(
            connection.execute(
                """
                SELECT homework.title, homework.due_date, homework.status, subjects.name AS subject_name
                FROM homework
                JOIN subjects ON subjects.id = homework.subject_id
                ORDER BY date(homework.due_date)
                LIMIT 10
                """
            )
        )
        return {
            "upcoming_homework": upcoming_homework,
            "calculated_grades": fetch_calculated_grades(),
            "deadlines": deadlines,
        }
