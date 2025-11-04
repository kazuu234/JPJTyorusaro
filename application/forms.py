from django import forms
from .models import SalonApplication, SubscriptionUser, CSVUpload, DiscountApplication


class SalonApplicationForm(forms.ModelForm):
    """夜遊びサロン申し込みフォーム"""
    
    class Meta:
        model = SalonApplication
        fields = ['last_name', 'first_name', 'email']
        widgets = {
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '姓を入力してください',
                'required': True
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '名を入力してください',
                'required': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'example@email.com',
                'required': True
            }),
        }
        labels = {
            'last_name': '姓',
            'first_name': '名',
            'email': 'メールアドレス',
        }
        help_texts = {
            'email': 'Joy Journeyの定期購入で登録されているメールアドレスを入力してください。',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            if field.required:
                field.widget.attrs['required'] = True

    def clean_email(self):
        """メールアドレスの検証"""
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower().strip()
            # 既存の申し込みをチェック（重複チェックは要件に応じて調整）
            existing = SalonApplication.objects.filter(
                email=email,
                status__in=['pending', 'verified', 'approved', 'completed']
            ).exclude(pk=self.instance.pk if self.instance.pk else None)
            
            if existing.exists():
                latest = existing.first()
                if latest.status == 'completed':
                    raise forms.ValidationError(
                        'このメールアドレスは既にアクセスが付与されています。'
                    )
                elif latest.status in ['pending', 'verified', 'approved']:
                    raise forms.ValidationError(
                        'このメールアドレスで既に申し込みがあります。審査中ですのでしばらくお待ちください。'
                    )
        return email


class CSVUploadForm(forms.ModelForm):
    """CSVアップロードフォーム"""
    csv_file = forms.FileField(
        label='CSVファイル',
        help_text='Joy Journeyの定期購入の利用者CSVファイルをアップロードしてください。',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv',
        })
    )

    class Meta:
        model = CSVUpload
        fields = ['file_name']
        widgets = {
            'file_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ファイル名（自動入力）',
            }),
        }
        labels = {
            'file_name': 'ファイル名',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file_name'].widget.attrs['readonly'] = True
        self.fields['file_name'].required = False

    def clean_csv_file(self):
        """CSVファイルの検証"""
        csv_file = self.cleaned_data.get('csv_file')
        if csv_file:
            # ファイル拡張子のチェック
            if not csv_file.name.endswith('.csv'):
                raise forms.ValidationError('CSVファイルをアップロードしてください。')
            # ファイルサイズのチェック（10MB制限）
            if csv_file.size > 10 * 1024 * 1024:
                raise forms.ValidationError('ファイルサイズは10MB以下にしてください。')
        return csv_file

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.cleaned_data.get('csv_file'):
            instance.file_name = self.cleaned_data['csv_file'].name
        if commit:
            instance.save()
        return instance


class DiscordAccountForm(forms.ModelForm):
    """Discordアカウント名入力フォーム"""
    
    class Meta:
        model = SalonApplication
        fields = ['discord_display_name', 'discord_username']
        widgets = {
            'discord_display_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Discord表示名を入力してください（日本語可）',
                'required': True
            }),
            'discord_username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Discordアカウント名を入力してください（例: username#1234、日本語可）',
                'required': True
            }),
        }
        labels = {
            'discord_display_name': 'Discord表示名',
            'discord_username': 'Discordアカウント名',
        }
        help_texts = {
            'discord_display_name': 'Discordの表示名を入力してください（日本語可）。',
            'discord_username': 'Discordのアカウント名を入力してください（username#1234形式、日本語可）。',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['discord_display_name'].widget.attrs['class'] = 'form-control'
        self.fields['discord_display_name'].widget.attrs['required'] = True
        self.fields['discord_username'].widget.attrs['class'] = 'form-control'
        self.fields['discord_username'].widget.attrs['required'] = True

    def clean_discord_display_name(self):
        """Discord表示名の検証"""
        discord_display_name = self.cleaned_data.get('discord_display_name')
        if discord_display_name:
            discord_display_name = discord_display_name.strip()
            if len(discord_display_name) < 1:
                raise forms.ValidationError('Discord表示名は1文字以上で入力してください。')
            if len(discord_display_name) > 100:
                raise forms.ValidationError('Discord表示名は100文字以内で入力してください。')
        return discord_display_name

    def clean_discord_username(self):
        """Discordアカウント名の検証"""
        discord_username = self.cleaned_data.get('discord_username')
        if discord_username:
            discord_username = discord_username.strip()
            if len(discord_username) < 1:
                raise forms.ValidationError('Discordアカウント名は1文字以上で入力してください。')
            if len(discord_username) > 100:
                raise forms.ValidationError('Discordアカウント名は100文字以内で入力してください。')
        return discord_username


class DiscountApplicationForm(forms.ModelForm):
    """値引き申請フォーム"""
    
    class Meta:
        model = DiscountApplication
        fields = ['last_name', 'first_name', 'email', 'discord_display_name', 'discord_username']
        widgets = {
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '姓を入力してください',
                'required': True
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '名を入力してください',
                'required': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'example@email.com',
                'required': True
            }),
            'discord_display_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Discord表示名を入力してください（日本語可）',
                'required': True
            }),
            'discord_username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Discordアカウント名を入力してください（例: username#1234、日本語可）',
                'required': True
            }),
        }
        labels = {
            'last_name': '姓',
            'first_name': '名',
            'email': 'メールアドレス',
            'discord_display_name': 'Discord表示名',
            'discord_username': 'Discordアカウント名',
        }
        help_texts = {
            'email': 'Joy Journeyの定期購入で登録されているメールアドレスを入力してください。',
            'discord_display_name': 'Discordの表示名を入力してください（日本語可）。',
            'discord_username': 'Discordのアカウント名を入力してください（username#1234形式、日本語可）。',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            if field.required:
                field.widget.attrs['required'] = True

    def clean_email(self):
        """メールアドレスの検証"""
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower().strip()
            # 既存の申請をチェック
            existing = DiscountApplication.objects.filter(
                email=email,
                status__in=['pending', 'verified', 'approved', 'completed']
            ).exclude(pk=self.instance.pk if self.instance.pk else None)
            
            if existing.exists():
                latest = existing.first()
                if latest.status == 'completed':
                    raise forms.ValidationError(
                        'このメールアドレスは既に値引きが適用されています。'
                    )
                elif latest.status in ['pending', 'verified', 'approved']:
                    raise forms.ValidationError(
                        'このメールアドレスで既に申請があります。審査中ですのでしばらくお待ちください。'
                    )
        return email

    def clean_discord_display_name(self):
        """Discord表示名の検証"""
        discord_display_name = self.cleaned_data.get('discord_display_name')
        if discord_display_name:
            discord_display_name = discord_display_name.strip()
            if len(discord_display_name) < 1:
                raise forms.ValidationError('Discord表示名は1文字以上で入力してください。')
            if len(discord_display_name) > 100:
                raise forms.ValidationError('Discord表示名は100文字以内で入力してください。')
        return discord_display_name

    def clean_discord_username(self):
        """Discordアカウント名の検証"""
        discord_username = self.cleaned_data.get('discord_username')
        if discord_username:
            discord_username = discord_username.strip()
            if len(discord_username) < 1:
                raise forms.ValidationError('Discordアカウント名は1文字以上で入力してください。')
            if len(discord_username) > 100:
                raise forms.ValidationError('Discordアカウント名は100文字以内で入力してください。')
        return discord_username
