from django.db import models
from django.core.validators import EmailValidator
from django.utils import timezone


class SubscriptionUser(models.Model):
    """Joy Journeyの定期購入利用者情報"""
    email = models.EmailField(
        verbose_name='メールアドレス',
        unique=True,
        validators=[EmailValidator()]
    )
    subscription_id = models.CharField(
        verbose_name='サブスクリプションID',
        max_length=100,
        unique=True,
        help_text='Joy Journeyの定期購入の一意なID'
    )
    is_active = models.BooleanField(
        verbose_name='有効',
        default=True,
        help_text='サブスクリプションが有効かどうか'
    )
    created_at = models.DateTimeField(
        verbose_name='作成日時',
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        verbose_name='更新日時',
        auto_now=True
    )

    class Meta:
        verbose_name = '定期購入ユーザー'
        verbose_name_plural = '定期購入ユーザー'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.email} ({self.subscription_id})"


class CSVUpload(models.Model):
    """CSVアップロード情報"""
    STATUS_CHOICES = [
        ('pending', '処理待ち'),
        ('processing', '処理中'),
        ('completed', '完了'),
        ('error', 'エラー'),
    ]

    file_name = models.CharField(
        verbose_name='ファイル名',
        max_length=255
    )
    file_path = models.CharField(
        verbose_name='ファイルパス',
        max_length=500,
        blank=True
    )
    status = models.CharField(
        verbose_name='ステータス',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    total_rows = models.IntegerField(
        verbose_name='総行数',
        default=0
    )
    active_subscriptions = models.IntegerField(
        verbose_name='継続ユーザー数',
        default=0
    )
    matched_count = models.IntegerField(
        verbose_name='突合成功数',
        default=0,
        help_text='（非推奨：各突合種類別の件数を使用してください）'
    )
    # 各突合種類別の件数
    salon_match_count = models.IntegerField(
        verbose_name='サロン申請突合成功数',
        default=0,
        help_text='夜遊びサロン利用申請とCSVの突合成功数'
    )
    access_revocation_count = models.IntegerField(
        verbose_name='アクセス権剥奪必要件数',
        default=0,
        help_text='アクセス権付与済みとCSVの突合で剥奪が必要と判定された件数'
    )
    discount_match_count = models.IntegerField(
        verbose_name='値引き申請突合成功数',
        default=0,
        help_text='値引き申請とCSVの突合成功数'
    )
    discount_revocation_count = models.IntegerField(
        verbose_name='値引き剥奪必要件数',
        default=0,
        help_text='値引き適用済みとCSVの突合で剥奪が必要と判定された件数'
    )
    error_message = models.TextField(
        verbose_name='エラーメッセージ',
        blank=True
    )
    uploaded_by = models.CharField(
        verbose_name='アップロード者',
        max_length=100,
        blank=True
    )
    created_at = models.DateTimeField(
        verbose_name='アップロード日時',
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        verbose_name='更新日時',
        auto_now=True
    )

    class Meta:
        verbose_name = 'CSVアップロード'
        verbose_name_plural = 'CSVアップロード'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.file_name} ({self.get_status_display()})"


