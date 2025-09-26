import random
import sys
import secrets
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
def generate_license_key(parts: int = 4, part_len: int = 5) -> str:
    """Generate a random string with letters and numbers."""
    characters = string.ascii_uppercase + string.digits  # A-Z, a-z, 0-9
    return ''.join(random.choices(characters, k=16))

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
        self.resize(400, 200)

        self.printer = None  # پرینتر انتخابی کاربر

        self.title_label = QLabel("لایسنس ۳ ماهه رایگان")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold; text-align:center")
        self.title_label.setAlignment(Qt.AlignCenter)

        self.select_printer_btn = QPushButton("انتخاب پرینتر")
        self.select_printer_btn.clicked.connect(self.select_printer)

        self.generate_print_btn = QPushButton("تولید، ذخیره و پرینت")
        self.generate_print_btn.clicked.connect(self.generate_and_print)

        layout = QVBoxLayout()
        layout.addWidget(self.title_label)
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

        session = Session()
        # تولید کلید
        new_key = generate_license_key()
        license_obj = License(license_key=new_key, created_at=datetime.utcnow())
        session.add(license_obj)

        try:
            session.commit()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Database error", f"خطا در ذخیره‌سازی: {e}")
            return
        finally:
            session.close()

        # ساخت HTML برای پرینت
        qr_b64 = make_qr_base64(new_key)
        html = f"""
        <html dir="rtl">
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Tahoma, sans-serif; text-align: center; }}
                .license {{ margin: 30px 0; }}
                .title {{ font-size: 16px; font-weight: bold; margin-bottom: 10px; }}
                .license-code {{ font-size: 14px; margin-top: 5px; }}
                .site {{ font-size: 14px; font-weight: bolder; margin-top: 5px; color: black; }}
            </style>
        </head>
        <body>
            <div class="license">
                <div class="title">لایسنس ۳ ماهه رایگان</br> نرم افزار حسابداری عدد.</div>
                
                <img src="{qr_b64}" width="120" height="120" />
                <div class="license-code">{new_key}</div>
                <div class="site">www.bans.ir</div>
            </div>
        </body>
        </html>
        """

        web = QWebEngineView()
        web.setHtml(html)

        def print_callback(success):
            if success:
                QMessageBox.information(self, "پرینت شد", "لایسنس با موفقیت چاپ شد.")
            else:
                QMessageBox.warning(self, "خطا", "پرینت انجام نشد.")

        def do_print():
            page = web.page()
            page.print(self.printer, print_callback)

        web.loadFinished.connect(lambda ok: do_print())

# ---------- Main ----------
def main():
    app = QApplication(sys.argv)
    window = LicenseApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
