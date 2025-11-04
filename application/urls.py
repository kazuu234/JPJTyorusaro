from django.urls import path
from . import views

app_name = 'application'

urlpatterns = [
    # 管理画面ログイン
    path('admin/login/', views.admin_login, name='admin_login'),
    path('admin/logout/', views.admin_logout, name='admin_logout'),
    
    # 申し込みフォーム
    path('', views.application_form, name='application_form'),
    path('success/<int:application_id>/', views.application_success, name='application_success'),
    path('pending/<int:application_id>/', views.application_pending, name='application_pending'),
    
    # Discordアカウント名入力（管理者用）
    path('discord/input/<int:application_id>/', views.discord_account_input, name='discord_account_input'),
    
    # CSVアップロード
    path('csv/upload/', views.csv_upload, name='csv_upload'),
    path('csv/list/', views.csv_upload_list, name='csv_upload_list'),
    path('csv/detail/<int:upload_id>/', views.csv_upload_detail, name='csv_upload_detail'),
    path('csv/delete/<int:upload_id>/', views.csv_upload_delete, name='csv_upload_delete'),
    
    # 申し込み管理
    path('list/', views.application_list, name='application_list'),
    path('detail/<int:application_id>/', views.application_detail, name='application_detail'),
    path('delete/<int:application_id>/', views.application_delete, name='application_delete'),
    path('manual-match/select/<int:application_id>/', views.manual_match_select, name='manual_match_select'),
    path('manual-match/<int:application_id>/', views.manual_match, name='manual_match'),
    path('grant/<int:application_id>/', views.manual_access_grant, name='manual_access_grant'),
    path('revoke/<int:application_id>/', views.revoke_access, name='revoke_access'),
    
    # 値引き申請：手動突合
    path('discount/manual-match/select/<int:application_id>/', views.manual_discount_match_select, name='manual_discount_match_select'),
    path('discount/manual-match/<int:application_id>/', views.manual_discount_match, name='manual_discount_match'),
    
    # アクセス権付与状況
    path('access-grant/', views.access_grant_list, name='access_grant_list'),
    path('batch-grant/', views.batch_access_grant, name='batch_access_grant'),
    
    # 値引き申請フォーム
    path('discount/', views.discount_application_form, name='discount_application_form'),
    path('discount/pending/<int:application_id>/', views.discount_application_pending, name='discount_application_pending'),
    path('discount/success/<int:application_id>/', views.discount_application_success, name='discord_application_success'),
    
    # 値引き申請管理
    path('discount/list/', views.discount_application_list, name='discount_application_list'),
    path('discount/detail/<int:application_id>/', views.discount_application_detail, name='discount_application_detail'),
    path('discount/apply/<int:application_id>/', views.apply_discount, name='apply_discount'),
    path('discount/revoke/<int:application_id>/', views.revoke_discount, name='revoke_discount'),
    path('discount/delete/<int:application_id>/', views.discount_application_delete, name='discount_application_delete'),
    
    # アクセス剥奪管理
    path('revocation/', views.revocation_list, name='revocation_list'),
    path('batch-revoke/', views.batch_access_revoke, name='batch_access_revoke'),
    path('data-management/', views.data_management, name='data_management'),
]
