# your_app_name/models.py
from django.contrib.auth.models import User
from django.db import models
from django.utils.timezone import now



class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    phone = models.CharField(max_length=20, blank=True, null=True) # <-- ADD THIS LINE
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name} - {self.subject}"

    class Meta:
        verbose_name = "Contact Message"
        verbose_name_plural = "Contact Messages"
        ordering = ['-sent_at']


class UserHistory(models.Model):
    """
    Model to store calculation history for authenticated users.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='calculation_history')
    tool_name = models.CharField(max_length=100, blank=True, null=True) # <-- ADDED BLANK=TRUE, NULL=TRUE
    input_data = models.TextField(blank=True, null=True)
    result_data = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(default=now) 
    city = models.CharField(max_length=100, blank=True, null=True)       # ✅ new field
    country = models.CharField(max_length=100, blank=True, null=True)    # ✅ optional
    user_email = models.EmailField(blank=True, null=True)                # ✅ optional
    username = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s {self.tool_name} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        verbose_name = "User History Entry"
        verbose_name_plural = "User History Entries"
        ordering = ['-created_at']
        
        

class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=128, unique=True)
    created_at = models.DateTimeField()

    def __str__(self):
        return f"{self.user.email} - {self.token}"

    def is_expired(self):
        from django.utils import timezone
        from datetime import timedelta
        return timezone.now() > self.created_at + timedelta(hours=1)
