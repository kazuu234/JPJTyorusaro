from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import csv
import os
from .models import SalonApplication, SubscriptionUser, CSVUpload, DiscountApplication
from .forms import SalonApplicationForm, CSVUploadForm, DiscordAccountForm, DiscountApplicationForm
from .decorators import admin_login_required


@require_http_methods(["GET", "POST"])
def admin_login(request):
    """管理画面ログイン"""
    # 既に認証済みの場合はリダイレクト先に移動
    if request.session.get('admin_authenticated', False):
        next_url = request.GET.get('next')
        if next_url:
            return redirect(next_url)
        else:
            return redirect('application:application_list')
    
    if request.method == 'POST':
        password = request.POST.get('password', '').strip()
        
        # 設定ファイルのパスワードと比較
        admin_password = getattr(settings, 'ADMIN_PASSWORD', '11223456778899#JP')
        
        if password == admin_password:
            # 認証成功：セッションに認証済みフラグを設定
            request.session['admin_authenticated'] = True
            request.session.set_expiry(86400 * 7)  # 7日間有効
            
            next_url = request.GET.get('next')
            if next_url:
                messages.success(request, 'ログインしました。')
                return redirect(next_url)
            else:
                messages.success(request, 'ログインしました。')
                return redirect('application:application_list')
        else:
            messages.error(request, 'パスワードが正しくありません。')
    
    return render(request, 'application/admin_login.html', {
        'page_title': '管理画面ログイン'
    })


def admin_logout(request):
    """管理画面ログアウト"""
    request.session.pop('admin_authenticated', None)
    messages.success(request, 'ログアウトしました。')
    return redirect('application:admin_login')


