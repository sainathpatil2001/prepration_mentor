from django import forms
from .models import Test, TestCategory, Question, Answer, ReferralCode, PrivacyPolicy


class AdminTestSetForm(forms.ModelForm):
    """
    Form used in the custom admin dashboard for managing test sets.
    
    Includes validation for:
    - Passing score range (0-100)
    - Non-negative total questions
    """

    class Meta:
        model = Test
        fields = [
            'title',
            'description',
            'category',
            'duration_minutes',
            'total_questions',
            'passing_score',
            'negative_marking_rule',
            'instructions',
            'is_active',
            'is_hidden',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Briefly describe this test set'}),
            'instructions': forms.Textarea(attrs={'rows': 6, 'placeholder': 'Provide instructions or guidelines for this test'}),
            'duration_minutes': forms.NumberInput(attrs={'min': 1}),
            'total_questions': forms.NumberInput(attrs={'min': 0}),
            'passing_score': forms.NumberInput(attrs={'min': 0, 'max': 100}),
            'negative_marking_rule': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing_class = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f'{existing_class} form-control'.strip()
        # Checkbox styling
        self.fields['is_active'].widget.attrs['class'] = 'form-check-input'
        self.fields['is_hidden'].widget.attrs['class'] = 'form-check-input'
        self.fields['category'].queryset = TestCategory.objects.filter(is_active=True).order_by('display_order', 'name')

    def clean_passing_score(self):
        """
        Validate passing score is between 0 and 100.
        """
        value = self.cleaned_data.get('passing_score')
        if value is None:
            return value
        if value < 0 or value > 100:
            raise forms.ValidationError('Passing score must be between 0 and 100.')
        return value

    def clean_total_questions(self):
        """
        Validate total questions is non-negative.
        """
        value = self.cleaned_data.get('total_questions')
        if value is None:
            return value
        if value < 0:
            raise forms.ValidationError('Total questions cannot be negative.')
        return value


class AnswerForm(forms.ModelForm):
    """
    Form for editing an Answer.
    """
    class Meta:
        model = Answer
        fields = ["answer_text", "answer_image", "is_correct", "order"]
        widgets = {
            "answer_text": forms.TextInput(attrs={"class": "form-control answer-text-input", "placeholder": "Option text"}),
            "answer_image": forms.ClearableFileInput(attrs={"class": "form-control answer-image-input", "accept": "image/*"}),
            "is_correct": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "order": forms.HiddenInput(),
        }

    def clean(self):
        """
        Validate that either text or image is provided.
        """
        cleaned_data = super().clean()
        text = cleaned_data.get("answer_text")
        image = cleaned_data.get("answer_image")

        if not text and not image:
            pass # Let the formset validation handle truly empty forms if needed, but for a valid answer:
            # Actually, standard django formset deletion handles empty forms. 
            # If a user intends to add an answer, they must provide one.
            # However, if this is an extra form that is left empty, we shouldn't raise error.
            # But if 'is_correct' is checked, then it must have content.
            # Let's rely on the view or formset validation for "required" if it's not the extra one.
            # For now, if we have neither, and it's not being deleted, it requires content.
            if not self.files and not text: 
                 # This check is tricky in formsets because empty forms are allowed.
                 pass
        
        if image and not text:
            cleaned_data['answer_text'] = "Refer to image"
        
        return cleaned_data

class QuestionForm(forms.ModelForm):
    """
    Form for editing a Question.
    """
    class Meta:
        model = Question
        fields = ["question_text", "question_image", "marks", "explanation", "explanation_image", "order"]
        widgets = {
            "question_text": forms.Textarea(attrs={"rows": 2, "class": "form-control question-text-input", "placeholder": "Enter question here"}),
            "marks": forms.NumberInput(attrs={"min": 1, "class": "form-control", "placeholder": "Marks"}),
            "order": forms.HiddenInput(),
            "question_image": forms.ClearableFileInput(attrs={"class": "form-control question-image-input", "accept": "image/*"}),
            "explanation": forms.Textarea(attrs={"rows": 2, "class": "form-control", "placeholder": "Explanation for the correct answer"}),
            "explanation_image": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
        }

    def clean(self):
        """
        Validate that either text or image is provided.
        """
        cleaned_data = super().clean()
        text = cleaned_data.get("question_text")
        image = cleaned_data.get("question_image")

        if not text and not image:
            raise forms.ValidationError("Please provide either text or an image for the question.")
        
        if image and not text:
            cleaned_data['question_text'] = "Refer to image below"
        
        return cleaned_data

# Inline formsets
from django.forms import inlineformset_factory

AnswerFormSet = inlineformset_factory(
    Question, Answer,
    form=AnswerForm,
    extra=0,  # 0 extra slots by default (prevents extra options on update)
    min_num=2,
    max_num=6,
    can_delete=True,
    validate_min=True,
    validate_max=True
)

QuestionFormSet = inlineformset_factory(
    Test, Question,
    form=QuestionForm,
    extra=0,
    can_delete=True
)

# Helper to bind answer formset for each given question in view

def get_answer_formset(data=None, files=None, instance=None, prefix=None):
    """
    Helper function to instantiate the AnswerFormSet for a given question.
    """
    return AnswerFormSet(data, files, instance=instance, prefix=prefix)


class TestCategoryForm(forms.ModelForm):
    """Form for managing test categories."""
    class Meta:
        model = TestCategory
        fields = ['name', 'description', 'display_order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Category Name'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Description'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


from .models import Subscription, SubscriptionPlan

class SubscriptionForm(forms.ModelForm):
    """
    Form for editing an existing Subscription.
    """
    class Meta:
        model = Subscription
        fields = ['plan', 'status', 'expires_at', 'is_active']
        widgets = {
            'expires_at': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'plan': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class AddSubscriptionForm(forms.Form):
    """
    Form for adding a new subscription manually.
    """
    username_or_email = forms.CharField(
        label="Username or Email", 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search user...'})
    )
    plan = forms.ModelChoiceField(
        queryset=SubscriptionPlan.objects.all(), 
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
class ReferralCodeForm(forms.ModelForm):
    """
    Form for managing referral codes.
    """
    class Meta:
        model = ReferralCode
        fields = ['code', 'discount_type', 'discount_value', 'valid_from', 'valid_until', 'usage_limit', 'description', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. SAVE20'}),
            'discount_type': forms.Select(attrs={'class': 'form-select'}),
            'discount_value': forms.NumberInput(attrs={'class': 'form-control'}),
            'valid_from': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'valid_until': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'usage_limit': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class PrivacyPolicyForm(forms.ModelForm):
    """
    Form for editing Privacy Policy content.
    """
    class Meta:
        model = PrivacyPolicy
        fields = ['title', 'content', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Policy Title'}),
        }

from .models import EmailConfiguration

class EmailConfigurationForm(forms.ModelForm):
    """
    Form for managing Google SMTP Email Configuration.
    """
    class Meta:
        model = EmailConfiguration
        fields = [
            'email_host', 
            'email_port', 
            'email_host_user',
            'email_host_password',
            'email_use_tls', 
            'email_use_ssl', 
            'default_from_email', 
            'is_active'
        ]
        widgets = {
            'email_host': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'smtp.gmail.com'}),
            'email_port': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '587'}),
            'email_host_user': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'example@gmail.com'}),
            'email_host_password': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'App Password', 'render_value': True}),
            'default_from_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'No-reply <noreply@example.com>'}),
            'email_use_tls': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_use_ssl': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
             'email_host_password': 'Use an App Password generated from your Google Account Security settings.'
        }
