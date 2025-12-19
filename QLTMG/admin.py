from flask import redirect, url_for
from flask_admin import Admin, AdminIndexView, expose, BaseView
from flask_admin.contrib.sqla import ModelView
from flask_admin.theme import Bootstrap4Theme
from flask_login import current_user, logout_user

# Import các Models của trường mầm non
from models import User, UserRole, Student, ClassRoom, Regulation, Receipt
# Import app và db từ package QLTMG
from QLTMG import app, db
import dao


# 1. Class cơ sở: Kiểm tra quyền Admin
class AuthenticatedModelView(ModelView):
    def is_accessible(self):
        # Chỉ cho phép Admin truy cập
        return current_user.is_authenticated and current_user.role == UserRole.ADMIN

    def inaccessible_callback(self, name, **kwargs):
        # Nếu không phải Admin thì đá về trang đăng nhập
        return redirect(url_for('login_process'))


# 2. Các View quản lý cụ thể
class UserView(AuthenticatedModelView):
    column_list = ['id', 'name', 'username', 'role', 'active']
    column_searchable_list = ['name', 'username']
    column_filters = ['role']
    can_create = True
    can_edit = True

    # Form hiển thị tên tiếng Việt
    column_labels = {
        'name': 'Họ tên',
        'username': 'Tài khoản',
        'role': 'Vai trò',
        'active': 'Kích hoạt'
    }


class StudentView(AuthenticatedModelView):
    column_list = ['id', 'name', 'birth_date', 'gender', 'parent_name', 'phone', 'classroom']
    column_searchable_list = ['name', 'parent_name']
    column_filters = ['classroom']
    column_labels = {
        'name': 'Tên trẻ',
        'birth_date': 'Ngày sinh',
        'gender': 'Giới tính',
        'parent_name': 'Phụ huynh',
        'phone': 'SĐT',
        'classroom': 'Lớp học'
    }


class ClassRoomView(AuthenticatedModelView):
    column_list = ['id', 'name', 'students']
    column_labels = {'name': 'Tên lớp', 'students': 'Danh sách trẻ'}


class RegulationView(AuthenticatedModelView):
    column_list = ['key', 'value', 'description']
    can_create = False  # Quy định hệ thống hạn chế tạo mới bừa bãi
    can_delete = False
    column_labels = {'key': 'Mã', 'value': 'Giá trị', 'description': 'Mô tả'}


# 3. View Đăng xuất trong Admin
class LogoutView(BaseView):
    @expose('/')
    def index(self):
        logout_user()
        return redirect(url_for('login_process'))

    def is_accessible(self):
        return current_user.is_authenticated


# 4. View Trang chủ Admin (Dashboard thống kê)
class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        # Lấy thống kê số học sinh theo lớp từ DAO
        stats = dao.count_students_by_class()
        return self.render('admin/index.html', class_stats=stats)


# 5. Khởi tạo Admin
admin = Admin(app=app, name="E-COMMERCE", theme=Bootstrap4Theme(), index_view=MyAdminIndexView())


# Thêm các trang quản lý vào menu
admin.add_view(UserView(User, db.session, name='Người dùng'))
admin.add_view(ClassRoomView(ClassRoom, db.session, name='Lớp học'))
admin.add_view(StudentView(Student, db.session, name='Học sinh'))
admin.add_view(RegulationView(Regulation, db.session, name='Quy định'))
admin.add_view(AuthenticatedModelView(Receipt, db.session, name='Hóa đơn'))
admin.add_view(LogoutView(name='Đăng xuất'))