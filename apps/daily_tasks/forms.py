from django import forms

from .models import DailyTask

FORM_CONTROL = {'class': 'form-control'}
FORM_SELECT = {'class': 'form-select'}


class DailyTaskForm(forms.ModelForm):
    class Meta:
        model = DailyTask
        fields = [
            'title',
            'task_type',
            'description',
            'scheduled_date',
            'scheduled_time',
            'priority',
            'status',
            'assigned_to',
            'subscriber',
            'device',
            'location',
            'completion_notes',
        ]
        widgets = {
            'title': forms.TextInput(attrs=FORM_CONTROL),
            'task_type': forms.Select(attrs=FORM_SELECT),
            'description': forms.Textarea(attrs={**FORM_CONTROL, 'rows': 4}),
            'scheduled_date': forms.DateInput(attrs={**FORM_CONTROL, 'type': 'date'}),
            'scheduled_time': forms.TimeInput(attrs={**FORM_CONTROL, 'type': 'time'}),
            'priority': forms.Select(attrs=FORM_SELECT),
            'status': forms.Select(attrs=FORM_SELECT),
            'assigned_to': forms.Select(attrs=FORM_SELECT),
            'subscriber': forms.Select(attrs=FORM_SELECT),
            'device': forms.Select(attrs=FORM_SELECT),
            'location': forms.TextInput(attrs=FORM_CONTROL),
            'completion_notes': forms.Textarea(attrs={**FORM_CONTROL, 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_to'].queryset = (
            self.fields['assigned_to'].queryset.filter(is_active=True).order_by(
                'first_name', 'last_name', 'email'
            )
        )
        self.fields['subscriber'].queryset = (
            self.fields['subscriber'].queryset.order_by('full_name')
        )
        self.fields['device'].queryset = self.fields['device'].queryset.order_by('name')
