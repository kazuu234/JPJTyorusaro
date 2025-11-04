from django.contrib import admin
from django.shortcuts import redirect
from django.conf import settings
from django.contrib import messages
from .models import SubscriptionUser, SalonApplication, CSVUpload, DiscountApplication


class CustomAdminSite(admin.AdminSite):
    """カスタムAdminSite（パスワード認証のみ）"""
    site_header = '管理画面'
    site_title = '管理画面'
    index_title = '管理画面'
    
    def login(self, request, extra_context=None):
        """ログイン処理をカスタマイズ（パスワードのみ）"""
        from django.template.response import TemplateResponse
        
        # 既に認証済みの場合は管理画面にリダイレクト
        if request.session.get('admin_authenticated', False):
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url:
                return redirect(next_url)
            else:
                # 申し込み一覧にリダイレクト
                from django.urls import reverse
                return redirect(reverse('application:application_list'))
        
        # ログインフォームの処理
        if request.method == 'POST':
            password = request.POST.get('password', '').strip()
            
            # 設定ファイルのパスワードと比較
            admin_password = getattr(settings, 'ADMIN_PASSWORD', '11223456778899#JP')
            
            if password == admin_password:
                # 認証成功：セッションに認証済みフラグを設定
                request.session['admin_authenticated'] = True
                request.session.set_expiry(86400 * 7)  # 7日間有効
                messages.success(request, 'ログインしました。')
                
                # nextパラメータがある場合はそこにリダイレクト
                next_url = request.GET.get('next') or request.POST.get('next')
                if next_url:
                    return redirect(next_url)
                else:
                    # 申し込み一覧にリダイレクト
                    from django.urls import reverse
                    return redirect(reverse('application:application_list'))
            else:
                messages.error(request, 'パスワードが正しくありません。')
        
        # カスタムログインテンプレートを使用
        context = {
            'title': '管理画面ログイン',
            'site_header': self.site_header,
            'site_title': self.site_title,
            'site_url': self.site_url,
            'has_permission': False,
            **(extra_context or {}),
        }
        
        # nextパラメータをコンテキストに追加
        next_url = request.GET.get('next')
        if next_url:
            context['next'] = next_url
        
        return TemplateResponse(request, 'application/admin_login.html', context)
    
    def has_permission(self, request):
        """パスワード認証済みかどうかをチェック"""
        return request.session.get('admin_authenticated', False)
    
    def logout(self, request, extra_context=None):
        """ログアウト処理をカスタマイズ（GET/POST両方対応）"""
        from django.contrib import messages
        
        # セッションから認証フラグを削除
        request.session.pop('admin_authenticated', None)
        messages.success(request, 'ログアウトしました。')
        
        # ログインページにリダイレクト（カスタムログインビューに）
        from django.urls import reverse
        return redirect(reverse('application:admin_login'))
    
    def get_urls(self):
        """URL設定をカスタマイズしてログアウトをGETメソッドでも受け付けるようにする"""
        from django.urls import path
        from django.urls.resolvers import URLPattern
        
        urls = super().get_urls()
        
        # ログアウトURLを上書き
        custom_urls = [
            path('logout/', self.logout, name='logout'),
        ]
        
        # 既存のURLの中でログアウトURLを置き換える（URLPatternオブジェクトのみチェック）
        filtered_urls = []
        for url in urls:
            if isinstance(url, URLPattern) and hasattr(url, 'name') and url.name == 'logout':
                continue  # ログアウトURLはスキップ
            filtered_urls.append(url)
        
        return custom_urls + filtered_urls


# カスタムAdminSiteのインスタンスを作成
custom_admin_site = CustomAdminSite(name='custom_admin')


# モデルをカスタムAdminSiteに登録
class SubscriptionUserAdmin(admin.ModelAdmin):
    list_display = ['email', 'subscription_id', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['email', 'subscription_id']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


class CSVUploadAdmin(admin.ModelAdmin):
    list_display = ['id', 'file_name', 'status', 'total_rows', 'active_subscriptions', 'matched_count', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['file_name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


class SalonApplicationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'last_name', 'first_name', 'email', 'status',
        'subscription_verified', 'match_method', 'access_granted', 'created_at'
    ]
    list_filter = ['status', 'subscription_verified', 'access_granted', 'match_method', 'created_at']
    search_fields = ['last_name', 'first_name', 'email']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('基本情報', {
            'fields': ('last_name', 'first_name', 'email', 'subscription_id')
        }),
        ('突合情報', {
            'fields': ('subscription_verified', 'subscription_user', 'match_method', 'matched_at', 'csv_upload', 'match_notes')
        }),
        ('確認情報', {
            'fields': ('status',)
        }),
        ('Discordアカウント情報', {
            'fields': ('discord_display_name', 'discord_username', 'discord_account_name', 'discord_account_submitted_at')
        }),
        ('アクセス情報', {
            'fields': ('access_granted', 'access_granted_at')
        }),
        ('その他', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['grant_access_action']
    
    def grant_access_action(self, request, queryset):
        """選択された申し込みにアクセスを付与"""
        count = 0
        for application in queryset:
            if (not application.access_granted and 
                application.subscription_verified and 
                (application.discord_display_name or application.discord_account_name)):
                application.grant_access()
                count += 1
        
        self.message_user(
            request,
            f'{count}件の申し込みにアクセスを付与しました。'
        )
    grant_access_action.short_description = '選択された申し込みにアクセスを付与'


# カスタムAdminSiteに登録
custom_admin_site.register(SubscriptionUser, SubscriptionUserAdmin)
custom_admin_site.register(CSVUpload, CSVUploadAdmin)
custom_admin_site.register(SalonApplication, SalonApplicationAdmin)


class DiscountApplicationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'last_name', 'first_name', 'email', 'status',
        'subscription_verified', 'match_method', 'discount_applied', 'created_at'
    ]
    list_filter = ['status', 'subscription_verified', 'discount_applied', 'match_method', 'created_at']
    search_fields = ['last_name', 'first_name', 'email']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('基本情報', {
            'fields': ('last_name', 'first_name', 'email')
        }),
        ('突合情報', {
            'fields': ('subscription_verified', 'subscription_user', 'match_method', 'matched_at', 'csv_upload', 'match_notes')
        }),
        ('確認情報', {
            'fields': ('status',)
        }),
        ('Discordアカウント情報', {
            'fields': ('discord_display_name', 'discord_username', 'discord_account_submitted_at')
        }),
        ('値引き適用情報', {
            'fields': ('discount_applied', 'discount_applied_at')
        }),
        ('その他', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


custom_admin_site.register(DiscountApplication, DiscountApplicationAdmin)