def match_applications_with_csv(csv_file_path, csv_upload_instance):
    """
    CSVファイルと申し込み情報を突合
    
    Args:
        csv_file_path: CSVファイルのパス
        csv_upload_instance: CSVUploadインスタンス
    
    Returns:
        tuple: (matched_count, revocation_msg)
    """
    matched_count = 0
    revocation_msg = ""
    
    try:
        # CSVファイルを読み込む（cp932エンコーディング）
        encodings = ['cp932', 'shift_jis', 'utf-8-sig', 'utf-8']
        csv_data = None
        detected_encoding = None
        
        for enc in encodings:
            try:
                with open(csv_file_path, 'r', encoding=enc, newline='') as f:
                    reader = csv.DictReader(f)
                    csv_data = list(reader)
                    detected_encoding = enc
                    break
            except (UnicodeDecodeError, FileNotFoundError):
                continue
        
        if csv_data is None:
            return 0, "CSVファイルの読み込みに失敗しました。文字コードを確認してください。"
        
        # 必要なカラムを確認
        required_columns = ['定期ステータス', '配送先 姓', '配送先 名', '配送先 名前', '注文者 メールアドレス']
        headers = csv_data[0].keys() if csv_data else []
        
        missing_columns = [col for col in required_columns if col not in headers]
        if missing_columns:
            return 0, f"必要なカラムが見つかりません: {', '.join(missing_columns)}"
        
        # 「定期ステータス」が「継続」の行のみをフィルタ
        active_subscriptions = [
            row for row in csv_data 
            if row.get('定期ステータス', '').strip() == '継続'
        ]
        
        # 「継続」以外の行（アクセス剥奪チェック用）
        inactive_subscriptions = [
            row for row in csv_data 
            if row.get('定期ステータス', '').strip() != '継続'
        ]
        
        csv_upload_instance.active_subscriptions = len(active_subscriptions)
        csv_upload_instance.total_rows = len(csv_data)
        csv_upload_instance.save()
        
        # 未処理の申し込みとアクセス付与済みの申し込みを取得
        pending_applications = SalonApplication.objects.filter(
            subscription_verified=False
        ).order_by('created_at')
        
        # アクセス付与済みの申し込みも突合対象にする（剥奪チェックのため）
        # ただし、剥奪済み（access_revoked_atが設定済み）の申し込みは除外（終着点）
        granted_applications = SalonApplication.objects.filter(
            access_granted=True,
            subscription_verified=True,
            access_revoked_at__isnull=True  # 剥奪済みは除外
        ).order_by('created_at')
        
        # 各申し込みを突合
        for application in pending_applications:
            app_email = application.email.lower().strip()
            app_last_name = application.last_name.strip()
            app_first_name = application.first_name.strip()
            app_full_name = f"{app_last_name} {app_first_name}".strip()
            
            matched_row = None
            match_method = ''
            
            # 優先1: メールアドレス + 名前（姓・名）の完全一致
            for row in active_subscriptions:
                row_email = row.get('注文者 メールアドレス', '').lower().strip()
                row_last_name = row.get('配送先 姓', '').strip()
                row_first_name = row.get('配送先 名', '').strip()
                row_full_name = f"{row_last_name} {row_first_name}".strip()
                
                if (app_email == row_email and 
                    app_last_name == row_last_name and 
                    app_first_name == row_first_name):
                    matched_row = row
                    match_method = 'email_and_name'
                    break
            
            # 優先2: メールアドレスのみの一致
            if not matched_row:
                for row in active_subscriptions:
                    row_email = row.get('注文者 メールアドレス', '').lower().strip()
                    if app_email == row_email:
                        matched_row = row
                        match_method = 'email_only'
                        break
            
            # 優先3: 名前（姓・名）の完全一致
            if not matched_row:
                name_matches = []
                for row in active_subscriptions:
                    row_last_name = row.get('配送先 姓', '').strip()
                    row_first_name = row.get('配送先 名', '').strip()
                    row_email = row.get('注文者 メールアドレス', '').lower().strip()
                    
                    if (app_last_name == row_last_name and 
                        app_first_name == row_first_name):
                        name_matches.append({
                            'row': row,
                            'email': row_email
                        })
                
                # 同姓同名が1人だけの場合はマッチ
                if len(name_matches) == 1:
                    matched_row = name_matches[0]['row']
                    match_method = 'name_only'
                    application.match_notes = f"同姓同名の候補が1件のみ。メール: {name_matches[0]['email']}"
                elif len(name_matches) > 1:
                    # 複数の同姓同名がある場合はメモに記録
                    emails = [m['email'] for m in name_matches]
                    application.match_notes = (
                        f"同姓同名の候補が複数あります。手動確認が必要です。\n"
                        f"候補メールアドレス: {', '.join(emails)}"
                    )
            
            # 突合成功時
            if matched_row:
                application.subscription_verified = True
                application.match_method = match_method
                application.matched_at = timezone.now()
                application.csv_upload = csv_upload_instance
                application.status = 'verified'
                
                # SubscriptionUserを作成または取得
                row_email = matched_row.get('注文者 メールアドレス', '').lower().strip()
                subscription_id = matched_row.get('注文番号', '').strip() or f"CSV_{csv_upload_instance.id}_{matched_count}"
                
                subscription_user, created = SubscriptionUser.objects.get_or_create(
                    email=row_email,
                    defaults={
                        'subscription_id': subscription_id,
                        'is_active': True
                    }
                )
                
                application.subscription_user = subscription_user
                application.match_notes = f"CSV突合成功: {match_method}"
                application.save()
                matched_count += 1
            else:
                # 突合失敗時
                if not application.match_notes:
                    application.match_notes = "CSV突合で一致する情報が見つかりませんでした。"
                application.save()
        
        # アクセス付与済みの申し込みを突合（剥奪チェックのため）
        revocation_count = 0
        for application in granted_applications:
            app_email = application.email.lower().strip()
            app_last_name = application.last_name.strip()
            app_first_name = application.first_name.strip()
            
            # まず「継続」のエントリーと突合できるかチェック
            matched_with_active = None
            
            # 優先1: メールアドレス + 名前（姓・名）の完全一致
            for row in active_subscriptions:
                row_email = row.get('注文者 メールアドレス', '').lower().strip()
                row_last_name = row.get('配送先 姓', '').strip()
                row_first_name = row.get('配送先 名', '').strip()
                
                if (app_email == row_email and 
                    app_last_name == row_last_name and 
                    app_first_name == row_first_name):
                    matched_with_active = row
                    break
            
            # 優先2: メールアドレスのみの一致
            if not matched_with_active:
                for row in active_subscriptions:
                    row_email = row.get('注文者 メールアドレス', '').lower().strip()
                    if app_email == row_email:
                        matched_with_active = row
                        break
            
            # 「継続」と突合できた場合は剥奪不要（スキップ）
            if matched_with_active:
                continue
            
            # 「継続」と突合できなかった場合、「継続」以外のエントリーと突合されているかチェック
            matched_with_inactive = None
            matched_status = None
            
            # メールアドレス + 名前で突合チェック
            for row in inactive_subscriptions:
                row_email = row.get('注文者 メールアドレス', '').lower().strip()
                row_last_name = row.get('配送先 姓', '').strip()
                row_first_name = row.get('配送先 名', '').strip()
                row_status = row.get('定期ステータス', '').strip()
                
                if row_status == '継続':
                    continue
                
                # メール+名前で一致
                if (app_email == row_email and 
                    app_last_name == row_last_name and 
                    app_first_name == row_first_name):
                    matched_with_inactive = row
                    matched_status = row_status
                    break
            
            # メールアドレスのみでチェック（名前一致なしの場合）
            if not matched_with_inactive:
                for row in inactive_subscriptions:
                    row_email = row.get('注文者 メールアドレス', '').lower().strip()
                    row_status = row.get('定期ステータス', '').strip()
                    
                    if row_status == '継続':
                        continue
                    
                    if app_email == row_email:
                        matched_with_inactive = row
                        matched_status = row_status
                        break
            
            # 「継続」とは突合できず、「継続」以外のみと突合された場合、アクセス剥奪必要フラグを立てる
            if matched_with_inactive:
                if not application.access_revocation_required:
                    application.access_revocation_required = True
                    application.access_revocation_required_at = timezone.now()
                    application.match_notes = (
                        f"{application.match_notes}\n" if application.match_notes else ""
                    ) + (
                        f"[CSV突合 {csv_upload_instance.file_name}] "
                        f"「継続」とは突合できず、定期ステータス「{matched_status}」とのみ突合されました。"
                        f"アクセス権の剥奪が必要です。"
                    )
                    application.save()
                    revocation_count += 1
        
        csv_upload_instance.matched_count = matched_count
        csv_upload_instance.salon_match_count = matched_count  # サロン申請突合成功数
        csv_upload_instance.access_revocation_count = revocation_count  # アクセス権剥奪必要件数
        csv_upload_instance.status = 'completed'
        csv_upload_instance.save()
        
        revocation_msg = f"（アクセス剥奪必要: {revocation_count}件）" if revocation_count > 0 else ""
        return matched_count, revocation_msg
    
    except Exception as e:
        error_message = f"エラーが発生しました: {str(e)}"
        csv_upload_instance.status = 'error'
        csv_upload_instance.error_message = error_message
        csv_upload_instance.save()
        return matched_count, error_message


