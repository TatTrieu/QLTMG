from sqlalchemy import func, desc
from models import User, Student, ClassRoom, HealthRecord, Receipt, Regulation, UserRole, Gender, Notification
from datetime import datetime
from QLTMG import db
import hashlib

def auth_user(username, password):

    if username and password:
        # Mã hóa mật khẩu đầu vào sang MD5
        password = hashlib.md5(password.strip().encode('utf-8')).hexdigest()

        # Truy vấn SQL: SELECT * FROM user WHERE username = ? AND password = ?
        return User.query.filter(User.username == username.strip(),
                                 User.password == password).first()
    return None

def get_class_by_id(class_id):
    """Lấy thông tin chi tiết một lớp học (bao gồm cả GVCN)"""
    return ClassRoom.query.get(class_id)

def get_class_by_teacher(user_id):
    """Tìm lớp học mà user_id đang làm chủ nhiệm"""
    return ClassRoom.query.filter_by(teacher_id=user_id).first()

def get_user_by_id(user_id):
    """Lấy thông tin User theo ID (Dùng cho Flask-Login lưu session)"""
    return User.query.get(user_id)

# --- 2. QUẢN LÝ LỚP & HỌC SINH ---
def load_classes():
    return ClassRoom.query.all()


# --- 3. QUẢN LÝ SỨC KHỎE ---
def get_health_list_with_stats(kw=None, class_id=None):
    """
    Lấy danh sách học sinh kèm theo thông số so sánh: Cũ vs Mới
    """
    # Lấy tất cả học sinh đang đi học
    query = Student.query.filter(Student.active == True)

    if kw:
        query = query.filter(Student.name.contains(kw))
    if class_id:
        query = query.filter(Student.class_id == class_id)

    students = query.all()
    result = []

    for s in students:
        # Lấy 2 bản ghi sức khỏe gần nhất của học sinh này
        records = HealthRecord.query.filter_by(student_id=s.id) \
            .order_by(desc(HealthRecord.created_date)) \
            .limit(2).all()

        # Mặc định chưa có dữ liệu
        new_data = None
        old_data = None
        diff_temp = None

        if records:
            # records[0] là MỚI NHẤT
            new_data = records[0]

            # records[1] là CŨ HƠN (Lần đo trước)
            if len(records) > 1:
                old_data = records[1]
                # Tính chênh lệch nhiệt độ
                diff_temp = round(new_data.temperature - old_data.temperature, 1)

        result.append({
            'student': s,
            'class_name': s.classroom.name if s.classroom else 'Chưa xếp lớp',
            'new_rec': new_data,  # Object HealthRecord mới
            'old_rec': old_data,  # Object HealthRecord cũ
            'diff_temp': diff_temp  # Số chênh lệch
        })

    return result


def update_health_record(health_id, height, weight, temperature, note):
    try:
        hr = HealthRecord.query.get(health_id)
        if hr:
            # Lưu Chiều cao
            hr.height = float(height) if height else 0

            # Lưu Cân nặng
            hr.weight = float(weight) if weight else 0

            # Lưu Nhiệt độ
            hr.temperature = float(temperature) if temperature else 37.0

            # Lưu Ghi chú
            hr.note = note

            db.session.commit()
            return True
    except Exception as ex:
        print(f"Lỗi update sức khỏe: {ex}")
        db.session.rollback()
    return False

def save_health_record(student_id, weight, height, temperature, note):
    # r = HealthRecord(student_id=student_id, weight=weight, temperature=temperature, note=note)
    # db.session.add(r)
    # db.session.commit()
    # return r
    h = HealthRecord(student_id=student_id, weight=weight, height=height, temperature=temperature, note=note)

    db.session.add(h)
    db.session.commit()
    return True


def add_new_health_checkup(student_id, height, weight, temperature, note):
    """
    Luôn TẠO MỚI bản ghi để lưu lịch sử (Không ghi đè)
    """
    try:
        # Xử lý dữ liệu đầu vào (tránh lỗi None)
        h = float(height) if height else 0
        w = float(weight) if weight else 0
        t = float(temperature) if temperature else 37.0

        # Tạo bản ghi mới hoàn toàn
        new_record = HealthRecord(
            student_id=student_id,
            height=h,
            weight=w,
            temperature=t,
            note=note
            # created_date tự động lấy now() nhờ model
        )

        db.session.add(new_record)
        db.session.commit()
        return True
    except Exception as ex:
        print(f"Lỗi thêm sức khỏe: {ex}")
        db.session.rollback()
        return False


# --- 4. HỌC PHÍ & QUY ĐỊNH ---
def get_regulation(key):
    r = Regulation.query.filter_by(key=key).first()
    return r.value if r else 0

def calculate_tuition_fee(meal_days):
    base_fee = get_regulation('BASE_TUITION')
    meal_price = get_regulation('MEAL_PRICE')
    return base_fee + (meal_price * meal_days)

def load_receipts(month=None):
    query = Receipt.query
    if month:
        query = query.filter(Receipt.month == month)
    return query.all()

