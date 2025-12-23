from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from flask_login import UserMixin
import enum
# Import db và app từ QLTMG
from QLTMG import db, app


# 1. Định nghĩa các Enum
class UserRole(enum.Enum):
    ADMIN = 1
    TEACHER = 2


class Gender(enum.Enum):
    MALE = 1
    FEMALE = 2


# 2. Class Base
class Base(db.Model):
    __abstract__ = True
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), nullable=False)
    active = Column(Boolean, default=True)
    created_date = Column(DateTime, default=datetime.now())
    def __str__(self):
        return self.name


# 3. Các Models
class Regulation(db.Model):
    __tablename__ = 'regulation'
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(50), unique=True, nullable=False)
    value = Column(Float, default=0)
    description = Column(String(200))

    # [MỚI] Lưu ID người sửa đổi cuối cùng (Audit Trail)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=True)

    # Tạo quan hệ để truy vấn: regulation.user.name (để biết ai sửa)
    user = relationship('User', backref='regulations', lazy=True)


class ClassRoom(Base):
    __tablename__ = 'classroom'
    # ... (các cột cũ giữ nguyên) ...

    # --- THÊM 2 DÒNG NÀY ---
    # Liên kết với bảng User (Giáo viên)
    teacher_id = Column(Integer, ForeignKey('user.id'), nullable=True, unique=True)

    # Tạo quan hệ để sau này gọi: classroom.teacher.name
    teacher = relationship('User', backref='homeroom_classes', lazy=True)
    # -----------------------

    students = relationship('Student', backref='classroom', lazy=True)


class Student(Base):
    __tablename__ = 'student'
    # ... (Các cột cũ giữ nguyên) ...
    birth_date = Column(DateTime)
    gender = Column(Enum(Gender), default=Gender.FEMALE)
    parent_name = Column(String(150))
    phone = Column(String(20))

    # --- THÊM CỘT AVATAR ---
    # Link ảnh mặc định nếu không có ảnh
    avatar = Column(String(500), default="https://cdn-icons-png.flaticon.com/512/2922/2922510.png")
    # -----------------------

    class_id = Column(Integer, ForeignKey('classroom.id'), nullable=True)


class HealthRecord(db.Model):
    # ... giữ nguyên các cột cũ ...
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_date = Column(DateTime, default=datetime.now)

    weight = Column(Float, default=0)
    temperature = Column(Float, default=37)

    # --- THÊM DÒNG NÀY ---
    height = Column(Float, default=0)
    # ---------------------

    note = Column(String(255))
    student_id = Column(Integer, ForeignKey(Student.id), nullable=False)


class User(Base, UserMixin):
    __tablename__ = 'user'
    username = Column(String(150), unique=True, nullable=False)
    password = Column(String(150), nullable=False)
    email = Column(String(150), unique=True)  # Email nên là duy nhất
    avatar = Column(String(300),default="https://res.cloudinary.com/dy1unykph/image/upload/v1740037805/apple-iphone-16-pro-natural-titanium_lcnlu2.webp")
    role = Column(Enum(UserRole), default=UserRole.TEACHER)
    receipts_created = relationship('Receipt', backref='creator', lazy=True)


class Notification(db.Model):
    __tablename__ = 'notification'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    created_date = Column(DateTime, default=datetime.now)
    active = Column(Boolean, default=True)

    # [MỚI] Lưu ID người đăng thông báo
    user_id = Column(Integer, ForeignKey('user.id'), nullable=True)

    # Tạo quan hệ để truy vấn: notification.creator.name (để biết ai đăng)
    creator = relationship('User', backref='notifications', lazy=True)

    def __str__(self):
        return self.title


class Receipt(db.Model):
    __tablename__ = 'receipt'
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_date = Column(DateTime, default=datetime.now())

    # Lưu tháng thu phí (VD: "04/2025")
    month = Column(String(20), nullable=False)

    # 1. Các khoản chi tiết
    meal_days = Column(Integer, default=22)  # Số ngày ăn (mặc định 22)
    base_tuition = Column(Float, default=0)  # Học phí cơ bản (lưu lại giá tại thời điểm thu)
    meal_total = Column(Float, default=0)  # Thành tiền ăn (ngày * giá)
    discount = Column(Float, default=0)  # Tiền miễn giảm

    # 2. Tổng kết tiền
    total_due = Column(Float, default=0)  # PHẢI THU (Tổng cộng sau khi trừ miễn giảm)
    paid_amount = Column(Float, default=0)  # ĐÃ THU (Số tiền phụ huynh thực đóng)

    # 3. Trạng thái
    # False: Chưa hoàn thành (Còn nợ), True: Đã hoàn thành (Hết nợ)
    status = Column(Boolean, default=False)

    # Khóa ngoại
    student_id = Column(Integer, ForeignKey('student.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)  # Người thu tiền
    student = relationship('Student', backref='receipts', lazy=True)
    # Tính toán số tiền nợ (Property ảo, không lưu DB nhưng gọi được như biến)
    @property
    def debt(self):
        return self.total_due - self.paid_amount


class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, default=datetime.now)  # Ngày điểm danh

    # Trạng thái: 1=Có mặt, 0=Vắng, -1=Vắng có phép
    status = Column(Integer, default=1)
    note = Column(String(255), nullable=True)  # Ghi chú (lý do vắng)

    student_id = Column(Integer, ForeignKey('student.id'), nullable=False)

    # Quan hệ để truy vấn ngược nếu cần
    student = relationship('Student', backref='attendance_records', lazy=True)


# --- TẠO DỮ LIỆU MẪU ---
if __name__ == "__main__":
    import hashlib

    # Sử dụng app_context của app đã import
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Tạo Quy định mẫu
        regulations_data = [
            {'key': 'MAX_STUDENT', 'value': 25, 'desc': 'Sĩ số tối đa một lớp'},
            {'key': 'BASE_TUITION', 'value': 1500000, 'desc': 'Học phí cơ bản hàng tháng'},
            {'key': 'MEAL_PRICE', 'value': 25000, 'desc': 'Tiền ăn một ngày'}
        ]

        for reg in regulations_data:
            if not Regulation.query.filter_by(key=reg['key']).first():
                r = Regulation(key=reg['key'], value=reg['value'], description=reg['desc'])
                db.session.add(r)
                print(f"--> Đã thêm quy định: {reg['key']}")

        # Tạo Admin mẫu
        if not User.query.filter_by(username='admin').first():
            password_hashed = hashlib.md5("123".encode("utf-8")).hexdigest()
            admin_user = User(
                name="Quản Trị Viên",
                username="admin",
                password=password_hashed,
                role=UserRole.ADMIN,
            )
            db.session.add(admin_user)
            print("--> Đã tạo tài khoản Admin")

        db.session.commit()