class SalonApplication(models.Model):
    """夜遊びサロン申し込み情報"""
    STATUS_CHOICES = [
        ('pending', '審査中'),
        ('verified', '確認済み'),
        ('approved', '承認済み'),
        ('rejected', '拒否'),
        ('completed', 'アクセス付与済み'),
    ]

    MATCH_METHOD_CHOICES = [
        ('email_and_name', 'メール+名前'),
        ('email_only', 'メールのみ'),
        ('name_only', '名前のみ'),
        ('manual', '手動'),
        ('', '未突合'),
    ]

    # 基本情報
    last_name = models.CharField(
        verbose_name='姓',
        max_length=50
    )
    first_name = models.CharField(
        verbose_name='名',
        max_length=50
    )
    email = models.EmailField(
        verbose_name='メールアドレス',
        validators=[EmailValidator()]
    )
    # subscription_idは後方互換性のため残すが、使用しない
    subscription_id = models.CharField(
        verbose_name='サブスクリプションID',
        max_length=100,
        blank=True,
        null=True,
        help_text='（非推奨：CSV突合で使用）'
    )

    # チェック結果
    subscription_verified = models.BooleanField(
        verbose_name='定期購入確認済み',
        default=False,
        help_text='Joy Journeyの定期購入の利用確認が完了したか'
    )
    subscription_user = models.ForeignKey(
        SubscriptionUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='applications',
        verbose_name='関連定期購入ユーザー',
        help_text='確認された定期購入ユーザー情報'
    )

    # 突合情報
    match_method = models.CharField(
        verbose_name='突合方法',
        max_length=20,
        choices=MATCH_METHOD_CHOICES,
        default='',
        blank=True,
        help_text='突合に使用した方法'
    )
    matched_at = models.DateTimeField(
        verbose_name='突合日時',
        null=True,
        blank=True,
        help_text='突合が完了した日時'
    )
    csv_upload = models.ForeignKey(
        CSVUpload,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='applications',
        verbose_name='関連CSVアップロード',
        help_text='突合に使用したCSV'
    )
    match_notes = models.TextField(
        verbose_name='突合備考',
        blank=True,
        help_text='突合時のメモ（不一致理由など）'
    )

    # ステータス
    status = models.CharField(
        verbose_name='ステータス',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # Discordアカウント情報
    discord_display_name = models.CharField(
        verbose_name='Discord表示名',
        max_length=100,
        blank=True,
        help_text='Discordの表示名（日本語可）'
    )
    discord_username = models.CharField(
        verbose_name='Discordアカウント名',
        max_length=100,
        blank=True,
        help_text='Discordのアカウント名（username#1234形式、日本語可）'
    )
    # 後方互換性のため残す（非推奨）
    discord_account_name = models.CharField(
        verbose_name='Discordアカウント名（旧）',
        max_length=100,
        blank=True,
        help_text='（非推奨：discord_display_nameとdiscord_usernameを使用してください）'
    )
    discord_account_submitted_at = models.DateTimeField(
        verbose_name='Discordアカウント名入力日時',
        null=True,
        blank=True,
        help_text='Discordアカウント名が入力された日時'
    )
    
    # アクセス付与情報
    access_granted = models.BooleanField(
        verbose_name='アクセス付与済み',
        default=False
    )
    access_granted_at = models.DateTimeField(
        verbose_name='アクセス付与日時',
        null=True,
        blank=True
    )
    
    # アクセス剥奪情報
    access_revocation_required = models.BooleanField(
        verbose_name='アクセス剥奪必要',
        default=False,
        help_text='CSV突合により「継続」以外と突合され、アクセス権の剥奪が必要な場合にマークされます'
    )
    access_revocation_required_at = models.DateTimeField(
        verbose_name='アクセス剥奪必要マーク日時',
        null=True,
        blank=True,
        help_text='アクセス剥奪必要フラグが立てられた日時'
    )
    access_revoked_at = models.DateTimeField(
        verbose_name='アクセス剥奪実行日時',
        null=True,
        blank=True,
        help_text='実際にアクセス権が剥奪された日時'
    )

    # メモ・備考
    notes = models.TextField(
        verbose_name='備考',
        blank=True,
        help_text='内部メモ'
    )

    # タイムスタンプ
    created_at = models.DateTimeField(
        verbose_name='申し込み日時',
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        verbose_name='更新日時',
        auto_now=True
    )

    class Meta:
        verbose_name = 'サロン申し込み'
        verbose_name_plural = 'サロン申し込み'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.last_name} {self.first_name} ({self.email}) - {self.get_status_display()}"

    @property
    def full_name(self):
        """フルネームを返す"""
        return f"{self.last_name} {self.first_name}"

    def grant_access(self):
        """アクセスを付与"""
        self.access_granted = True
        self.access_granted_at = timezone.now()
        self.status = 'completed'
        self.save()

    def revoke_access(self):
        """アクセスを取り消し"""
        self.access_granted = False
        self.access_granted_at = None
        self.access_revocation_required = False  # 剥奪実行時にフラグをリセット
        self.access_revoked_at = timezone.now()  # 剥奪実行日時を記録
        # ステータスは'verified'に戻す（'pending'には戻さない）
        if self.status == 'completed':
            self.status = 'verified'
        self.save()


