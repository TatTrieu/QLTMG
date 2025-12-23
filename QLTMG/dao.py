from sqlalchemy import func, desc
from models import User, Student, ClassRoom, HealthRecord, Receipt, Regulation, UserRole, Gender, Notification, \
    Attendance
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


def check_class_capacity(class_id):
    """
    Kiểm tra lớp học còn chỗ trống không.
    Trả về: True (Còn chỗ), False (Đã đầy)
    """
    if not class_id: return True  # Chưa xếp lớp thì không tính

    # 1. Lấy quy định Sĩ số tối đa
    reg = Regulation.query.filter_by(key='MAX_STUDENT').first()
    max_student = int(reg.value) if reg else 30  # Mặc định 30 nếu chưa cài

    # 2. Đếm số học sinh hiện tại của lớp (Chỉ tính học sinh đang Active)
    current_count = Student.query.filter(Student.class_id == class_id, Student.active == True).count()

    # 3. So sánh
    if current_count >= max_student:
        return False  # Đã đầy hoặc vượt quá
    return True


# --- Sửa lại hàm add_student ---
def add_student(name, birth_date, gender, parent_name, phone, class_id, avatar=None, creator_id=None):
    try:
        # [MỚI] KIỂM TRA SĨ SỐ TRƯỚC KHI THÊM
        if class_id and not check_class_capacity(class_id):
            return False, "Lớp này đã ĐỦ SĨ SỐ quy định! Vui lòng chọn lớp khác hoặc tăng giới hạn sĩ số."

        # ... (Phần code tạo new_student cũ giữ nguyên) ...
        new_student = Student(name=name, parent_name=parent_name, phone=phone, class_id=class_id)
        if birth_date: new_student.birth_date = datetime.strptime(birth_date, "%Y-%m-%d")
        if gender == 'MALE':
            new_student.gender = Gender.MALE
        elif gender == 'FEMALE':
            new_student.gender = Gender.FEMALE
        if avatar and avatar.strip(): new_student.avatar = avatar

        db.session.add(new_student)
        db.session.flush()  # Để lấy ID

        # ... (Phần tạo hóa đơn cũ giữ nguyên) ...
        # (Copy lại đoạn tạo Receipt từ code cũ của bạn vào đây)
        reg_tuition = Regulation.query.filter_by(key='BASE_TUITION').first()
        reg_meal = Regulation.query.filter_by(key='MEAL_PRICE').first()
        base_price = reg_tuition.value if reg_tuition else 0
        meal_price = reg_meal.value if reg_meal else 0
        current_month = datetime.now().strftime('%m/%Y')
        default_days = 22
        meal_total = default_days * meal_price
        total_due = base_price + meal_total

        if creator_id:
            new_receipt = Receipt(
                student_id=new_student.id, month=current_month, meal_days=default_days,
                base_tuition=base_price, meal_total=meal_total, discount=0,
                total_due=total_due, paid_amount=0, status=False, user_id=creator_id
            )
            db.session.add(new_receipt)

        db.session.commit()
        return True, "Thêm học sinh thành công!"

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
            # [MỚI] KIỂM TRA NẾU ĐỔI LỚP
            # Nếu có chọn lớp mới VÀ lớp mới khác lớp cũ
            if class_id and str(s.class_id) != str(class_id):
                if not check_class_capacity(class_id):
                    return False, "Lớp chuyển đến đã ĐỦ SĨ SỐ! Không thể chuyển học sinh vào."

            # ... (Các lệnh gán dữ liệu cũ giữ nguyên) ...
            s.name = name
            s.birth_date = datetime.strptime(birth_date, "%Y-%m-%d") if birth_date else None
            if gender == 'MALE': s.gender = Gender.MALE
            elif gender == 'FEMALE': s.gender = Gender.FEMALE
            s.parent_name = parent_name
            s.phone = phone
            s.class_id = class_id
            if avatar and avatar.strip(): s.avatar = avatar

            db.session.commit()
            return True, "Cập nhật thông tin thành công!" # Trả về Tuple (True, Msg)
    except Exception as ex:
        print(f"Lỗi update student: {ex}")
        return False, "Lỗi hệ thống khi cập nhật!"
    return False, "Không tìm thấy học sinh!"


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
    Trả về: (True/False, Message)
    """
    warning_msg = ""
    try:
        for key, value in config_data.items():
            reg = Regulation.query.filter_by(key=key).first()
            if reg:
                reg.value = float(value)

        db.session.commit()

        # [MỚI] SAU KHI LƯU, KIỂM TRA LẠI CÁC LỚP
        if 'MAX_STUDENT' in config_data:
            new_max = float(config_data['MAX_STUDENT'])

            # Tìm các lớp có sĩ số > new_max
            overloaded_classes = db.session.query(ClassRoom.name) \
                .join(Student).filter(Student.active == True) \
                .group_by(ClassRoom.id) \
                .having(func.count(Student.id) > new_max).all()

            if overloaded_classes:
                # Tạo danh sách tên lớp: "Mầm 1, Chồi 2..."
                names = ", ".join([c[0] for c in overloaded_classes])
                warning_msg = f" | CẢNH BÁO: Các lớp ({names}) hiện đang vượt quá quy định mới ({int(new_max)} em). Vui lòng chuyển bớt học sinh!"

        return True, "Đã cập nhật cấu hình thành công!" + warning_msg

    except Exception as ex:
        print(f"Lỗi update settings: {ex}")
        db.session.rollback()
        return False, "Lỗi Database! Không thể lưu cài đặt."


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


def get_dashboard_data(date_input_str, class_id=None):
    """
    Lấy dữ liệu thống kê cho Dashboard.
    - date_input_str: Chuỗi ngày định dạng 'YYYY-MM-DD' (Ví dụ: '2025-12-20')
    - class_id: ID lớp học (hoặc None nếu xem toàn trường)
    """
    data = {}

    try:
        # 1. XỬ LÝ NGÀY VÀ THÁNG
        # Chuyển chuỗi ngày thành đối tượng datetime
        current_date = datetime.strptime(date_input_str, '%Y-%m-%d')

        # Tự động suy ra THÁNG từ ngày đó (Để dùng cho thống kê học phí)
        # Ví dụ: Chọn ngày 20/12/2025 -> Lấy tháng '12/2025'
        current_month_str = current_date.strftime('%m/%Y')
        data['month_display'] = current_month_str

    except ValueError:
        # Phòng trường hợp ngày lỗi, mặc định lấy hôm nay
        current_date = datetime.now()
        current_month_str = current_date.strftime('%m/%Y')
        data['month_display'] = current_month_str

    # -----------------------------------------------------
    # 2. TỔNG SĨ SỐ HỌC SINH (Theo Lớp hoặc Toàn trường)
    # -----------------------------------------------------
    q_students = Student.query.filter(Student.active == True)
    if class_id:
        q_students = q_students.filter(Student.class_id == class_id)

    data['total_students'] = q_students.count()

    # -----------------------------------------------------
    # 3. THỐNG KÊ HỌC PHÍ (Dựa theo THÁNG chứa ngày đó)
    # -----------------------------------------------------
    q_receipts = Receipt.query.filter_by(month=current_month_str)

    # Nếu lọc theo lớp thì phải join bảng Student
    if class_id:
        q_receipts = q_receipts.join(Student).filter(Student.class_id == class_id)

    total_receipts = q_receipts.count()
    paid_count = q_receipts.filter(Receipt.status == True).count()
    unpaid_count = total_receipts - paid_count

    data['paid_count'] = paid_count
    data['unpaid_count'] = unpaid_count

    # -----------------------------------------------------
    # 4. THỐNG KÊ VẮNG (Dựa theo NGÀY CHÍNH XÁC)
    # -----------------------------------------------------
    # Lấy bảng điểm danh, lọc đúng ngày user chọn
    q_attendance = Attendance.query.filter(func.date(Attendance.date) == date_input_str)

    if class_id:
        q_attendance = q_attendance.join(Student).filter(Student.class_id == class_id)

    # Đếm số vắng KHÔNG phép (status = 0)
    absent_no = q_attendance.filter(Attendance.status == 0).count()

    # Đếm số vắng CÓ phép (status = -1)
    absent_yes = q_attendance.filter(Attendance.status == -1).count()

    # Tổng hợp lại
    data['absent_total'] = absent_no + absent_yes  # Tổng số vắng (hiển thị số to)
    data['absent_permission'] = absent_yes  # Số có phép (hiển thị chú thích nhỏ)

    # -----------------------------------------------------
    # 5. DANH SÁCH NỢ PHÍ (Top 5 em chưa đóng)
    # -----------------------------------------------------
    # Lấy danh sách hóa đơn chưa thanh toán (status=False)
    debtors = q_receipts.filter(Receipt.status == False).limit(5).all()
    data['debtors'] = debtors

    # -----------------------------------------------------
    # 6. TỶ LỆ GIỚI TÍNH
    # -----------------------------------------------------
    male_count = q_students.filter(Student.gender == Gender.MALE).count()
    female_count = data['total_students'] - male_count

    data['gender_male'] = male_count
    data['gender_female'] = female_count

    return data


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


def get_attendance_list(class_id, date_str):
    """
    Lấy danh sách học sinh kèm trạng thái điểm danh của ngày hôm đó.
    date_str: Định dạng 'YYYY-MM-DD'
    """
    # 1. Lấy tất cả học sinh trong lớp
    query = Student.query.filter(Student.active == True)
    if class_id:
        query = query.filter(Student.class_id == class_id)
    students = query.all()

    result = []
    # 2. Duyệt từng học sinh xem ngày đó đã điểm danh chưa
    for s in students:
        att = Attendance.query.filter(
            Attendance.student_id == s.id,
            func.date(Attendance.date) == date_str  # So sánh ngày
        ).first()

        result.append({
            'student': s,
            'status': att.status if att else 1,  # Mặc định là Có mặt (1) nếu chưa điểm danh
            'note': att.note if att else ''
        })

    return result


def save_attendance(student_id, date_str, status, note):
    try:
        # Kiểm tra xem đã có bản ghi của ngày hôm đó chưa
        att = Attendance.query.filter(
            Attendance.student_id == student_id,
            func.date(Attendance.date) == date_str
        ).first()

        if att:
            # Nếu có rồi -> Cập nhật
            att.status = int(status)
            att.note = note
        else:
            # Chưa có -> Tạo mới
            new_att = Attendance(
                student_id=student_id,
                date=datetime.strptime(date_str, '%Y-%m-%d'),
                status=int(status),
                note=note
            )
            db.session.add(new_att)

        db.session.commit()
        return True
    except Exception as ex:
        print(ex)
        db.session.rollback()
        return False


def count_attended_days(student_id, month_str):
    """
    Đếm số ngày đi học (status=1) của học sinh trong tháng (month_str: 'mm/yyyy')
    """
    try:
        # Chuyển chuỗi '12/2025' thành đối tượng ngày tháng
        dt = datetime.strptime(month_str, '%m/%Y')

        # Đếm số bản ghi trong bảng Attendance có status = 1 (Có mặt)
        count = Attendance.query.filter(
            Attendance.student_id == student_id,
            Attendance.status == 1,
            func.extract('month', Attendance.date) == dt.month,
            func.extract('year', Attendance.date) == dt.year
        ).count()

        return count
    except Exception as ex:
        print(f"Lỗi đếm ngày: {ex}")
        return 0


def auto_update_tuition_from_attendance(month, class_id=None):
    """
    Tự động cập nhật tiền ăn cho tất cả hóa đơn trong tháng dựa vào điểm danh
    """
    try:
        # 1. Lấy đơn giá tiền ăn hiện tại
        reg_meal = Regulation.query.filter_by(key='MEAL_PRICE').first()
        meal_price = reg_meal.value if reg_meal else 0

        # 2. Lấy danh sách hóa đơn của tháng đó
        query = Receipt.query.filter_by(month=month)

        # Nếu đang xem 1 lớp cụ thể thì chỉ cập nhật lớp đó cho nhanh
        if class_id and class_id != 'all' and class_id != '-1':
            query = query.join(Student).filter(Student.class_id == class_id)

        receipts = query.all()

        # 3. Duyệt từng hóa đơn để tính lại
        for r in receipts:
            # Đếm ngày đi học thực tế
            actual_days = count_attended_days(r.student_id, month)

            # --- QUAN TRỌNG: CHỈ CẬP NHẬT KHI ĐÃ CÓ DỮ LIỆU ĐIỂM DANH ---
            # (Để tránh trường hợp đầu tháng chưa điểm danh mà bị reset về 0)
            if actual_days > 0:
                # Cập nhật số ngày ăn
                r.meal_days = actual_days

                # Tính lại Thành tiền ăn = Số ngày * Giá 1 ngày
                r.meal_total = actual_days * meal_price

                # Tính lại Tổng tiền phải thu = Học phí CB + Tiền ăn - Miễn giảm
                r.total_due = r.base_tuition + r.meal_total - r.discount

                # Cập nhật trạng thái Nợ (Nếu Tổng thu <= Đã đóng thì là Hết nợ)
                if (r.total_due - r.paid_amount) <= 0:
                    r.status = True
                else:
                    r.status = False

        # Lưu thay đổi vào Database
        db.session.commit()

    except Exception as ex:
        print(f"Lỗi tự động cập nhật học phí: {ex}")