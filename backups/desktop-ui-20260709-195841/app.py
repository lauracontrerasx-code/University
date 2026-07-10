from __future__ import annotations

import sys
from typing import Callable

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from university_tracker import database


TOPIC_STATUSES = ["pending", "studying", "seen"]
HOMEWORK_STATUSES = ["pending", "in progress", "submitted", "graded"]
ASSESSMENT_TYPES = ["exam", "quiz", "homework", "project", "participation", "other"]
PASSING_GRADE = 3.0


def grade_result(grade: float) -> str:
    return "Pass" if grade >= PASSING_GRADE else "Lost"


def format_grade(grade: float | None, decimals: int = 1) -> str:
    if grade is None:
        return ""
    value = float(grade)
    return f"{value:.{decimals}f} - {grade_result(value)}"


def grade_color(grade: float | None) -> str:
    if grade is None:
        return "#9A9AA5"
    return "#57B981" if grade >= PASSING_GRADE else "#E26D63"


def make_table(headers: list[str]) -> QTableWidget:
    table = QTableWidget()
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().setVisible(False)
    table.setSelectionBehavior(QTableWidget.SelectRows)
    table.setSelectionMode(QTableWidget.SingleSelection)
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    table.setAlternatingRowColors(True)
    return table


def set_table_rows(table: QTableWidget, rows: list[list[object]], ids: list[int] | None = None) -> None:
    table.setRowCount(len(rows))
    for row_index, row in enumerate(rows):
        if ids:
            table.setVerticalHeaderItem(row_index, QTableWidgetItem(str(ids[row_index])))
        for column_index, value in enumerate(row):
            item = QTableWidgetItem("" if value is None else str(value))
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            table.setItem(row_index, column_index, item)
    table.resizeRowsToContents()


def selected_row_id(table: QTableWidget) -> int | None:
    selected = table.selectionModel().selectedRows()
    if not selected:
        return None
    header = table.verticalHeaderItem(selected[0].row())
    return int(header.text()) if header else None


def show_error(parent: QWidget, error: Exception) -> None:
    QMessageBox.warning(parent, "Could not save", str(error))


class SubjectPicker(QComboBox):
    def refresh(self) -> None:
        current = self.currentData()
        self.clear()
        for subject in database.fetch_subjects():
            self.addItem(subject["name"], subject["id"])
        if current is not None:
            index = self.findData(current)
            if index >= 0:
                self.setCurrentIndex(index)

    def set_subject(self, subject_id: int) -> None:
        index = self.findData(subject_id)
        if index >= 0:
            self.setCurrentIndex(index)


class CategoryPicker(QComboBox):
    def refresh(self, subject_id: int | None) -> None:
        current = self.currentData()
        self.clear()
        self.addItem("No category", None)
        if subject_id is not None:
            for category in database.fetch_categories(subject_id):
                self.addItem(f"{category['name']} ({category['weight']:.0f}%)", category["id"])
        if current is not None:
            index = self.findData(current)
            if index >= 0:
                self.setCurrentIndex(index)

    def set_category(self, category_id: int | None) -> None:
        index = self.findData(category_id)
        self.setCurrentIndex(index if index >= 0 else 0)


class DashboardTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        heading = QLabel("University Dashboard")
        heading.setObjectName("PageTitle")
        layout.addWidget(heading)

        grid = QGridLayout()
        grid.setSpacing(14)
        layout.addLayout(grid)

        self.upcoming = make_table(["Subject", "Homework", "Due", "Status"])
        self.grades = make_table(["Subject", "Average", "Weight configured", "Weight graded"])
        self.deadlines = make_table(["Subject", "Deadline", "Due", "Status"])

        grid.addWidget(self.panel("Upcoming Homework", self.upcoming), 0, 0)
        grid.addWidget(self.panel("Current Calculated Grades", self.grades), 0, 1)
        grid.addWidget(self.panel("Important Deadlines", self.deadlines), 1, 0, 1, 2)

    def panel(self, title: str, table: QTableWidget) -> QWidget:
        frame = QFrame()
        frame.setObjectName("Panel")
        panel_layout = QVBoxLayout(frame)
        label = QLabel(title)
        label.setObjectName("PanelTitle")
        panel_layout.addWidget(label)
        panel_layout.addWidget(table)
        return frame

    def refresh(self) -> None:
        data = database.fetch_dashboard()
        set_table_rows(
            self.upcoming,
            [
                [
                    row["subject_name"],
                    row["title"] if row["category_name"] is None else f"{row['title']} - {row['category_name']}",
                    row["due_date"],
                    row["status"],
                ]
                for row in data["upcoming_homework"]
            ],
        )
        set_table_rows(
            self.grades,
            [
                [
                    row["subject_name"],
                    "No grades" if row["weighted_average"] is None else format_grade(row["weighted_average"], 2),
                    f"{row['total_weight']:.1f}%",
                    f"{row['graded_weight']:.1f}%",
                ]
                for row in data["calculated_grades"]
            ],
        )
        set_table_rows(
            self.deadlines,
            [[row["subject_name"], row["title"], row["due_date"], row["status"]] for row in data["deadlines"]],
        )


