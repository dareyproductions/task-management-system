from django import forms
from django.contrib.auth.models import User
from .models import Profile, Task, Comment

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")
    role = forms.ChoiceField(choices=Profile.Role.choices, required=True)

    class Meta:
        model = User
        fields = ['username', 'email']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password2 = cleaned_data.get("password2")

        if password and password2 and password != password2:
            raise forms.ValidationError("Passwords do not match.")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])  # Hash the password
        if commit:
            user.save()
            Profile.objects.create(user=user, role=self.cleaned_data['role'])
        return user


    
class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'priority', 'status', 'due_date', 'assigned_to']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'assigned_to': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super(TaskForm, self).__init__(*args, **kwargs)
        # ✅ Filter "assigned_to" so it only shows Developers
        self.fields['assigned_to'].queryset = User.objects.filter(profile__role='Developer')

class TaskUpdateForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['status', 'project_link']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'project_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Enter project link (if applicable)'}),
        }

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Write a comment...'}),
        }
