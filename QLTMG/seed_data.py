from QLTMG import app, db
from models import User, UserRole, ClassRoom, Student, Gender, Regulation, Receipt
import hashlib
from datetime import datetime


def seed_database():
    with app.app_context():
        print("--- BẮT ĐẦU KHỞI TẠO DỮ LIỆU ---")

        # 1. TẠO DATABASE (NẾU CHƯA CÓ)
        db.create_all()

        # 2. TẠO QUY ĐỊNH
        regulations_data = [
            {'key': 'MAX_STUDENT', 'value': 25, 'desc': 'Sĩ số tối đa một lớp'},
            {'key': 'BASE_TUITION', 'value': 1500000, 'desc': 'Học phí cơ bản hàng tháng'},
            {'key': 'MEAL_PRICE', 'value': 25000, 'desc': 'Tiền ăn một ngày'}
        ]
        for reg in regulations_data:
            if not Regulation.query.filter_by(key=reg['key']).first():
                db.session.add(Regulation(key=reg['key'], value=reg['value'], description=reg['desc']))
        db.session.commit()
        print("1. Đã tạo Quy định")

        # 3. TẠO TÀI KHOẢN (ADMIN + GV)
        password_hashed = hashlib.md5("123".encode("utf-8")).hexdigest()

        # Admin
        if not User.query.filter_by(username='admin').first():
            db.session.add(User(name="Quản Trị Viên", username="admin", password=password_hashed,
                                email="admin@gmail.com", role=UserRole.ADMIN))

        # GV1
        gv1 = User.query.filter_by(username='gv1').first()
        if not gv1:
            gv1 = User(name="Cô Trần Thị Lan", username="gv1", password=password_hashed,
                       email="lan@gmail.com", role=UserRole.TEACHER)
            db.session.add(gv1)

        # GV2
        gv2 = User.query.filter_by(username='gv2').first()
        if not gv2:
            gv2 = User(name="Cô Nguyễn Thu Mai", username="gv2", password=password_hashed,
                       email="mai@gmail.com", role=UserRole.TEACHER)
            db.session.add(gv2)

        db.session.commit()
        print("2. Đã tạo Admin và Giáo viên")

        # 4. TẠO LỚP HỌC (Lấy lại GV từ DB để chắc chắn có ID)
        gv1 = User.query.filter_by(username='gv1').first()
        gv2 = User.query.filter_by(username='gv2').first()

        class1 = ClassRoom.query.filter_by(name="Mầm 1").first()
        if not class1:
            class1 = ClassRoom(name="Mầm 1", teacher_id=gv1.id)
            db.session.add(class1)

        class2 = ClassRoom.query.filter_by(name="Chồi 1").first()
        if not class2:
            class2 = ClassRoom(name="Chồi 1", teacher_id=gv2.id)
            db.session.add(class2)

        db.session.commit()
        print("3. Đã tạo Lớp học")

        # 5. TẠO HỌC SINH (Chỉ tạo nếu lớp chưa có đủ học sinh)
        # Lấy lại Class từ DB để chắc chắn có ID
        c1 = ClassRoom.query.filter_by(name="Mầm 1").first()
        c2 = ClassRoom.query.filter_by(name="Chồi 1").first()

        # Dữ liệu mẫu
        students_data = [
            # Lớp Mầm 1
            {"name": "Nguyễn Văn An", "gender": Gender.MALE, "dob": "2021-05-15", "parent": "Anh Bình",
             "phone": "0901234567", "class_obj": c1},
            {"name": "Trần Thị Bống", "gender": Gender.FEMALE, "dob": "2021-08-20", "parent": "Chị Hoa",
             "phone": "0902345678", "class_obj": c1},
            {"name": "Lê Hoàng Cường", "gender": Gender.MALE, "dob": "2021-12-10", "parent": "Anh Dũng",
             "phone": "0903456789", "class_obj": c1},
            # Lớp Chồi 1
            {"name": "Phạm Ngọc Diệp", "gender": Gender.FEMALE, "dob": "2020-02-14", "parent": "Chị Lan",
             "phone": "0904567890", "class_obj": c2},
            {"name": "Hoàng Minh Đức", "gender": Gender.MALE, "dob": "2020-06-01", "parent": "Anh Tuấn",
             "phone": "0905678901", "class_obj": c2},
            {"name": "Vũ Thảo Vy", "gender": Gender.FEMALE, "dob": "2020-10-30", "parent": "Chị Mai",
             "phone": "0906789012", "class_obj": c2}
        ]

        # Lấy đơn giá để tạo hóa đơn
        reg_base = Regulation.query.filter_by(key='BASE_TUITION').first().value
        reg_meal = Regulation.query.filter_by(key='MEAL_PRICE').first().value
        current_month = datetime.now().strftime('%m/%Y')
        count_new = 0

        for s in students_data:
            # Kiểm tra xem học sinh này đã có trong DB chưa (tránh trùng)
            exist = Student.query.filter_by(name=s['name'], parent_name=s['parent']).first()

            if not exist:
                new_s = Student(
                    name=s["name"],
                    gender=s["gender"],
                    birth_date=datetime.strptime(s["dob"], "%Y-%m-%d"),
                    parent_name=s["parent"],
                    phone=s["phone"],
                    class_id=s["class_obj"].id
                )
                db.session.add(new_s)
                db.session.flush()  # Để lấy ID

                # Tạo hóa đơn
                receipt = Receipt(
                    student_id=new_s.id,
                    month=current_month,
                    meal_days=22,
                    base_tuition=reg_base,
                    meal_total=22 * reg_meal,
                    discount=0,
                    total_due=reg_base + (22 * reg_meal),
                    paid_amount=0,
                    status=False,
                    user_id=1  # Admin
                )
                db.session.add(receipt)
                count_new += 1

        db.session.commit()
        print(f"4. Đã thêm mới {count_new} học sinh thành công!")
        print("--- HOÀN TẤT ---")


if __name__ == "__main__":
    seed_database()