class HomeTab(QWidget):
    def __init__(self, navigate: Callable[[str], None]) -> None:
        super().__init__()
        layout = QGridLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(18)

        buttons = [
            ("Dashboard", "dashboard"),
            ("Homeworks", "homework"),
            ("Signatures", "signatures"),
            ("Grades", "grades"),
        ]
        for index, (label, destination) in enumerate(buttons):
            button = QPushButton(label)
            button.setObjectName("HomeButton")
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            button.clicked.connect(lambda checked=False, target=destination: navigate(target))
            layout.addWidget(button, index // 2, index % 2)

        layout.setRowStretch(0, 1)
        layout.setRowStretch(1, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)


class SubjectsTab(QWidget):
    def __init__(self, after_change: Callable[[], None]) -> None:
        super().__init__()
        self.after_change = after_change
        self.editing_id: int | None = None
        self.editing_category_id: int | None = None
        self.editing_topic_id: int | None = None
        self.editing_homework_id: int | None = None
        self.loading_homework_form = False

        layout = QHBoxLayout(self)
        self.table = make_table(["Signature"])
        self.table.itemSelectionChanged.connect(self.load_selected)
        layout.addWidget(self.table, 1)

        self.detail_tabs = QTabWidget()
        layout.addWidget(self.detail_tabs, 2)

        self.detail_tabs.addTab(self.signature_panel(), "Signature")
        self.detail_tabs.addTab(self.grading_panel(), "General grading")
        self.detail_tabs.addTab(self.topics_panel(), "Topics")
        self.detail_tabs.addTab(self.homeworks_panel(), "Homeworks")

    def signature_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("FormPanel")
        layout = QVBoxLayout(panel)
        title = QLabel("Signature Details")
        title.setObjectName("PanelTitle")
        layout.addWidget(title)

        form = QFormLayout()
        self.name = QLineEdit()
        self.professor = QLineEdit()
        self.teacher_email = QLineEdit()
        self.schedule = QLineEdit()
        self.semester = QSpinBox()
        self.semester.setRange(1, 20)
        self.semester.setMinimumHeight(36)
        form.addRow("Signature", self.name)
        form.addRow("Semester", self.semester)
        form.addRow("Professor", self.professor)
        form.addRow("Teacher email", self.teacher_email)
        form.addRow("Schedule", self.schedule)
        layout.addLayout(form)
        layout.addStretch()

        buttons = QHBoxLayout()
        save = QPushButton("Save")
        save.clicked.connect(self.save)
        new = QPushButton("New")
        new.clicked.connect(self.clear)
        delete = QPushButton("Delete")
        delete.clicked.connect(self.delete)
        buttons.addWidget(save)
        buttons.addWidget(new)
        buttons.addWidget(delete)
        layout.addLayout(buttons)
        return panel

    def grading_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("FormPanel")
        layout = QVBoxLayout(panel)
        title = QLabel("General Grading")
        title.setObjectName("PanelTitle")
        layout.addWidget(title)

        overall_card = QFrame()
        overall_card.setObjectName("OverallGradeCard")
        overall_layout = QVBoxLayout(overall_card)
        overall_label = QLabel("Overall grade")
        overall_label.setObjectName("OverallGradeLabel")
        self.overall_grade = QLabel("--")
        self.overall_grade.setObjectName("OverallGradeValue")
        self.overall_grade_detail = QLabel("Select a signature to calculate it.")
        self.overall_grade_detail.setObjectName("OverallGradeDetail")
        overall_layout.addWidget(overall_label)
        overall_layout.addWidget(self.overall_grade)
        overall_layout.addWidget(self.overall_grade_detail)
        layout.addWidget(overall_card)

        self.category_table = make_table(["Category", "Weight %", "Average", "Graded items"])
        self.category_table.itemSelectionChanged.connect(self.load_category)
        layout.addWidget(self.category_table)

        form = QFormLayout()
        self.category_name = QLineEdit()
        self.category_weight = QDoubleSpinBox()
        self.category_weight.setRange(0, 100)
        self.category_weight.setDecimals(2)
        self.category_weight.setSuffix("%")
        form.addRow("Category", self.category_name)
        form.addRow("Weight", self.category_weight)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        save = QPushButton("Save Category")
        save.clicked.connect(self.save_category)
        new = QPushButton("New Category")
        new.clicked.connect(self.clear_category)
        delete = QPushButton("Delete Category")
        delete.clicked.connect(self.delete_category)
        buttons.addWidget(save)
        buttons.addWidget(new)
        buttons.addWidget(delete)
        layout.addLayout(buttons)
        return panel

    def topics_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("FormPanel")
        layout = QVBoxLayout(panel)
        title = QLabel("Topics")
        title.setObjectName("PanelTitle")
        layout.addWidget(title)
        self.signature_topics = make_table(["Topic", "Status", "Notes"])
        self.signature_topics.itemSelectionChanged.connect(self.load_signature_topic)
        layout.addWidget(self.signature_topics)

        form = QFormLayout()
        self.topic_name = QLineEdit()
        self.topic_status = QComboBox()
        self.topic_status.addItems(TOPIC_STATUSES)
        self.topic_notes = QTextEdit()
        self.topic_notes.setFixedHeight(80)
        form.addRow("Topic", self.topic_name)
        form.addRow("Status", self.topic_status)
        form.addRow("Notes", self.topic_notes)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        add = QPushButton("Save Topic")
        add.clicked.connect(self.save_signature_topic)
        new = QPushButton("New Topic")
        new.clicked.connect(self.clear_topic_form)
        delete = QPushButton("Delete Topic")
        delete.clicked.connect(self.delete_signature_topic)
        buttons.addWidget(add)
        buttons.addWidget(new)
        buttons.addWidget(delete)
        layout.addLayout(buttons)
        return panel

    def homeworks_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("FormPanel")
        layout = QVBoxLayout(panel)
        title = QLabel("Homeworks")
        title.setObjectName("PanelTitle")
        layout.addWidget(title)
        self.signature_homeworks = make_table(["Homework", "Category", "Due", "Status", "Grade"])
        self.signature_homeworks.itemSelectionChanged.connect(self.load_signature_homework)
        layout.addWidget(self.signature_homeworks)

        form = QFormLayout()
        self.homework_category = CategoryPicker()
        self.homework_title = QLineEdit()
        self.homework_due_date = QDateEdit()
        self.homework_due_date.setCalendarPopup(True)
        self.homework_due_date.setDisplayFormat("yyyy-MM-dd")
        self.homework_due_date.setDate(QDate.currentDate())
        self.homework_status = QComboBox()
        self.homework_status.addItems(HOMEWORK_STATUSES)
        self.homework_grade_enabled = QComboBox()
        self.homework_grade_enabled.addItems(["No grade yet", "Has grade"])
        self.homework_grade = QDoubleSpinBox()
        self.homework_grade.setRange(1.0, 5.0)
        self.homework_grade.setDecimals(1)
        self.homework_grade.setSingleStep(0.1)
        self.homework_grade.valueChanged.connect(self.mark_signature_homework_has_grade)
        self.homework_notes = QTextEdit()
        self.homework_notes.setFixedHeight(80)
        form.addRow("Category", self.homework_category)
        form.addRow("Homework", self.homework_title)
        form.addRow("Due date", self.homework_due_date)
        form.addRow("Status", self.homework_status)
        form.addRow("Grade", self.homework_grade_enabled)
        form.addRow("Grade value", self.homework_grade)
        form.addRow("Notes/link", self.homework_notes)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        add = QPushButton("Save Homework")
        add.clicked.connect(self.save_signature_homework)
        new = QPushButton("New Homework")
        new.clicked.connect(self.clear_homework_form)
        delete = QPushButton("Delete Homework")
        delete.clicked.connect(self.delete_signature_homework)
        buttons.addWidget(add)
        buttons.addWidget(new)
        buttons.addWidget(delete)
        layout.addLayout(buttons)
        return panel

    def refresh(self) -> None:
        current_id = self.editing_id
        rows = database.fetch_subjects()
        set_table_rows(
            self.table,
            [[row["name"]] for row in rows],
            [row["id"] for row in rows],
        )

        if current_id:
            self.load_subject(current_id)
        else:
            self.refresh_subject_tables(None)

    def clear(self) -> None:
        self.editing_id = None
        self.editing_category_id = None
        self.table.clearSelection()
        self.name.clear()
        self.semester.setValue(1)
        self.professor.clear()
        self.teacher_email.clear()
        self.schedule.clear()
        self.clear_category()
        self.clear_topic_form()
        self.clear_homework_form()
        self.refresh_subject_tables(None)
        self.detail_tabs.setCurrentIndex(0)

    def load_selected(self) -> None:
        subject_id = selected_row_id(self.table)
        if subject_id is not None:
            self.load_subject(subject_id)

    def load_subject(self, subject_id: int) -> None:
        subjects = {row["id"]: row for row in database.fetch_subjects()}
        subject = subjects.get(subject_id)
        if subject is None:
            return
        self.editing_id = subject_id
        self.name.setText(subject["name"])
        self.semester.setValue(subject["semester"])
        self.professor.setText(subject["professor"])
        self.teacher_email.setText(subject["teacher_email"])
        self.schedule.setText(subject["schedule"])
        self.clear_category()
        self.refresh_subject_tables(subject_id)

    def refresh_subject_tables(self, subject_id: int | None) -> None:
        if subject_id is None:
            self.overall_grade.setText("--")
            self.overall_grade_detail.setText("Select a signature to calculate it.")
            set_table_rows(self.category_table, [])
            set_table_rows(self.signature_topics, [])
            set_table_rows(self.signature_homeworks, [])
            self.homework_category.refresh(None)
            return

        calculated_grades = {
            row["subject_id"]: row for row in database.fetch_calculated_grades()
        }
        calculated_grade = calculated_grades.get(subject_id)
        if calculated_grade is None or calculated_grade["weighted_average"] is None:
            self.overall_grade.setText("--")
            self.overall_grade_detail.setText("No graded category data yet.")
            self.overall_grade.setStyleSheet("color: #FFC212;")
        else:
            overall = calculated_grade["weighted_average"]
            self.overall_grade.setText(f"{overall:.2f}")
            self.overall_grade.setStyleSheet(f"color: {grade_color(overall)};")
            self.overall_grade_detail.setText(
                f"{grade_result(overall)}. Calculated from {calculated_grade['graded_weight']:.1f}% "
                f"of {calculated_grade['total_weight']:.1f}% configured."
            )

        categories = database.fetch_category_summary(subject_id)
        set_table_rows(
            self.category_table,
            [
                [
                    row["name"],
                    f"{row['weight']:.2f}",
                    "No grades" if row["category_average"] is None else format_grade(row["category_average"], 2),
                    row["graded_items"],
                ]
                for row in categories
            ],
            [row["id"] for row in categories],
        )

        topics = database.fetch_topics(subject_id)
        set_table_rows(
            self.signature_topics,
            [[row["name"], row["status"], row["notes"]] for row in topics],
            [row["id"] for row in topics],
        )

        self.homework_category.refresh(subject_id)
        homework = database.fetch_homework(subject_id)
        set_table_rows(
            self.signature_homeworks,
            [
                [
                    row["title"],
                    "" if row["category_name"] is None else f"{row['category_name']} ({row['category_weight']:.0f}%)",
                    row["due_date"],
                    row["status"],
                    format_grade(row["grade"]),
                ]
                for row in homework
            ],
            [row["id"] for row in homework],
        )

    def save(self) -> None:
        if not self.name.text().strip():
            QMessageBox.information(self, "Signature needed", "Add a signature name first.")
            return
        try:
            if self.editing_id:
                database.update_subject(
                    self.editing_id,
                    self.name.text(),
                    self.professor.text(),
                    self.teacher_email.text(),
                    self.schedule.text(),
                    self.semester.value(),
                )
            else:
                database.add_subject(
                    self.name.text(),
                    self.professor.text(),
                    self.teacher_email.text(),
                    self.schedule.text(),
                    self.semester.value(),
                )
            self.after_change()
        except Exception as error:
            show_error(self, error)

    def delete(self) -> None:
        if self.editing_id is None:
            return
        database.delete_subject(self.editing_id)
        self.clear()
        self.after_change()

    def clear_category(self) -> None:
        self.editing_category_id = None
        if hasattr(self, "category_table"):
            self.category_table.clearSelection()
        self.category_name.clear()
        self.category_weight.setValue(0)

    def load_category(self) -> None:
        category_id = selected_row_id(self.category_table)
        if category_id is None:
            return
        self.editing_category_id = category_id
        row = self.category_table.currentRow()
        self.category_name.setText(self.category_table.item(row, 0).text())
        self.category_weight.setValue(float(self.category_table.item(row, 1).text()))

    def save_category(self) -> None:
        if self.editing_id is None:
            QMessageBox.information(self, "Choose a signature", "Select a signature before editing grading.")
            return
        if not self.category_name.text().strip():
            QMessageBox.information(self, "Category needed", "Add a grading category name.")
            return
        try:
            if self.editing_category_id:
                database.update_category(
                    self.editing_category_id,
                    self.category_name.text(),
                    self.category_weight.value(),
                )
            else:
                database.add_category(
                    self.editing_id,
                    self.category_name.text(),
                    self.category_weight.value(),
                )
            self.clear_category()
            self.after_change()
        except Exception as error:
            show_error(self, error)

    def delete_category(self) -> None:
        if self.editing_category_id is None:
            return
        database.delete_category(self.editing_category_id)
        self.clear_category()
        self.after_change()

    def clear_topic_form(self) -> None:
        self.editing_topic_id = None
        if hasattr(self, "signature_topics"):
            self.signature_topics.clearSelection()
        self.topic_name.clear()
        self.topic_status.setCurrentIndex(0)
        self.topic_notes.clear()

    def load_signature_topic(self) -> None:
        topic_id = selected_row_id(self.signature_topics)
        if topic_id is None or self.editing_id is None:
            return
        topics = {row["id"]: row for row in database.fetch_topics(self.editing_id)}
        topic = topics.get(topic_id)
        if topic is None:
            return
        self.editing_topic_id = topic_id
        self.topic_name.setText(topic["name"])
        self.topic_status.setCurrentText(topic["status"])
        self.topic_notes.setPlainText(topic["notes"])

    def save_signature_topic(self) -> None:
        if self.editing_id is None:
            QMessageBox.information(self, "Choose a signature", "Select a signature before adding topics.")
            return
        if not self.topic_name.text().strip():
            QMessageBox.information(self, "Topic needed", "Add a topic name first.")
            return
        is_update = self.editing_topic_id is not None
        if self.editing_topic_id:
            database.update_topic(
                self.editing_topic_id,
                self.editing_id,
                self.topic_name.text(),
                self.topic_status.currentText(),
                self.topic_notes.toPlainText(),
            )
        else:
            database.add_topic(
                self.editing_id,
                self.topic_name.text(),
                self.topic_status.currentText(),
                self.topic_notes.toPlainText(),
            )
        if not is_update:
            self.clear_topic_form()
        self.after_change()

    def delete_signature_topic(self) -> None:
        if self.editing_topic_id is None:
            return
        database.delete_topic(self.editing_topic_id)
        self.clear_topic_form()
        self.after_change()

    def clear_homework_form(self) -> None:
        self.editing_homework_id = None
        if hasattr(self, "signature_homeworks"):
            self.signature_homeworks.clearSelection()
        self.homework_category.refresh(self.editing_id)
        self.homework_title.clear()
        self.homework_due_date.setDate(QDate.currentDate())
        self.homework_status.setCurrentIndex(0)
        self.loading_homework_form = True
        self.homework_grade_enabled.setCurrentIndex(0)
        self.homework_grade.setValue(1.0)
        self.loading_homework_form = False
        self.homework_notes.clear()

    def load_signature_homework(self) -> None:
        homework_id = selected_row_id(self.signature_homeworks)
        if homework_id is None or self.editing_id is None:
            return
        homeworks = {row["id"]: row for row in database.fetch_homework(self.editing_id)}
        homework = homeworks.get(homework_id)
        if homework is None:
            return
        self.editing_homework_id = homework_id
        self.homework_category.refresh(self.editing_id)
        self.homework_category.set_category(homework["category_id"])
        self.homework_title.setText(homework["title"])
        self.homework_due_date.setDate(QDate.fromString(homework["due_date"], "yyyy-MM-dd"))
        self.homework_status.setCurrentText(homework["status"])
        self.loading_homework_form = True
        self.homework_grade_enabled.setCurrentIndex(1 if homework["grade"] is not None else 0)
        self.homework_grade.setValue(1.0 if homework["grade"] is None else homework["grade"])
        self.loading_homework_form = False
        self.homework_notes.setPlainText(homework["notes"])

    def save_signature_homework(self) -> None:
        if self.editing_id is None:
            QMessageBox.information(self, "Choose a signature", "Select a signature before adding homeworks.")
            return
        if not self.homework_title.text().strip():
            QMessageBox.information(self, "Homework needed", "Add a homework title first.")
            return
        grade = self.homework_grade.value() if self.homework_grade_enabled.currentIndex() == 1 else None
        is_update = self.editing_homework_id is not None
        if self.editing_homework_id:
            database.update_homework(
                self.editing_homework_id,
                self.editing_id,
                self.homework_title.text(),
                self.homework_due_date.date().toString("yyyy-MM-dd"),
                self.homework_status.currentText(),
                grade,
                self.homework_notes.toPlainText(),
                self.homework_category.currentData(),
            )
        else:
            database.add_homework(
                self.editing_id,
                self.homework_title.text(),
                self.homework_due_date.date().toString("yyyy-MM-dd"),
                self.homework_status.currentText(),
                grade,
                self.homework_notes.toPlainText(),
                self.homework_category.currentData(),
            )
        if not is_update:
            self.clear_homework_form()
        self.after_change()

    def delete_signature_homework(self) -> None:
        if self.editing_homework_id is None:
            return
        database.delete_homework(self.editing_homework_id)
        self.clear_homework_form()
        self.after_change()

    def mark_signature_homework_has_grade(self) -> None:
        if not self.loading_homework_form:
            self.homework_grade_enabled.setCurrentIndex(1)


class TopicsTab(QWidget):
    def __init__(self, after_change: Callable[[], None]) -> None:
        super().__init__()
        self.after_change = after_change
        self.editing_id: int | None = None

        layout = QHBoxLayout(self)
        self.table = make_table(["Subject", "Topic", "Status", "Notes"])
        self.table.itemSelectionChanged.connect(self.load_selected)
        layout.addWidget(self.table, 2)

        form_panel = QFrame()
        form_panel.setObjectName("FormPanel")
        form_layout = QVBoxLayout(form_panel)
        title = QLabel("Topic Details")
        title.setObjectName("PanelTitle")
        form_layout.addWidget(title)

        form = QFormLayout()
        self.subject = SubjectPicker()
        self.name = QLineEdit()
        self.status = QComboBox()
        self.status.addItems(TOPIC_STATUSES)
        self.notes = QTextEdit()
        self.notes.setFixedHeight(120)
        form.addRow("Subject", self.subject)
        form.addRow("Topic", self.name)
        form.addRow("Status", self.status)
        form.addRow("Notes", self.notes)
        form_layout.addLayout(form)
        form_layout.addStretch()
        form_layout.addLayout(self.buttons())
        layout.addWidget(form_panel, 1)

    def buttons(self) -> QHBoxLayout:
        buttons = QHBoxLayout()
        save = QPushButton("Save")
        save.clicked.connect(self.save)
        new = QPushButton("New")
        new.clicked.connect(self.clear)
        delete = QPushButton("Delete")
        delete.clicked.connect(self.delete)
        buttons.addWidget(save)
        buttons.addWidget(new)
        buttons.addWidget(delete)
        return buttons

    def refresh(self) -> None:
        self.subject.refresh()
        rows = database.fetch_topics()
        set_table_rows(
            self.table,
            [[row["subject_name"], row["name"], row["status"], row["notes"]] for row in rows],
            [row["id"] for row in rows],
        )

    def clear(self) -> None:
        self.editing_id = None
        self.table.clearSelection()
        self.name.clear()
        self.status.setCurrentIndex(0)
        self.notes.clear()

    def load_selected(self) -> None:
        row_id = selected_row_id(self.table)
        if row_id is None:
            return
        self.editing_id = row_id
        rows = {row["id"]: row for row in database.fetch_topics()}
        row = rows[row_id]
        self.subject.set_subject(row["subject_id"])
        self.name.setText(row["name"])
        self.status.setCurrentText(row["status"])
        self.notes.setPlainText(row["notes"])

    def save(self) -> None:
        if self.subject.currentData() is None or not self.name.text().strip():
            QMessageBox.information(self, "Topic needed", "Choose a subject and add a topic name.")
            return
        if self.editing_id:
            database.update_topic(
                self.editing_id,
                self.subject.currentData(),
                self.name.text(),
                self.status.currentText(),
                self.notes.toPlainText(),
            )
        else:
            database.add_topic(
                self.subject.currentData(),
                self.name.text(),
                self.status.currentText(),
                self.notes.toPlainText(),
            )
        self.clear()
        self.after_change()

    def delete(self) -> None:
        if self.editing_id is None:
            return
        database.delete_topic(self.editing_id)
        self.clear()
        self.after_change()


class HomeworkTab(QWidget):
    def __init__(self, after_change: Callable[[], None]) -> None:
        super().__init__()
        self.after_change = after_change
        self.editing_id: int | None = None

        layout = QHBoxLayout(self)
        self.table = make_table(["Subject", "Title", "Category", "Due", "Status", "Grade", "Notes"])
        self.table.itemSelectionChanged.connect(self.load_selected)
        layout.addWidget(self.table, 2)

        form_panel = QFrame()
        form_panel.setObjectName("FormPanel")
        form_layout = QVBoxLayout(form_panel)
        title = QLabel("Homework Details")
        title.setObjectName("PanelTitle")
        form_layout.addWidget(title)

        form = QFormLayout()
        self.subject = SubjectPicker()
        self.subject.currentIndexChanged.connect(self.update_category_options)
        self.category = CategoryPicker()
        self.title = QLineEdit()
        self.due_date = QDateEdit()
        self.due_date.setCalendarPopup(True)
        self.due_date.setDisplayFormat("yyyy-MM-dd")
        self.due_date.setDate(QDate.currentDate())
        self.status = QComboBox()
        self.status.addItems(HOMEWORK_STATUSES)
        self.grade_enabled = QComboBox()
        self.grade_enabled.addItems(["No grade yet", "Has grade"])
        self.grade = QDoubleSpinBox()
        self.grade.setRange(1.0, 5.0)
        self.grade.setDecimals(1)
        self.grade.setSingleStep(0.1)
        self.notes = QTextEdit()
        self.notes.setFixedHeight(120)
        form.addRow("Subject", self.subject)
        form.addRow("Category", self.category)
        form.addRow("Title", self.title)
        form.addRow("Due date", self.due_date)
        form.addRow("Status", self.status)
        form.addRow("Grade", self.grade_enabled)
        form.addRow("Grade value", self.grade)
        form.addRow("Notes/link", self.notes)
        form_layout.addLayout(form)
        form_layout.addStretch()
        form_layout.addLayout(self.buttons())
        layout.addWidget(form_panel, 1)

    def buttons(self) -> QHBoxLayout:
        buttons = QHBoxLayout()
        save = QPushButton("Save")
        save.clicked.connect(self.save)
        new = QPushButton("New")
        new.clicked.connect(self.clear)
        delete = QPushButton("Delete")
        delete.clicked.connect(self.delete)
        buttons.addWidget(save)
        buttons.addWidget(new)
        buttons.addWidget(delete)
        return buttons

    def refresh(self) -> None:
        self.subject.refresh()
        self.update_category_options()
        rows = database.fetch_homework()
        set_table_rows(
            self.table,
            [
                [
                    row["subject_name"],
                    row["title"],
                    "" if row["category_name"] is None else f"{row['category_name']} ({row['category_weight']:.0f}%)",
                    row["due_date"],
                    row["status"],
                    format_grade(row["grade"]),
                    row["notes"],
                ]
                for row in rows
            ],
            [row["id"] for row in rows],
        )

    def clear(self) -> None:
        self.editing_id = None
        self.table.clearSelection()
        self.title.clear()
        self.update_category_options()
        self.due_date.setDate(QDate.currentDate())
        self.status.setCurrentIndex(0)
        self.grade_enabled.setCurrentIndex(0)
        self.grade.setValue(1.0)
        self.notes.clear()

    def load_selected(self) -> None:
        row_id = selected_row_id(self.table)
        if row_id is None:
            return
        self.editing_id = row_id
        rows = {row["id"]: row for row in database.fetch_homework()}
        row = rows[row_id]
        self.subject.set_subject(row["subject_id"])
        self.update_category_options()
        self.category.set_category(row["category_id"])
        self.title.setText(row["title"])
        self.due_date.setDate(QDate.fromString(row["due_date"], "yyyy-MM-dd"))
        self.status.setCurrentText(row["status"])
        self.grade_enabled.setCurrentIndex(1 if row["grade"] is not None else 0)
        self.grade.setValue(1.0 if row["grade"] is None else row["grade"])
        self.notes.setPlainText(row["notes"])

    def save(self) -> None:
        if self.subject.currentData() is None or not self.title.text().strip():
            QMessageBox.information(self, "Homework needed", "Choose a subject and add a homework title.")
            return
        grade = self.grade.value() if self.grade_enabled.currentIndex() == 1 else None
        if self.editing_id:
            database.update_homework(
                self.editing_id,
                self.subject.currentData(),
                self.title.text(),
                self.due_date.date().toString("yyyy-MM-dd"),
                self.status.currentText(),
                grade,
                self.notes.toPlainText(),
                self.category.currentData(),
            )
        else:
            database.add_homework(
                self.subject.currentData(),
                self.title.text(),
                self.due_date.date().toString("yyyy-MM-dd"),
                self.status.currentText(),
                grade,
                self.notes.toPlainText(),
                self.category.currentData(),
            )
        self.clear()
        self.after_change()

    def delete(self) -> None:
        if self.editing_id is None:
            return
        database.delete_homework(self.editing_id)
        self.clear()
        self.after_change()

    def update_category_options(self, *_: object) -> None:
        if hasattr(self, "category"):
            self.category.refresh(self.subject.currentData())


class GradesTab(QWidget):
    def __init__(self, after_change: Callable[[], None]) -> None:
        super().__init__()
        self.after_change = after_change
        layout = QVBoxLayout(self)
        title = QLabel("Grades")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        self.summary = make_table(["Signature", "Average", "Weight configured", "Weight graded"])
        self.categories = make_table(["Signature", "Category", "Weight %", "Category average", "Graded items"])
        layout.addWidget(self.panel("Current Calculated Grades", self.summary))
        layout.addWidget(self.panel("Category Breakdown", self.categories))

    def panel(self, title: str, table: QTableWidget) -> QWidget:
        frame = QFrame()
        frame.setObjectName("Panel")
        layout = QVBoxLayout(frame)
        label = QLabel(title)
        label.setObjectName("PanelTitle")
        layout.addWidget(label)
        layout.addWidget(table)
        return frame

    def refresh(self) -> None:
        set_table_rows(
            self.summary,
            [
                [
                    row["subject_name"],
                    "No grades" if row["weighted_average"] is None else format_grade(row["weighted_average"], 2),
                    f"{row['total_weight']:.1f}%",
                    f"{row['graded_weight']:.1f}%",
                ]
                for row in database.fetch_calculated_grades()
            ],
        )
        rows = database.fetch_category_summary()
        set_table_rows(
            self.categories,
            [
                [
                    row["subject_name"],
                    row["name"],
                    f"{row['weight']:.2f}",
                    "No grades" if row["category_average"] is None else format_grade(row["category_average"], 2),
                    row["graded_items"],
                ]
                for row in rows
            ],
            [row["id"] for row in rows],
        )


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("University Tracker")
        self.resize(1180, 740)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.home_tab = HomeTab(self.navigate_to)
        self.dashboard_tab = DashboardTab()
        self.subjects_tab = SubjectsTab(self.refresh_all)

        self.tabs.addTab(self.home_tab, "Home")
        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        self.tabs.addTab(self.subjects_tab, "Signatures")

        self.tab_routes = {
            "home": self.home_tab,
            "dashboard": self.dashboard_tab,
            "signatures": self.subjects_tab,
            "topics": self.subjects_tab,
            "homework": self.subjects_tab,
            "grades": self.subjects_tab,
        }

        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self.refresh_all)
        self.toolbar = self.addToolBar("Main")
        self.toolbar.addAction(refresh_action)

        self.statusBar().showMessage(f"Saving locally to {database.DB_PATH}")
        self.refresh_all()

    def navigate_to(self, route: str) -> None:
        tab = self.tab_routes.get(route)
        if tab is not None:
            self.tabs.setCurrentWidget(tab)
        if route == "grades":
            self.subjects_tab.detail_tabs.setCurrentIndex(1)
        elif route == "topics":
            self.subjects_tab.detail_tabs.setCurrentIndex(2)
        elif route == "homework":
            self.subjects_tab.detail_tabs.setCurrentIndex(3)
        elif route == "signatures":
            self.subjects_tab.detail_tabs.setCurrentIndex(0)

    def refresh_all(self) -> None:
        self.dashboard_tab.refresh()
        self.subjects_tab.refresh()