class DiscountApplication(models.Model):
    """値引き申請情報（既存の夜遊びサロン会員向け）"""
    STATUS_CHOICES = [
        ('pending', '審査中'),
        ('verified', '確認済み'),
        ('approved', '承認済み'),
        ('rejected', '拒否'),
        ('completed', '値引き適用済み'),
    ]

    MATCH_METHOD_CHOICES = [
        ('email_and_name', 'メール+名前'),
        ('email_only', 'メールのみ'),
        ('name_only', '名前のみ'),
        ('manual', '手動'),
        ('', '未突合'),
    ]

    # 基本情報
    last_name = models.CharField(
        verbose_name='姓',
        max_length=50
    )
    first_name = models.CharField(
        verbose_name='名',
        max_length=50
    )
    email = models.EmailField(
        verbose_name='メールアドレス',
        validators=[EmailValidator()]
    )

    # チェック結果
    subscription_verified = models.BooleanField(
        verbose_name='定期購入確認済み',
        default=False,
        help_text='Joy Journeyの定期購入の利用確認が完了したか'
    )
    subscription_user = models.ForeignKey(
        SubscriptionUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='discount_applications',
        verbose_name='関連定期購入ユーザー',
        help_text='確認された定期購入ユーザー情報'
    )

    # 突合情報
    match_method = models.CharField(
        verbose_name='突合方法',
        max_length=20,
        choices=MATCH_METHOD_CHOICES,
        default='',
        blank=True,
        help_text='突合に使用した方法'
    )
    matched_at = models.DateTimeField(
        verbose_name='突合日時',
        null=True,
        blank=True,
        help_text='突合が完了した日時'
    )
    csv_upload = models.ForeignKey(
        CSVUpload,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='discount_applications',
        verbose_name='関連CSVアップロード',
        help_text='突合に使用したCSV'
    )
    match_notes = models.TextField(
        verbose_name='突合備考',
        blank=True,
        help_text='突合時のメモ（不一致理由など）'
    )

    # ステータス
    status = models.CharField(
        verbose_name='ステータス',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # Discordアカウント情報
    discord_display_name = models.CharField(
        verbose_name='Discord表示名',
        max_length=100,
        blank=True,
        help_text='Discordの表示名（日本語可）'
    )
    discord_username = models.CharField(
        verbose_name='Discordアカウント名',
        max_length=100,
        blank=True,
        help_text='Discordのアカウント名（username#1234形式、日本語可）'
    )
    discord_account_submitted_at = models.DateTimeField(
        verbose_name='Discordアカウント名入力日時',
        null=True,
        blank=True,
        help_text='Discordアカウント名が入力された日時'
    )

    # 値引き適用情報
    discount_applied = models.BooleanField(
        verbose_name='値引き適用済み',
        default=False
    )
    discount_applied_at = models.DateTimeField(
        verbose_name='値引き適用日時',
        null=True,
        blank=True
    )
    
    # 値引き剥奪情報
    discount_revocation_required = models.BooleanField(
        verbose_name='値引き剥奪必要',
        default=False,
        help_text='CSV突合により「継続」以外と突合され、値引きの剥奪が必要な場合にマークされます'
    )
    discount_revocation_required_at = models.DateTimeField(
        verbose_name='値引き剥奪必要マーク日時',
        null=True,
        blank=True,
        help_text='値引き剥奪必要フラグが立てられた日時'
    )
    discount_revoked_at = models.DateTimeField(
        verbose_name='値引き剥奪実行日時',
        null=True,
        blank=True,
        help_text='実際に値引きが剥奪された日時'
    )

    # メモ・備考
    notes = models.TextField(
        verbose_name='備考',
        blank=True,
        help_text='内部メモ'
    )

    # タイムスタンプ
    created_at = models.DateTimeField(
        verbose_name='申請日時',
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        verbose_name='更新日時',
        auto_now=True
    )

    class Meta:
        verbose_name = '値引き申請'
        verbose_name_plural = '値引き申請'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.last_name} {self.first_name} ({self.email}) - {self.get_status_display()}"

    @property
    def full_name(self):
        """フルネームを返す"""
        return f"{self.last_name} {self.first_name}"

    def apply_discount(self):
        """値引きを適用"""
        self.discount_applied = True
        self.discount_applied_at = timezone.now()
        self.status = 'completed'
        self.save()

    def revoke_discount(self):
        """値引きを解除"""
        self.discount_applied = False
        self.discount_applied_at = None
        self.discount_revocation_required = False  # 剥奪実行時にフラグをリセット
        self.discount_revoked_at = timezone.now()  # 剥奪実行日時を記録
        # ステータスは'verified'に戻す（'pending'には戻さない）
        if self.status == 'completed':
            self.status = 'verified'
        self.save()
