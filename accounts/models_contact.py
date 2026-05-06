from django.db import models
from django.utils import timezone

class ContactQuery(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    submitted_at = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-submitted_at']
        verbose_name = "Contact Query"
        verbose_name_plural = "Contact Queries"

    def __str__(self):
        return f"{self.name} - {self.email}"
