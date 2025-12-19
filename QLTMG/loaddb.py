import json
import hashlib
from datetime import datetime
from QLTMG import app, db
from models import User, UserRole, Regulation, ClassRoom, Student, Gender, HealthRecord


# Hàm hỗ trợ đọc file JSON
def read_json(file_path):
    try:
        with open(file_path, encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Lỗi đọc file {file_path}: {e}")
        return []


def load_data():
    print("--- BẮT ĐẦU NẠP DỮ LIỆU ---")

    # 1. NẠP QUY ĐỊNH
    regulations = read_json('data/regulations.json')  # Sửa đường dẫn nếu bạn để file ở chỗ khác
    for reg in regulations:
        if not Regulation.query.filter_by(key=reg['key']).first():
            r = Regulation(key=reg['key'], value=reg['value'], description=reg['desc'])
            db.session.add(r)
            print(f"+ Đã thêm quy định: {reg['key']}")

    # 2. NẠP USER
    users = read_json('data/users.json')
    for u in users:
        if not User.query.filter_by(username=u['username']).first():
            role_enum = UserRole[u['role']]  # Chuyển string "ADMIN" sang Enum

            user = User(
                name=u['name'],
                username=u['username'],
                password=hashlib.md5(u['password'].encode('utf-8')).hexdigest(),
                role=role_enum,
                avatar=u.get('avatar')
            )
            db.session.add(user)
            print(f"+ Đã thêm user: {u['username']}")

    # 3. NẠP LỚP HỌC & HỌC SINH
    classes = read_json('data/classes.json')
    for cls_data in classes:
        # Tạo lớp nếu chưa có
        classroom = ClassRoom.query.filter_by(name=cls_data['name']).first()
        if not classroom:
            classroom = ClassRoom(name=cls_data['name'])
            db.session.add(classroom)
            db.session.commit()  # Commit để lấy ID lớp
            print(f"+ Đã tạo lớp: {cls_data['name']}")

        # Thêm học sinh
        for s in cls_data.get('students', []):
            exists = Student.query.filter_by(name=s['name'], parent_name=s['parent_name']).first()
            if not exists:
                bdate = datetime.strptime(s['birth_date'], '%Y-%m-%d')
                gender_enum = Gender[s['gender']]

                student = Student(
                    name=s['name'],
                    birth_date=bdate,
                    gender=gender_enum,
                    parent_name=s['parent_name'],
                    phone=s['phone'],
                    class_id=classroom.id
                )
                db.session.add(student)
                print(f"  - Đã thêm bé: {s['name']}")

    db.session.commit()
    print("--- HOÀN TẤT ---")


def load_health():
    """Đọc và nạp dữ liệu Sức khỏe từ health.json"""
    print("\n--- NẠP DỮ LIỆU SỨC KHỎE ---")
    data = read_json('data/health.json')

    for item in data:
        # 1. Tìm học sinh trong DB dựa vào tên và phụ huynh
        student = Student.query.filter_by(
            name=item['student_name'],
            parent_name=item['parent_name']
        ).first()

        if student:
            for record in item['records']:
                # Chuyển đổi ngày tháng
                rec_date = datetime.strptime(record['date'], '%Y-%m-%d')

                # Kiểm tra xem đã có bản ghi sức khỏe ngày này chưa (tránh trùng)
                # Lưu ý: Logic này check đơn giản, thực tế có thể check kỹ hơn
                exists = HealthRecord.query.filter(
                    HealthRecord.student_id == student.id,
                    HealthRecord.created_date == rec_date
                ).first()

                if not exists:
                    hr = HealthRecord(
                        student_id=student.id,
                        created_date=rec_date,
                        weight=record['weight'],
                        temperature=record['temperature'],
                        note=record['note']
                    )
                    db.session.add(hr)
                    print(f"+ Đã thêm sức khỏe cho bé: {student.name} (Ngày {record['date']})")
        else:
            print(f"!!! Không tìm thấy học sinh: {item['student_name']} (Con của {item['parent_name']})")

    db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Tạo bảng trước nếu chưa có
        load_data()
        load_health()