from django import forms
from .models import ContactMessage
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV2Checkbox





class ContactForm(forms.Form):
    name = forms.CharField(label=_("Name"), max_length=100, widget=forms.TextInput(attrs={
        'placeholder': _('Your full name'),
    }))
    email = forms.EmailField(label=_("Email"), widget=forms.EmailInput(attrs={
        'placeholder': _('your@email.com'),
    }))
    subject = forms.CharField(label=_("Subject"), max_length=150, widget=forms.TextInput(attrs={
        'placeholder': _('Subject of your message'),
    }))
    message = forms.CharField(label=_("Message"), widget=forms.Textarea(attrs={
        'placeholder': _('Type your message here...'),
        'rows': 5
    }))
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox)

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords do not match.")