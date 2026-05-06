from django import forms
from .models import SupportTicket, TicketMessage

class SupportTicketForm(forms.ModelForm):
    """
    Form for creating a new support ticket.
    """
    class Meta:
        model = SupportTicket
        fields = ['subject', 'category', 'description']
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Briefly describe your issue'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Detailed explanation...'}),
        }

class TicketMessageForm(forms.ModelForm):
    """
    Form for posting a message to a support ticket.
    """
    class Meta:
        model = TicketMessage
        fields = ['message', 'attachment']
        widgets = {
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Type your message here...'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_attachment(self):
        """
        Validate attachment size (limit 5MB).
        """
        attachment = self.cleaned_data.get('attachment')
        if attachment:
            if attachment.size > 5 * 1024 * 1024:
                raise forms.ValidationError("The file is too large. Please upload an attachment smaller than 5MB.")
        return attachment

    def clean(self):
        """
        Ensure at least a message or an attachment is provided.
        """
        cleaned_data = super().clean()
        message = cleaned_data.get('message')
        attachment = cleaned_data.get('attachment')

        if not message and not attachment:
            raise forms.ValidationError("Please enter a message or attach a file.")
        
        return cleaned_data
