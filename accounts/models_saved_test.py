from django.db import models
from django.contrib.auth.models import User
from .models import Test

class SavedTest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_tests')
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='users_saved')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'test']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.test.title}"