def match_discount_applications_with_csv(csv_file_path, csv_upload_instance):
    """
    CSVファイルと値引き申請情報を突合
    
    Args:
        csv_file_path: CSVファイルのパス
        csv_upload_instance: CSVUploadインスタンス
    
    Returns:
        int: 突合成功数
    """
    matched_count = 0
    
    try:
        # CSVファイルを読み込む（cp932エンコーディング）
        encodings = ['cp932', 'shift_jis', 'utf-8-sig', 'utf-8']
        csv_data = None
        
        for enc in encodings:
            try:
                with open(csv_file_path, 'r', encoding=enc, newline='') as f:
                    reader = csv.DictReader(f)
                    csv_data = list(reader)
                    break
            except (UnicodeDecodeError, FileNotFoundError):
                continue
        
        if csv_data is None:
            return 0
        
        # 「定期ステータス」が「継続」の行のみをフィルタ
        active_subscriptions = [
            row for row in csv_data 
            if row.get('定期ステータス', '').strip() == '継続'
        ]
        
        # 未処理の値引き申請を取得
        pending_applications = DiscountApplication.objects.filter(
            subscription_verified=False
        ).order_by('created_at')
        
        # 各申請を突合
        for application in pending_applications:
            app_email = application.email.lower().strip()
            app_last_name = application.last_name.strip()
            app_first_name = application.first_name.strip()
            
            matched_row = None
            match_method = ''
            
            # 優先1: メールアドレス + 名前（姓・名）の完全一致
            for row in active_subscriptions:
                row_email = row.get('注文者 メールアドレス', '').lower().strip()
                row_last_name = row.get('配送先 姓', '').strip()
                row_first_name = row.get('配送先 名', '').strip()
                
                if (app_email == row_email and 
                    app_last_name == row_last_name and 
                    app_first_name == row_first_name):
                    matched_row = row
                    match_method = 'email_and_name'
                    break
            
            # 優先2: メールアドレスのみの一致
            if not matched_row:
                for row in active_subscriptions:
                    row_email = row.get('注文者 メールアドレス', '').lower().strip()
                    if app_email == row_email:
                        matched_row = row
                        match_method = 'email_only'
                        break
            
            # 優先3: 名前（姓・名）の完全一致
            if not matched_row:
                name_matches = []
                for row in active_subscriptions:
                    row_last_name = row.get('配送先 姓', '').strip()
                    row_first_name = row.get('配送先 名', '').strip()
                    row_email = row.get('注文者 メールアドレス', '').lower().strip()
                    
                    if (app_last_name == row_last_name and 
                        app_first_name == row_first_name):
                        name_matches.append({
                            'row': row,
                            'email': row_email
                        })
                
                # 同姓同名が1人だけの場合はマッチ
                if len(name_matches) == 1:
                    matched_row = name_matches[0]['row']
                    match_method = 'name_only'
                    application.match_notes = f"同姓同名の候補が1件のみ。メール: {name_matches[0]['email']}"
                elif len(name_matches) > 1:
                    # 複数の同姓同名がある場合はメモに記録
                    emails = [m['email'] for m in name_matches]
                    application.match_notes = (
                        f"同姓同名の候補が複数あります。手動確認が必要です。\n"
                        f"候補メールアドレス: {', '.join(emails)}"
                    )
            
            # 突合成功時
            if matched_row:
                application.subscription_verified = True
                application.match_method = match_method
                application.matched_at = timezone.now()
                application.csv_upload = csv_upload_instance
                application.status = 'verified'
                
                # SubscriptionUserを作成または取得
                row_email = matched_row.get('注文者 メールアドレス', '').lower().strip()
                subscription_id = matched_row.get('注文番号', '').strip() or f"CSV_{csv_upload_instance.id}_{matched_count}"
                
                subscription_user, created = SubscriptionUser.objects.get_or_create(
                    email=row_email,
                    defaults={
                        'subscription_id': subscription_id,
                        'is_active': True
                    }
                )
                
                application.subscription_user = subscription_user
                application.match_notes = f"CSV突合成功: {match_method}"
                application.save()
                matched_count += 1
            else:
                # 突合失敗時
                if not application.match_notes:
                    application.match_notes = "CSV突合で一致する情報が見つかりませんでした。"
                application.save()
        
        csv_upload_instance.discount_match_count = matched_count  # 値引き申請突合成功数
        csv_upload_instance.save()
        
        return matched_count
    
    except Exception as e:
        return 0


