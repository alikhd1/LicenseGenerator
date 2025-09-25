"""
PyQt5 application that collects Full Name and Phone Number,
generates a random license key, and stores the record into a SQLite database
using SQLAlchemy ORM.

Requirements:
    pip install PyQt5 SQLAlchemy

Run:
    python main.py

"""

import sys
import re
import secrets
import string
from datetime import datetime

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
)

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

# ---------- Database setup (SQLAlchemy) ----------
Base = declarative_base()

class License(Base):
    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True)
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    license_key = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<License(id={self.id}, name={self.full_name}, phone={self.phone}, key={self.license_key})>"

DATABASE_URL = "sqlite:///licenses.db"
engine = create_engine(DATABASE_URL, echo=False, future=True)
Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

# Create tables if they don't exist
Base.metadata.create_all(engine)

# ---------- Helper functions ----------

def generate_license_key(parts: int = 4, part_len: int = 5) -> str:
    """Generate a license key like: ABC12-DE3F4-GH56J-K9L0M"""
    alphabet = string.ascii_uppercase + string.digits
    groups = ["".join(secrets.choice(alphabet) for _ in range(part_len)) for _ in range(parts)]
    return "-".join(groups)


def validate_phone(phone: str) -> bool:
    """Very simple phone validation: ensures there are between 7 and 15 digits (ignores spaces, +, -)."""
    digits = re.sub(r"[^0-9]", "", phone)
    return 7 <= len(digits) <= 15

# ---------- PyQt UI ----------

class LicenseApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.setWindowTitle("License Generator")
        self.resize(420, 220)

        # Widgets
        self.name_label = QLabel("نام:")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("نام")

        self.phone_label = QLabel("شماره تماس:")
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("شماره تماس")

        self.key_label = QLabel("لایسنس:")
        self.key_output = QLineEdit()
        self.key_output.setReadOnly(True)

        self.generate_btn = QPushButton("ذخیره سازی")
        self.generate_btn.clicked.connect(self.on_generate_save)

        self.view_btn = QPushButton("مشاهده لایسنس ها")
        self.view_btn.clicked.connect(self.on_view)

        # Layouts
        form_layout = QVBoxLayout()

        name_layout = QHBoxLayout()
        name_layout.addWidget(self.name_label)
        name_layout.addWidget(self.name_input)

        phone_layout = QHBoxLayout()
        phone_layout.addWidget(self.phone_label)
        phone_layout.addWidget(self.phone_input)

        key_layout = QHBoxLayout()
        key_layout.addWidget(self.key_label)
        key_layout.addWidget(self.key_output)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.view_btn)
        btn_layout.addWidget(self.generate_btn)

        form_layout.addLayout(name_layout)
        form_layout.addLayout(phone_layout)
        form_layout.addLayout(key_layout)
        form_layout.addLayout(btn_layout)

        self.setLayout(form_layout)

    def on_generate_save(self):
        full_name = self.name_input.text().strip()
        phone = self.phone_input.text().strip()

        if not full_name:
            QMessageBox.warning(self, "Validation error", "Full name cannot be empty")
            return

        if not validate_phone(phone):
            QMessageBox.warning(self, "Validation error", "Phone number seems invalid. Use 7-15 digits.")
            return

        # generate a unique license key (collision-resistant loop)
        session = Session()
        tries = 0
        new_key = None
        while tries < 10:
            candidate = generate_license_key()
            exists = session.query(License).filter_by(license_key=candidate).first()
            if not exists:
                new_key = candidate
                break
            tries += 1

        if new_key is None:
            QMessageBox.critical(self, "Error", "Could not generate a unique license key. Try again.")
            session.close()
            return

        license_obj = License(full_name=full_name, phone=phone, license_key=new_key, created_at=datetime.utcnow())
        session.add(license_obj)
        try:
            session.commit()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Database error", f"Failed to save license: {e}")
            session.close()
            return

        session.close()

        self.key_output.setText(new_key)
        QMessageBox.information(self, "Saved", f"License created and saved for {full_name}")

        # Optionally clear inputs (keep the generated key visible)
        self.name_input.clear()
        self.phone_input.clear()

    def on_view(self):
        dlg = ViewDialog(self)
        dlg.exec_()


class ViewDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Saved Licenses")
        self.resize(640, 360)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Full name", "Phone", "License key", "Created at (UTC)"])
        self.table.horizontalHeader().setStretchLastSection(True)

        layout = QVBoxLayout()
        layout.addWidget(self.table)
        self.setLayout(layout)

        self.load_data()

    def load_data(self):
        session = Session()
        records = session.query(License).order_by(License.created_at.desc()).all()
        self.table.setRowCount(len(records))

        for row_idx, r in enumerate(records):
            self.table.setItem(row_idx, 0, QTableWidgetItem(r.full_name))
            self.table.setItem(row_idx, 1, QTableWidgetItem(r.phone))
            self.table.setItem(row_idx, 2, QTableWidgetItem(r.license_key))
            created = r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else ""
            self.table.setItem(row_idx, 3, QTableWidgetItem(created))

        session.close()


# ---------- Main ----------

def main():
    app = QApplication(sys.argv)
    window = LicenseApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