# --- 5. THỐNG KÊ ---
def count_students():
    return Student.query.count()

def count_students_by_class():
    return db.session.query(ClassRoom.name, func.count(Student.id)) \
        .join(Student, Student.class_id == ClassRoom.id, isouter=True) \
        .group_by(ClassRoom.name).all()


def add_user(name, username, password, email=None, avatar=None):
    """Tạo người dùng mới. Trả về True nếu thành công, False nếu lỗi trùng."""
    password = hashlib.md5(password.strip().encode('utf-8')).hexdigest()

    if not avatar:
        avatar = "https://cdn-icons-png.flaticon.com/512/149/149071.png"

    u = User(name=name,
             username=username.strip(),
             password=password,
             email=email.strip() if email else None,
             avatar=avatar,
             role=UserRole.TEACHER) # Mặc định là giáo viên

    try:
        db.session.add(u)
        db.session.commit()
        return True
    except Exception as ex:
        print(f"Lỗi đăng ký user: {ex}")
        db.session.rollback() # Hoàn tác nếu lỗi trùng
        return False


def add_student(name, birth_date, gender, parent_name, phone, class_id, avatar=None, creator_id=None):
    try:
        # 1. TẠO HỌC SINH MỚI
        new_student = Student(name=name, parent_name=parent_name, phone=phone, class_id=class_id)

        # Xử lý ngày sinh
        if birth_date:
            new_student.birth_date = datetime.strptime(birth_date, "%Y-%m-%d")

        # Xử lý giới tính
        if gender == 'MALE':
            new_student.gender = Gender.MALE
        elif gender == 'FEMALE':
            new_student.gender = Gender.FEMALE

        # Xử lý Avatar (Nếu không nhập thì dùng ảnh mặc định trong Model)
        if avatar and avatar.strip():
            new_student.avatar = avatar

        db.session.add(new_student)

        # --- QUAN TRỌNG: Đẩy dữ liệu lên để lấy được ID của học sinh mới ---
        db.session.flush()

        # 2. TẠO HÓA ĐƠN HỌC PHÍ MẶC ĐỊNH CHO THÁNG NÀY
        # Lấy quy định tiền
        reg_tuition = Regulation.query.filter_by(key='BASE_TUITION').first()
        reg_meal = Regulation.query.filter_by(key='MEAL_PRICE').first()

        base_price = reg_tuition.value if reg_tuition else 0
        meal_price = reg_meal.value if reg_meal else 0

        # Các thông số mặc định
        current_month = datetime.now().strftime('%m/%Y')
        default_days = 22
        meal_total = default_days * meal_price
        total_due = base_price + meal_total

        # Tạo hóa đơn
        if creator_id:  # Chỉ tạo nếu có thông tin người tạo
            new_receipt = Receipt(
                student_id=new_student.id,
                month=current_month,
                meal_days=default_days,
                base_tuition=base_price,
                meal_total=meal_total,
                discount=0,
                total_due=total_due,
                paid_amount=0,
                status=False,  # Chưa đóng
                user_id=creator_id
            )
            db.session.add(new_receipt)

        # 3. Lưu tất cả vào DB
        db.session.commit()
        return True, "Thêm học sinh và tạo hóa đơn thành công!"

    except Exception as ex:
        print(f"Lỗi add_student: {ex}")
        db.session.rollback()
        return False, f"Lỗi hệ thống: {str(ex)}"

def delete_student(student_id):

    try:
        s = Student.query.get(student_id)
        if s:
            s.active = False # Đánh dấu là đã nghỉ học
            db.session.commit()
            return True
    except Exception as ex:
        print(ex)
    return False


def update_student(student_id, name, birth_date, gender, parent_name, phone, class_id, avatar=None):
    try:
        s = Student.query.get(student_id)
        if s:
            s.name = name
            s.birth_date = datetime.strptime(birth_date, "%Y-%m-%d") if birth_date else None

            # Xử lý Gender (Enum)
            if gender == 'MALE':
                s.gender = Gender.MALE
            elif gender == 'FEMALE':
                s.gender = Gender.FEMALE

            s.parent_name = parent_name
            s.phone = phone
            s.class_id = class_id

            # --- THÊM ĐOẠN NÀY ĐỂ LƯU AVATAR ---
            if avatar and avatar.strip():  # Nếu có nhập link ảnh
                s.avatar = avatar
            # -----------------------------------

            db.session.commit()
            return True
    except Exception as ex:
        print(f"Lỗi update student: {ex}")
        return False
    return False


def load_students(kw=None, class_id=None):
    # Chỉ lấy học sinh có active = True
    query = Student.query.filter(Student.active == True)

    if kw:
        query = query.filter(Student.name.contains(kw))

    if class_id:
        query = query.filter(Student.class_id == class_id)

    return query.all()

def get_student_by_id(student_id):
    return Student.query.get(student_id)

