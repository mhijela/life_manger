from django import forms
from .models import Asset, AssetCategory

FC = {'class': 'form-control'}
FS = {'class': 'form-select'}


class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = ['name', 'serial_number', 'category', 'assigned_to', 'assignment_date', 'status', 'notes']
        widgets = {
            'name': forms.TextInput(attrs=FC),
            'serial_number': forms.TextInput(attrs=FC),
            'category': forms.Select(attrs=FS),
            'assigned_to': forms.Select(attrs=FS),
            'assignment_date': forms.DateInput(attrs={**FC, 'type': 'date'}),
            'status': forms.Select(attrs=FS),
            'notes': forms.Textarea(attrs={**FC, 'rows': 2}),
        }