def match_discount_revocations_with_csv(csv_file_path, csv_upload_instance):
    """
    CSVファイルと値引き適用済み申請を突合（値引き剥奪チェック）
    
    Args:
        csv_file_path: CSVファイルのパス
        csv_upload_instance: CSVUploadインスタンス
    
    Returns:
        int: 値引き剥奪必要件数
    """
    revocation_count = 0
    
    try:
        # CSVファイルを読み込む（cp932エンコーディング）
        encodings = ['cp932', 'shift_jis', 'utf-8-sig', 'utf-8']
        csv_data = None
        
        for enc in encodings:
            try:
                with open(csv_file_path, 'r', encoding=enc, newline='') as f:
                    reader = csv.DictReader(f)
                    csv_data = list(reader)
                    break
            except (UnicodeDecodeError, FileNotFoundError):
                continue
        
        if csv_data is None:
            return 0
        
        # 「定期ステータス」が「継続」の行と「継続」以外の行を分ける
        active_subscriptions = [
            row for row in csv_data 
            if row.get('定期ステータス', '').strip() == '継続'
        ]
        inactive_subscriptions = [
            row for row in csv_data 
            if row.get('定期ステータス', '').strip() != '継続'
        ]
        
        # 値引き適用済みの申請を取得（剥奪済みは除外）
        granted_applications = DiscountApplication.objects.filter(
            discount_applied=True,
            discount_revoked_at__isnull=True  # 剥奪済みは除外
        ).order_by('created_at')
        
        # 各申請を突合
        for application in granted_applications:
            app_email = application.email.lower().strip()
            app_last_name = application.last_name.strip()
            app_first_name = application.first_name.strip()
            
            # まず「継続」のエントリーと突合できるかチェック
            matched_with_active = None
            
            # 優先1: メールアドレス + 名前（姓・名）の完全一致
            for row in active_subscriptions:
                row_email = row.get('注文者 メールアドレス', '').lower().strip()
                row_last_name = row.get('配送先 姓', '').strip()
                row_first_name = row.get('配送先 名', '').strip()
                
                if (app_email == row_email and 
                    app_last_name == row_last_name and 
                    app_first_name == row_first_name):
                    matched_with_active = row
                    break
            
            # 優先2: メールアドレスのみの一致
            if not matched_with_active:
                for row in active_subscriptions:
                    row_email = row.get('注文者 メールアドレス', '').lower().strip()
                    if app_email == row_email:
                        matched_with_active = row
                        break
            
            # 「継続」と突合できた場合は剥奪不要（スキップ）
            if matched_with_active:
                continue
            
            # 「継続」と突合できなかった場合、「継続」以外のエントリーと突合されているかチェック
            matched_with_inactive = None
            matched_status = None
            
            # メールアドレス + 名前で突合チェック
            for row in inactive_subscriptions:
                row_email = row.get('注文者 メールアドレス', '').lower().strip()
                row_last_name = row.get('配送先 姓', '').strip()
                row_first_name = row.get('配送先 名', '').strip()
                row_status = row.get('定期ステータス', '').strip()
                
                if row_status == '継続':
                    continue
                
                # メール+名前で一致
                if (app_email == row_email and 
                    app_last_name == row_last_name and 
                    app_first_name == row_first_name):
                    matched_with_inactive = row
                    matched_status = row_status
                    break
            
            # メールアドレスのみでチェック（名前一致なしの場合）
            if not matched_with_inactive:
                for row in inactive_subscriptions:
                    row_email = row.get('注文者 メールアドレス', '').lower().strip()
                    row_status = row.get('定期ステータス', '').strip()
                    
                    if row_status == '継続':
                        continue
                    
                    if app_email == row_email:
                        matched_with_inactive = row
                        matched_status = row_status
                        break
            
            # 「継続」とは突合できず、「継続」以外のみと突合された場合、値引き剥奪必要フラグを立てる
            if matched_with_inactive:
                if not application.discount_revocation_required:
                    application.discount_revocation_required = True
                    application.discount_revocation_required_at = timezone.now()
                    application.match_notes = (
                        f"{application.match_notes}\n" if application.match_notes else ""
                    ) + (
                        f"[CSV突合 {csv_upload_instance.file_name}] "
                        f"「継続」とは突合できず、定期ステータス「{matched_status}」とのみ突合されました。"
                        f"値引きの剥奪が必要です。"
                    )
                    application.save()
                    revocation_count += 1
        
        csv_upload_instance.discount_revocation_count = revocation_count  # 値引き剥奪必要件数
        csv_upload_instance.save()
        
        return revocation_count
    
    except Exception as e:
        return 0


@require_http_methods(["GET", "POST"])
def application_form(request):
    """夜遊びサロン申し込みフォーム"""
    if request.method == 'POST':
        form = SalonApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.status = 'pending'
            application.subscription_verified = False
            application.save()
            
            messages.success(
                request,
                '申し込みを受け付けました。Joy Journeyの定期購入の確認後、アクセスを付与いたします。'
            )
            return redirect('application:application_pending', application_id=application.id)
    else:
        form = SalonApplicationForm()
    
    return render(request, 'application/form.html', {
        'form': form,
        'page_title': '夜遊びサロン 申し込みフォーム'
    })


def application_success(request, application_id):
    """申し込み成功・アクセス付与済み"""
    application = get_object_or_404(SalonApplication, id=application_id)
    
    if not application.access_granted:
        messages.warning(request, 'アクセスがまだ付与されていません。')
        return redirect('application:application_form')
    
    return render(request, 'application/success.html', {
        'application': application,
        'page_title': '申し込み完了'
    })


def application_pending(request, application_id):
    """審査中ページ"""
    application = get_object_or_404(SalonApplication, id=application_id)
    
    return render(request, 'application/pending.html', {
        'application': application,
        'page_title': '審査中'
    })


@require_http_methods(["GET", "POST"])
def discount_application_form(request):
    """値引き申請フォーム"""
    if request.method == 'POST':
        form = DiscountApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.status = 'pending'
            application.subscription_verified = False
            application.discord_account_submitted_at = timezone.now()
            application.save()
            
            messages.success(
                request,
                '値引き申請を受け付けました。Joy Journeyの定期購入の確認後、値引きを適用いたします。'
            )
            return redirect('application:discount_application_pending', application_id=application.id)
    else:
        form = DiscountApplicationForm()
    
    return render(request, 'application/discount_application_form.html', {
        'form': form,
        'page_title': '値引き申請フォーム'
    })


def discount_application_pending(request, application_id):
    """値引き申請審査中ページ"""
    application = get_object_or_404(DiscountApplication, id=application_id)
    
    return render(request, 'application/discount_application_pending.html', {
        'application': application,
        'page_title': '値引き申請審査中'
    })


def discount_application_success(request, application_id):
    """値引き申請完了ページ"""
    application = get_object_or_404(DiscountApplication, id=application_id)
    
    if not application.discount_applied:
        messages.warning(request, '値引きがまだ適用されていません。')
        return redirect('application:discount_application_form')
    
    return render(request, 'application/discount_application_success.html', {
        'application': application,
        'page_title': '値引き申請完了'
    })


@admin_login_required
@require_http_methods(["GET", "POST"])
def discord_account_input(request, application_id):
    """Discordアカウント名入力（管理者用）"""
    application = get_object_or_404(SalonApplication, id=application_id)
    
    # 突合が完了していない場合はエラー
    if not application.subscription_verified:
        messages.error(request, '定期購入の確認が完了していません。先に突合を行ってください。')
        return redirect('application:application_detail', application_id=application.id)
    
    if request.method == 'POST':
        form = DiscordAccountForm(request.POST, instance=application)
        if form.is_valid():
            application = form.save(commit=False)
            application.discord_account_submitted_at = timezone.now()
            application.save()
            
            messages.success(request, 'Discordアカウント名を登録しました。')
            return redirect('application:application_detail', application_id=application.id)
    else:
        form = DiscordAccountForm(instance=application)
    
    return render(request, 'application/discord_account_input.html', {
        'form': form,
        'application': application,
        'page_title': f'Discordアカウント名入力: {application.full_name}'
    })