def get_settings():
    """
    Lấy tất cả quy định hệ thống và trả về dạng Dictionary
    Ví dụ: {'MAX_STUDENT': 25, 'BASE_TUITION': 1500000}
    """
    regs = Regulation.query.all()
    return {r.key: r.value for r in regs}


def update_settings(config_data):
    """
    Cập nhật quy định.
    config_data: {'MAX_STUDENT': '30', ...}
    """
    try:
        for key, value in config_data.items():
            # Tìm dòng quy định theo Key
            reg = Regulation.query.filter_by(key=key).first()
            if reg:
                # Cập nhật giá trị mới (ép kiểu int cho an toàn)
                reg.value = int(value)

        db.session.commit()
        return True
    except Exception as ex:
        print(f"Lỗi update settings: {ex}")
        db.session.rollback()
        return False


def update_user_profile(user_id, name, email, avatar=None, new_password=None):
    """Cập nhật thông tin profile: Tên, Email, Avatar và Mật khẩu mới"""
    try:
        u = User.query.get(user_id)
        if u:
            u.name = name.strip()
            u.email = email.strip() if email else None

            if avatar:
                u.avatar = avatar.strip()

            # --- XỬ LÝ ĐỔI MẬT KHẨU ---
            if new_password:
                # Mã hóa MD5 trước khi lưu (giống lúc đăng ký)
                hashed_pass = hashlib.md5(new_password.strip().encode('utf-8')).hexdigest()
                u.password = hashed_pass
            # --------------------------

            db.session.commit()
            return True
    except Exception as ex:
        print(f"Lỗi update profile: {ex}")
        db.session.rollback()
    return False


def stats_revenue_by_month(year=None):
    if not year:
        year = datetime.now().year

    # Sửa thành paid_amount (số tiền thực tế đã thu)
    return db.session.query(Receipt.month, func.sum(Receipt.paid_amount)) \
        .filter(func.extract('year', Receipt.created_date) == year) \
        .group_by(Receipt.month) \
        .order_by(Receipt.month).all()

def stats_gender():
    """
    Thống kê số lượng học sinh theo giới tính (Nam/Nữ)
    Trả về: [('MALE', 10), ('FEMALE', 15)]
    """
    return db.session.query(Student.gender, func.count(Student.id))\
             .filter(Student.active == True)\
             .group_by(Student.gender).all()

def get_health_alerts():
    """
    Lấy danh sách 5 học sinh có nhiệt độ cao (> 37.5 độ) gần nhất
    để hiển thị cảnh báo ngay trang chủ.
    """
    return HealthRecord.query.join(Student)\
                       .filter(Student.active == True, HealthRecord.temperature > 37.5)\
                       .order_by(HealthRecord.created_date.desc())\
                       .limit(5).all()


def load_notifications():
    """Lấy danh sách thông báo đang hiển thị (Mới nhất lên đầu)"""
    return Notification.query.filter(Notification.active == True)\
                             .order_by(Notification.created_date.desc()).all()

def add_notification(title, content):
    """Thêm thông báo mới"""
    try:
        n = Notification(title=title, content=content)
        db.session.add(n)
        db.session.commit()
        return True
    except Exception as ex:
        print(ex)
        return False

def delete_notification(notify_id):
    """Xóa thông báo (Ẩn đi)"""
    try:
        n = Notification.query.get(notify_id)
        if n:
            n.active = False
            db.session.commit()
            return True
    except Exception as ex:
        print(ex)
        return False


def get_user_by_email(email):
    """Tìm user bằng email"""
    return User.query.filter(User.email == email.strip()).first()

def update_password_by_email(email, new_password):
    """Cập nhật mật khẩu mới dựa trên email"""
    try:
        u = get_user_by_email(email)
        if u:
            # Mã hóa password
            import hashlib
            u.password = hashlib.md5(new_password.strip().encode('utf-8')).hexdigest()
            db.session.commit()
            return True
    except Exception as ex:
        print(ex)
    return False


def get_temp_comparison_stats():
    stats = []
    # Lấy tất cả học sinh đang đi học
    students = Student.query.filter(Student.active == True).all()

    for s in students:
        # Lấy 2 bản ghi sức khỏe mới nhất của học sinh đó, sắp xếp giảm dần theo ngày
        records = HealthRecord.query.filter_by(student_id=s.id) \
            .order_by(desc(HealthRecord.created_date)) \
            .limit(2).all()

        # Chỉ xử lý nếu có ít nhất 1 bản ghi
        if records:
            current = records[0]  # Mới nhất
            previous = records[1] if len(records) > 1 else None  # Cái cũ hơn (nếu có)

            diff = 0
            if previous:
                # Tính độ lệch: Mới - Cũ (Làm tròn 1 chữ số thập phân)
                diff = round(current.temperature - previous.temperature, 1)

            stats.append({
                'student_name': s.name,
                'class_name': s.classroom.name if s.classroom else 'Chưa xếp lớp',
                'new_date': current.created_date,
                'new_temp': current.temperature,
                'old_date': previous.created_date if previous else None,
                'old_temp': previous.temperature if previous else None,
                'diff': diff
            })

    return stats