def apply_theme(app: QApplication) -> None:
    app.setStyleSheet(
        """
        QWidget {
            font-family: Segoe UI, Arial, sans-serif;
            font-size: 10.5pt;
            color: #F0F0F3;
        }
        QMainWindow, QTabWidget::pane {
            background: #171721;
        }
        QTabBar::tab {
            background: #1B1B24;
            border: 1px solid #34343B;
            color: #9A9AA5;
            padding: 9px 16px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background: #2D2D32;
            color: #FFC212;
            border-bottom-color: #FFC212;
        }
        #PageTitle {
            font-size: 20pt;
            font-weight: 700;
            padding: 6px 2px 12px 2px;
            color: #F0F0F3;
        }
        #Panel, #FormPanel {
            background: #2D2D32;
            border: 1px solid #34343B;
            border-radius: 8px;
        }
        #PanelTitle {
            font-size: 12.5pt;
            font-weight: 700;
            padding: 4px 0 8px 0;
            color: #FFC212;
        }
        #OverallGradeCard {
            background: rgba(255, 194, 18, 0.12);
            border: 1px solid rgba(255, 194, 18, 0.5);
            border-radius: 8px;
            padding: 12px;
        }
        #OverallGradeLabel {
            color: #9A9AA5;
            font-size: 10pt;
            font-weight: 700;
        }
        #OverallGradeValue {
            color: #FFC212;
            font-size: 34pt;
            font-weight: 900;
            padding: 0;
        }
        #OverallGradeDetail {
            color: #9A9AA5;
            font-size: 10pt;
        }
        QTableWidget {
            background: #202027;
            alternate-background-color: #2D2D32;
            border: 1px solid #34343B;
            gridline-color: #34343B;
            color: #F0F0F3;
            selection-background-color: rgba(255, 194, 18, 0.12);
            selection-color: #FFC212;
        }
        QHeaderView::section {
            background: #34343B;
            color: #FFC212;
            padding: 7px;
            border: 0;
            font-weight: 600;
        }
        QLineEdit, QTextEdit, QComboBox, QDateEdit, QDoubleSpinBox, QSpinBox {
            background: #202027;
            border: 1px solid #34343B;
            border-radius: 6px;
            color: #F0F0F3;
            min-height: 28px;
            padding: 6px;
        }
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateEdit:focus,
        QDoubleSpinBox:focus, QSpinBox:focus {
            border: 1px solid rgba(255, 194, 18, 0.5);
        }
        QComboBox QAbstractItemView {
            background: #202027;
            border: 1px solid #34343B;
            color: #F0F0F3;
            selection-background-color: rgba(255, 194, 18, 0.12);
            selection-color: #FFC212;
        }
        QPushButton {
            background: #FFC212;
            color: #171721;
            border: 0;
            border-radius: 6px;
            padding: 8px 12px;
            font-weight: 600;
        }
        QPushButton:hover {
            background: #FFDD7A;
        }
        QPushButton#HomeButton {
            background: #FFC212;
            border-radius: 8px;
            color: #171721;
            font-size: 28pt;
            font-weight: 800;
            min-width: 260px;
            min-height: 180px;
        }
        QPushButton#HomeButton:hover {
            background: #FFDD7A;
        }
        QToolBar {
            background: #1B1B24;
            border-bottom: 1px solid #34343B;
            spacing: 8px;
            padding: 4px;
        }
        QStatusBar {
            background: #1B1B24;
            color: #9A9AA5;
        }
        QScrollBar:vertical, QScrollBar:horizontal {
            background: #202027;
            border: 0;
        }
        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
            background: #6B6B76;
            border-radius: 4px;
        }
        """
    )


def main() -> None:
    database.initialize_database()
    app = QApplication(sys.argv)
    app.setApplicationName("University Tracker")
    apply_theme(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