@admin_login_required
@require_http_methods(["GET", "POST"])
def csv_upload(request):
    """CSVアップロード"""
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_upload_instance = form.save(commit=False)
            csv_file = form.cleaned_data['csv_file']
            
            # ファイルを保存
            file_path = os.path.join(settings.MEDIA_ROOT, 'csv_uploads', csv_file.name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with default_storage.open(file_path, 'wb') as f:
                for chunk in csv_file.chunks():
                    f.write(chunk)
            
            csv_upload_instance.file_path = file_path
            csv_upload_instance.status = 'processing'
            csv_upload_instance.save()
            
            # 突合処理を実行
            salon_match_count, access_revocation_msg = match_applications_with_csv(
                file_path,
                csv_upload_instance
            )
            
            # 値引き申請の突合処理も実行
            discount_match_count = match_discount_applications_with_csv(
                file_path,
                csv_upload_instance
            )
            
            # 値引き剥奪チェック処理も実行
            discount_revocation_count = match_discount_revocations_with_csv(
                file_path,
                csv_upload_instance
            )
            
            if access_revocation_msg.startswith('エラー'):
                messages.error(request, access_revocation_msg)
            else:
                msg = f'CSVアップロードが完了しました。'
                msg += f' サロン申請突合: {salon_match_count}件'
                if discount_match_count > 0:
                    msg += f'、値引き申請突合: {discount_match_count}件'
                if access_revocation_msg:
                    msg += f' {access_revocation_msg}'
                if discount_revocation_count > 0:
                    msg += f'（値引き剥奪必要: {discount_revocation_count}件）'
                if access_revocation_msg or discount_revocation_count > 0:
                    messages.warning(request, msg)
                else:
                    messages.success(request, msg)
            
            return redirect('application:csv_upload_list')
    else:
        form = CSVUploadForm()
    
    return render(request, 'application/csv_upload.html', {
        'form': form,
        'page_title': 'CSVアップロード'
    })


@admin_login_required
def csv_upload_list(request):
    """CSVアップロード一覧"""
    uploads = CSVUpload.objects.all()
    
    return render(request, 'application/csv_upload_list.html', {
        'uploads': uploads,
        'page_title': 'CSVアップロード一覧'
    })


@admin_login_required
def csv_upload_detail(request, upload_id):
    """CSVアップロード詳細"""
    upload = get_object_or_404(CSVUpload, id=upload_id)
    
    # このCSVで突合された申し込み一覧
    applications = SalonApplication.objects.filter(csv_upload=upload)
    
    return render(request, 'application/csv_upload_detail.html', {
        'upload': upload,
        'applications': applications,
        'page_title': f'CSVアップロード詳細: {upload.file_name}'
    })


@admin_login_required
def application_list(request):
    """申し込み一覧（管理者用）"""
    applications = SalonApplication.objects.all()
    
    # フィルタリング
    status_filter = request.GET.get('status')
    verified_filter = request.GET.get('verified')
    access_filter = request.GET.get('access')
    revocation_filter = request.GET.get('revocation')
    
    if status_filter:
        applications = applications.filter(status=status_filter)
    if verified_filter == 'yes':
        applications = applications.filter(subscription_verified=True)
    elif verified_filter == 'no':
        applications = applications.filter(subscription_verified=False)
    if access_filter == 'yes':
        applications = applications.filter(access_granted=True)
    elif access_filter == 'no':
        applications = applications.filter(access_granted=False)
    if revocation_filter == 'required':
        applications = applications.filter(access_revocation_required=True, access_granted=True)
    elif revocation_filter == 'revoked':
        applications = applications.filter(access_revoked_at__isnull=False)
    
    return render(request, 'application/list.html', {
        'applications': applications,
        'page_title': '申し込み一覧',
        'status_filter': status_filter,
        'verified_filter': verified_filter,
        'access_filter': access_filter,
        'revocation_filter': revocation_filter,
    })


@admin_login_required
def application_detail(request, application_id):
    """申し込み詳細（管理者用）"""
    application = get_object_or_404(SalonApplication, id=application_id)
    
    return render(request, 'application/detail.html', {
        'application': application,
        'page_title': f'申し込み詳細: {application.full_name}'
    })


@admin_login_required
def manual_match_select(request, application_id):
    """手動突合：CSVエントリー選択画面"""
    application = get_object_or_404(SalonApplication, id=application_id)
    
    # 最新のCSVアップロードを取得
    latest_csv = CSVUpload.objects.filter(status='completed').order_by('-created_at').first()
    
    csv_entries = []
    if latest_csv and latest_csv.file_path and os.path.exists(latest_csv.file_path):
        encodings = ['cp932', 'shift_jis', 'utf-8-sig', 'utf-8']
        for enc in encodings:
            try:
                with open(latest_csv.file_path, 'r', encoding=enc, newline='') as f:
                    reader = csv.DictReader(f)
                    row_index = 0
                    for row in reader:
                        row_index += 1
                        if row.get('定期ステータス', '').strip() == '継続':
                            row_email = row.get('注文者 メールアドレス', '').lower().strip()
                            row_last_name = row.get('配送先 姓', '').strip()
                            row_first_name = row.get('配送先 名', '').strip()
                            row_full_name = f"{row_last_name} {row_first_name}".strip()
                            
                            csv_entries.append({
                                'row_index': row_index,
                                'email': row_email,
                                'last_name': row_last_name,
                                'first_name': row_first_name,
                                'full_name': row_full_name,
                                'csv_row': row,  # 全データを保存（後でsubscription_id等に使用）
                            })
                break
            except (UnicodeDecodeError, FileNotFoundError):
                continue
    
    return render(request, 'application/manual_match_select.html', {
        'application': application,
        'csv_upload': latest_csv,
        'csv_entries': csv_entries,
        'page_title': f'手動突合: {application.full_name}'
    })


@admin_login_required
@require_http_methods(["POST"])
def manual_match(request, application_id):
    """手動突合：選択したCSVエントリーで突合"""
    application = get_object_or_404(SalonApplication, id=application_id)
    
    # CSVからの選択されたエントリー情報を取得
    selected_row_index = request.POST.get('selected_row_index')
    candidate_email = request.POST.get('candidate_email', '').strip()
    candidate_last_name = request.POST.get('candidate_last_name', '').strip()
    candidate_first_name = request.POST.get('candidate_first_name', '').strip()
    
    if not candidate_email:
        messages.error(request, 'CSVエントリーが選択されていません。')
        return redirect('application:application_detail', application_id=application.id)
    
    # 最新のCSVアップロードを取得（subscription_idなどの情報取得のため）
    latest_csv = CSVUpload.objects.filter(status='completed').order_by('-created_at').first()
    subscription_id = f"MANUAL_{application.id}"
    
    if latest_csv and latest_csv.file_path and os.path.exists(latest_csv.file_path):
        # 選択された行のデータを取得
        encodings = ['cp932', 'shift_jis', 'utf-8-sig', 'utf-8']
        for enc in encodings:
            try:
                with open(latest_csv.file_path, 'r', encoding=enc, newline='') as f:
                    reader = csv.DictReader(f)
                    row_index = 0
                    for row in reader:
                        row_index += 1
                        if row.get('定期ステータス', '').strip() == '継続':
                            if str(row_index) == str(selected_row_index):
                                # 注文番号などがあればそれを使用
                                order_number = row.get('注文番号', '').strip()
                                if order_number:
                                    subscription_id = order_number
                                break
                break
            except (UnicodeDecodeError, FileNotFoundError):
                continue
    
    # 候補のメールアドレスでSubscriptionUserを作成または取得
    subscription_user, created = SubscriptionUser.objects.get_or_create(
        email=candidate_email.lower().strip(),
        defaults={
            'subscription_id': subscription_id,
            'is_active': True
        }
    )
    
    application.subscription_verified = True
    application.subscription_user = subscription_user
    application.match_method = 'manual'
    application.matched_at = timezone.now()
    application.status = 'verified'
    application.csv_upload = latest_csv
    application.match_notes = (
        f"手動突合: 管理者が選択したCSVエントリー\n"
        f"メール: {candidate_email}\n"
        f"名前: {candidate_last_name} {candidate_first_name}\n"
        f"CSV行番号: {selected_row_index}"
    )
    application.save()
    
    messages.success(request, '手動突合が完了しました。')
    return redirect('application:application_detail', application_id=application.id)


@admin_login_required
@require_http_methods(["POST"])
def manual_access_grant(request, application_id):
    """手動でアクセスを付与（管理者用）"""
    application = get_object_or_404(SalonApplication, id=application_id)
    
    if not application.access_granted:
        if not application.subscription_verified:
            messages.warning(request, '定期購入の確認が完了していません。先に突合を行ってください。')
            return redirect('application:application_detail', application_id=application.id)
        
        if not application.discord_display_name and not application.discord_account_name:
            messages.warning(request, 'Discordアカウント名が入力されていません。先にDiscordアカウント名の入力が完了するまでお待ちください。')
            return redirect('application:application_detail', application_id=application.id)
        
        application.grant_access()
        messages.success(request, 'アクセスを付与しました。')
    else:
        messages.info(request, '既にアクセスが付与されています。')
    
    return redirect('application:application_detail', application_id=application.id)


@admin_login_required
@require_http_methods(["POST"])
def revoke_access(request, application_id):
    """アクセス権を取り消し（管理者用）"""
    application = get_object_or_404(SalonApplication, id=application_id)
    
    if application.access_granted:
        application.revoke_access()
        messages.success(request, 'アクセス権を取り消しました。')
    else:
        messages.info(request, 'アクセスが付与されていません。')
    
    return redirect('application:application_detail', application_id=application.id)


@admin_login_required
@require_http_methods(["POST"])
def batch_access_grant(request):
    """一括アクセス付与"""
    application_ids = request.POST.getlist('application_ids')
    
    if not application_ids:
        messages.warning(request, '申し込みが選択されていません。')
        return redirect('application:access_grant_list')
    
    granted_count = 0
    for app_id in application_ids:
        try:
            application = SalonApplication.objects.get(id=app_id)
            if (application.subscription_verified and 
                (application.discord_display_name or application.discord_account_name) and 
                not application.access_granted):
                application.grant_access()
                granted_count += 1
        except SalonApplication.DoesNotExist:
            continue
    
    messages.success(request, f'{granted_count}件の申し込みにアクセスを付与しました。')
    return redirect('application:access_grant_list')


@admin_login_required
@require_http_methods(["POST"])
def batch_access_revoke(request):
    """一括アクセス剥奪"""
    application_ids = request.POST.getlist('application_ids')
    
    if not application_ids:
        messages.warning(request, '申し込みが選択されていません。')
        return redirect('application:revocation_list')
    
    revoked_count = 0
    for app_id in application_ids:
        try:
            application = SalonApplication.objects.get(id=app_id)
            if application.access_granted:
                application.revoke_access()
                revoked_count += 1
        except SalonApplication.DoesNotExist:
            continue
    
    messages.success(request, f'{revoked_count}件の申し込みのアクセス権を剥奪しました。')
    return redirect('application:revocation_list')


@admin_login_required
def access_grant_list(request):
    """アクセス権付与状況チェック表"""
    # 突合済みの申し込みのみを取得
    applications = SalonApplication.objects.filter(subscription_verified=True)
    
    # フィルタリング
    access_filter = request.GET.get('access')
    if access_filter == 'yes':
        applications = applications.filter(access_granted=True)
    elif access_filter == 'no':
        applications = applications.filter(access_granted=False)
    
    applications = applications.order_by('-created_at')
    
    return render(request, 'application/access_grant_list.html', {
        'applications': applications,
        'page_title': 'アクセス権付与状況チェック表',
        'access_filter': access_filter,
    })


@admin_login_required
def revocation_list(request):
    """アクセス剥奪管理画面"""
    # アクセス剥奪必要の申し込みを取得
    applications = SalonApplication.objects.filter(
        access_revocation_required=True,
        access_granted=True
    ).order_by('-access_revocation_required_at')
    
    # フィルタリング
    status_filter = request.GET.get('status')
    if status_filter == 'revoked':
        # 剥奪済みも表示
        applications = SalonApplication.objects.filter(
            access_revocation_required=True
        ).order_by('-access_revocation_required_at')
    elif status_filter == 'pending':
        # 剥奪待ちのみ
        applications = applications.filter(access_revoked_at__isnull=True)
    
    return render(request, 'application/revocation_list.html', {
        'applications': applications,
        'page_title': 'アクセス剥奪管理',
        'status_filter': status_filter,
    })


@admin_login_required
@require_http_methods(["POST"])
def application_delete(request, application_id):
    """申し込み削除"""
    application = get_object_or_404(SalonApplication, id=application_id)
    
    application_name = application.full_name
    application.delete()
    
    messages.success(request, f'申し込み「{application_name}」を削除しました。')
    return redirect('application:application_list')


@admin_login_required
@require_http_methods(["POST"])
def csv_upload_delete(request, upload_id):
    """CSVアップロード削除"""
    upload = get_object_or_404(CSVUpload, id=upload_id)
    
    # 関連するファイルも削除（オプション）
    if upload.file_path and os.path.exists(upload.file_path):
        try:
            os.remove(upload.file_path)
        except OSError:
            pass  # ファイル削除に失敗しても続行
    
    file_name = upload.file_name
    upload.delete()
    
    messages.success(request, f'CSVアップロード「{file_name}」を削除しました。')
    return redirect('application:csv_upload_list')


@admin_login_required
def discount_application_list(request):
    """値引き申請一覧（管理者用）"""
    applications = DiscountApplication.objects.all()
    
    # フィルタリング
    status_filter = request.GET.get('status')
    verified_filter = request.GET.get('verified')
    discount_filter = request.GET.get('discount')
    
    if status_filter:
        applications = applications.filter(status=status_filter)
    if verified_filter == 'yes':
        applications = applications.filter(subscription_verified=True)
    elif verified_filter == 'no':
        applications = applications.filter(subscription_verified=False)
    if discount_filter == 'yes':
        applications = applications.filter(discount_applied=True)
    elif discount_filter == 'no':
        applications = applications.filter(discount_applied=False)
    
    return render(request, 'application/discount_application_list.html', {
        'applications': applications,
        'page_title': '値引き申請一覧',
        'status_filter': status_filter,
        'verified_filter': verified_filter,
        'discount_filter': discount_filter,
    })


@admin_login_required
def discount_application_detail(request, application_id):
    """値引き申請詳細（管理者用）"""
    application = get_object_or_404(DiscountApplication, id=application_id)
    
    return render(request, 'application/discount_application_detail.html', {
        'application': application,
        'page_title': f'値引き申請詳細: {application.full_name}'
    })


@admin_login_required
def manual_discount_match_select(request, application_id):
    """値引き申請：手動突合：CSVエントリー選択画面"""
    application = get_object_or_404(DiscountApplication, id=application_id)
    
    # 最新のCSVアップロードを取得
    latest_csv = CSVUpload.objects.filter(status='completed').order_by('-created_at').first()
    
    csv_entries = []
    if latest_csv and latest_csv.file_path and os.path.exists(latest_csv.file_path):
        encodings = ['cp932', 'shift_jis', 'utf-8-sig', 'utf-8']
        for enc in encodings:
            try:
                with open(latest_csv.file_path, 'r', encoding=enc, newline='') as f:
                    reader = csv.DictReader(f)
                    row_index = 0
                    for row in reader:
                        row_index += 1
                        if row.get('定期ステータス', '').strip() == '継続':
                            row_email = row.get('注文者 メールアドレス', '').lower().strip()
                            row_last_name = row.get('配送先 姓', '').strip()
                            row_first_name = row.get('配送先 名', '').strip()
                            row_full_name = f"{row_last_name} {row_first_name}".strip()
                            
                            csv_entries.append({
                                'row_index': row_index,
                                'email': row_email,
                                'last_name': row_last_name,
                                'first_name': row_first_name,
                                'full_name': row_full_name,
                                'csv_row': row,
                            })
                break
            except (UnicodeDecodeError, FileNotFoundError):
                continue
    
    return render(request, 'application/manual_discount_match_select.html', {
        'application': application,
        'csv_upload': latest_csv,
        'csv_entries': csv_entries,
        'page_title': f'値引き申請：手動突合: {application.full_name}'
    })


@admin_login_required
@require_http_methods(["POST"])
def manual_discount_match(request, application_id):
    """値引き申請：手動突合：選択したCSVエントリーで突合"""
    application = get_object_or_404(DiscountApplication, id=application_id)
    
    # CSVからの選択されたエントリー情報を取得
    selected_row_index = request.POST.get('selected_row_index')
    candidate_email = request.POST.get('candidate_email', '').strip()
    candidate_last_name = request.POST.get('candidate_last_name', '').strip()
    candidate_first_name = request.POST.get('candidate_first_name', '').strip()
    
    if not candidate_email:
        messages.error(request, 'CSVエントリーが選択されていません。')
        return redirect('application:discount_application_detail', application_id=application.id)
    
    # 最新のCSVアップロードを取得（subscription_idなどの情報取得のため）
    latest_csv = CSVUpload.objects.filter(status='completed').order_by('-created_at').first()
    subscription_id = f"MANUAL_DISC_{application.id}"
    
    if latest_csv and latest_csv.file_path and os.path.exists(latest_csv.file_path):
        # 選択された行のデータを取得
        encodings = ['cp932', 'shift_jis', 'utf-8-sig', 'utf-8']
        for enc in encodings:
            try:
                with open(latest_csv.file_path, 'r', encoding=enc, newline='') as f:
                    reader = csv.DictReader(f)
                    row_index = 0
                    for row in reader:
                        row_index += 1
                        if row.get('定期ステータス', '').strip() == '継続':
                            if str(row_index) == str(selected_row_index):
                                # 注文番号などがあればそれを使用
                                order_number = row.get('注文番号', '').strip()
                                if order_number:
                                    subscription_id = order_number
                                break
                break
            except (UnicodeDecodeError, FileNotFoundError):
                continue
    
    # 候補のメールアドレスでSubscriptionUserを作成または取得
    subscription_user, created = SubscriptionUser.objects.get_or_create(
        email=candidate_email.lower().strip(),
        defaults={
            'subscription_id': subscription_id,
            'is_active': True
        }
    )
    
    application.subscription_verified = True
    application.subscription_user = subscription_user
    application.match_method = 'manual'
    application.matched_at = timezone.now()
    application.status = 'verified'
    application.csv_upload = latest_csv
    application.match_notes = (
        f"手動突合: 管理者が選択したCSVエントリー\n"
        f"メール: {candidate_email}\n"
        f"名前: {candidate_last_name} {candidate_first_name}\n"
        f"CSV行番号: {selected_row_index}"
    )
    application.save()
    
    messages.success(request, '手動突合が完了しました。')
    return redirect('application:discount_application_detail', application_id=application.id)


@admin_login_required
@require_http_methods(["POST"])
def apply_discount(request, application_id):
    """値引きを適用（管理者用）"""
    application = get_object_or_404(DiscountApplication, id=application_id)
    
    if not application.discount_applied:
        if not application.subscription_verified:
            messages.warning(request, '定期購入の確認が完了していません。先に突合を行ってください。')
            return redirect('application:discount_application_detail', application_id=application.id)
        
        application.apply_discount()
        messages.success(request, '値引きを適用しました。')
    else:
        messages.info(request, '既に値引きが適用されています。')
    
    return redirect('application:discount_application_detail', application_id=application.id)


@admin_login_required
@require_http_methods(["POST"])
def revoke_discount(request, application_id):
    """値引きを解除（管理者用）"""
    application = get_object_or_404(DiscountApplication, id=application_id)
    
    if application.discount_applied:
        application.revoke_discount()
        messages.success(request, '値引きを解除しました。')
    else:
        messages.info(request, '値引きが適用されていません。')
    
    return redirect('application:discount_application_detail', application_id=application.id)


@admin_login_required
@require_http_methods(["POST"])
def discount_application_delete(request, application_id):
    """値引き申請削除"""
    application = get_object_or_404(DiscountApplication, id=application_id)
    
    application_name = application.full_name
    application.delete()
    
    messages.success(request, f'値引き申請「{application_name}」を削除しました。')
    return redirect('application:discount_application_list')


@admin_login_required
@require_http_methods(["GET", "POST"])
def data_management(request):
    """データ管理画面（全削除機能付き）"""
    if request.method == 'POST':
        password = request.POST.get('password', '').strip()
        action = request.POST.get('action', '')
        
        # 設定ファイルのパスワードと比較
        admin_password = getattr(settings, 'ADMIN_PASSWORD', '11223456778899#JP')
        
        if password != admin_password:
            messages.error(request, 'パスワードが正しくありません。')
            # データ件数を取得
            salon_count = SalonApplication.objects.count()
            discount_count = DiscountApplication.objects.count()
            csv_count = CSVUpload.objects.count()
            subscription_count = SubscriptionUser.objects.count()
            return render(request, 'application/data_management.html', {
                'page_title': 'データ管理',
                'password_error': True,
                'salon_count': salon_count,
                'discount_count': discount_count,
                'csv_count': csv_count,
                'subscription_count': subscription_count,
            })
        
        if action == 'delete_all':
            # 全データ削除を実行
            try:
                # CSVファイルも削除
                csv_uploads = CSVUpload.objects.all()
                for csv_upload in csv_uploads:
                    if csv_upload.file_path and os.path.exists(csv_upload.file_path):
                        try:
                            os.remove(csv_upload.file_path)
                        except Exception as e:
                            pass  # ファイル削除エラーは無視
                
                # データベースから削除
                salon_count = SalonApplication.objects.count()
                discount_count = DiscountApplication.objects.count()
                csv_count = CSVUpload.objects.count()
                subscription_count = SubscriptionUser.objects.count()
                
                SalonApplication.objects.all().delete()
                DiscountApplication.objects.all().delete()
                CSVUpload.objects.all().delete()
                SubscriptionUser.objects.all().delete()
                
                messages.success(
                    request,
                    f'すべてのデータを削除しました。'
                    f'（申し込み: {salon_count}件、値引き申請: {discount_count}件、'
                    f'CSVアップロード: {csv_count}件、定期購入ユーザー: {subscription_count}件）'
                )
            except Exception as e:
                messages.error(request, f'データ削除中にエラーが発生しました: {str(e)}')
    
    # データ件数を取得
    salon_count = SalonApplication.objects.count()
    discount_count = DiscountApplication.objects.count()
    csv_count = CSVUpload.objects.count()
    subscription_count = SubscriptionUser.objects.count()
    
    return render(request, 'application/data_management.html', {
        'page_title': 'データ管理',
        'salon_count': salon_count,
        'discount_count': discount_count,
        'csv_count': csv_count,
        'subscription_count': subscription_count,
    })

