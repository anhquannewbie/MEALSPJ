from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.utils.translation import gettext_lazy as _

ACTION_VI = {
    'add':    _('Có thể thêm'),
    'change': _('Có thể sửa'),
    'delete': _('Có thể xoá'),
    'view':   _('Có thể xem'),
}

MODEL_VI = {
    'logentry':        _('nhật ký'),
    'permission':      _('quyền'),
    'group':           _('nhóm'),
    'user':            _('người dùng'),
    'contenttype':     _('loại nội dung'),
    'session':         _('phiên'),
    'student':         _('học sinh'),
    'mealrecord':      _('bản ghi bữa ăn'),
    'classroom':       _('lớp học'),
    'studentpayment':  _('thanh toán học sinh'),
    # … thêm model mới tại đây
}

class Command(BaseCommand):
    help = "Việt hoá cột name trong bảng auth_permission"

    def handle(self, *args, **kwargs):
        cnt = 0
        for perm in Permission.objects.all():
            if not perm.name.startswith("Can "):
                continue
            action, model = perm.codename.split("_", 1)
            vi_action = ACTION_VI.get(action)
            vi_model  = MODEL_VI.get(model, model)
            if vi_action:
                perm.name = f"{vi_action} {vi_model}"
                perm.save(update_fields=["name"])
                cnt += 1
        self.stdout.write(self.style.SUCCESS(f"Đã Việt‑hoá {cnt} quyền."))
