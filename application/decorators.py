from functools import wraps
from django.shortcuts import redirect
from django.conf import settings


def admin_login_required(view_func):
    """管理画面へのアクセスにパスワード認証を要求するデコレータ"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # セッションに認証済みフラグがあるか確認
        if request.session.get('admin_authenticated', False):
            return view_func(request, *args, **kwargs)
        
        # 未認証の場合はログイン画面にリダイレクト（現在のURLをnextパラメータに含める）
        from django.urls import reverse
        login_url = reverse('application:admin_login')
        current_path = request.get_full_path()
        if current_path != login_url:
            login_url = f"{login_url}?next={current_path}"
        return redirect(login_url)
    
    return _wrapped_view

