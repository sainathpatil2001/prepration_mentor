from django.db import models

class MotivationQuote(models.Model):
    quote = models.TextField()
    author = models.CharField(max_length=100, blank=True, null=True, default="Unknown")
    display_date = models.DateField(unique=True, help_text="Date when this quote should be displayed")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-display_date']

    def __str__(self):
        return f"{self.quote[:50]}... ({self.display_date})"
