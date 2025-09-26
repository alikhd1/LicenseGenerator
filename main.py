import random
import sys
import string
from datetime import datetime
import base64
from io import BytesIO

import qrcode
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QMessageBox,
    QSpinBox,
    QHBoxLayout,
)
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
from PyQt5.QtWebEngineWidgets import QWebEngineView

from sqlalchemy import Column, Integer, String, DateTime, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# ---------- Database setup ----------
Base = declarative_base()

class License(Base):
    __tablename__ = "licenses"
    id = Column(Integer, primary_key=True)
    license_key = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

DATABASE_URL = "sqlite:///licenses.db"
engine = create_engine(DATABASE_URL, echo=False, future=True)
Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base.metadata.create_all(engine)

# ---------- Helpers ----------
def generate_license_key(length: int = 16) -> str:
    """Generate a random string with letters and numbers."""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choices(characters, k=length))

def make_qr_base64(data: str) -> str:
    img = qrcode.make(data)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"

# ---------- PyQt App ----------
class LicenseApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("License Generator")
        self.resize(400, 250)

        self.printer = None  # پرینتر انتخابی کاربر

        self.title_label = QLabel("لایسنس ۳ ماهه رایگان")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold; text-align:center")
        self.title_label.setAlignment(Qt.AlignCenter)

        # فیلد عددی (QSpinBox)
        self.count_label = QLabel("تعداد لایسنس:")
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 100)
        self.count_spin.setValue(1)

        count_layout = QHBoxLayout()
        count_layout.addWidget(self.count_label)
        count_layout.addWidget(self.count_spin)

        self.select_printer_btn = QPushButton("انتخاب پرینتر")
        self.select_printer_btn.clicked.connect(self.select_printer)

        self.generate_print_btn = QPushButton("تولید، ذخیره و پرینت")
        self.generate_print_btn.clicked.connect(self.generate_and_print)

        layout = QVBoxLayout()
        layout.addWidget(self.title_label)
        layout.addLayout(count_layout)
        layout.addWidget(self.select_printer_btn)
        layout.addWidget(self.generate_print_btn)
        self.setLayout(layout)

    def select_printer(self):
        printer = QPrinter()
        dialog = QPrintDialog(printer, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.printer = printer
            QMessageBox.information(self, "پرینتر انتخاب شد", "پرینتر با موفقیت ذخیره شد.")

    def generate_and_print(self):
        if not self.printer:
            QMessageBox.warning(self, "خطا", "لطفاً ابتدا پرینتر را انتخاب کنید.")
            return

        count = self.count_spin.value()
        session = Session()
        new_keys = []

        for _ in range(count):
            new_key = generate_license_key()
            license_obj = License(license_key=new_key, created_at=datetime.utcnow())
            session.add(license_obj)
            new_keys.append(new_key)

        try:
            session.commit()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Database error", f"خطا در ذخیره‌سازی: {e}")
            return
        finally:
            session.close()

        # پرینت هر لایسنس به صورت جدا
        for key in new_keys:
            qr_b64 = make_qr_base64(key)

            html = f"""
            <html dir="rtl">
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Tahoma, sans-serif; text-align: center; }}
                    .license {{ margin: 30px 0; }}
                    .title {{ font-size: 16px; font-weight: bold; margin-bottom: 10px; }}
                    .license-code {{ font-size: 14px; font-weight: bolder; margin-top: 5px; color: black; }}
                    .site {{ font-size: 14px; font-weight: bolder; margin-top: 5px; color: black; }}
                </style>
            </head>
            <body>
                <div class="license">
                    <div class="title">لایسنس ۳ ماهه رایگان<br>نرم افزار حسابداری عدد.</div>
                    <img src="{qr_b64}" width="220" height="220" />
                    <div class="license-code">{key}</div>
                    <div class="site">دریافت نرم افزار</div>
                    <div class="site">www.bans.ir/adad</div>
                </div>
            </body>
            </html>
            """

            web = QWebEngineView()
            web.setHtml(html)

            def print_callback(success, k=key):
                if not success:
                    QMessageBox.warning(self, "خطا", f"پرینت لایسنس {k} انجام نشد.")

            def do_print():
                page = web.page()
                page.print(self.printer, print_callback)

            web.loadFinished.connect(lambda ok, w=web: do_print())

# ---------- Main ----------
def main():
    app = QApplication(sys.argv)
    window = LicenseApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
