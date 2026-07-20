from django import forms
from .models import Device, MaintenanceNote

FC = {'class': 'form-control'}
FS = {'class': 'form-select'}


class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = [
            'name', 'device_type', 'ip_address', 'mac_address', 'location',
            'serial_number', 'username', 'password', 'status',
            'purchase_date', 'warranty_date', 'subscriber', 'notes',
        ]
        widgets = {
            'name': forms.TextInput(attrs=FC),
            'device_type': forms.Select(attrs=FS),
            'ip_address': forms.TextInput(attrs=FC),
            'mac_address': forms.TextInput(attrs=FC),
            'location': forms.TextInput(attrs=FC),
            'serial_number': forms.TextInput(attrs=FC),
            'username': forms.TextInput(attrs=FC),
            'password': forms.PasswordInput(attrs=FC, render_value=True),
            'status': forms.Select(attrs=FS),
            'purchase_date': forms.DateInput(attrs={**FC, 'type': 'date'}),
            'warranty_date': forms.DateInput(attrs={**FC, 'type': 'date'}),
            'subscriber': forms.Select(attrs=FS),
            'notes': forms.Textarea(attrs={**FC, 'rows': 2}),
        }


class MaintenanceNoteForm(forms.ModelForm):
    class Meta:
        model = MaintenanceNote
        fields = ['date', 'description']
        widgets = {
            'date': forms.DateInput(attrs={**FC, 'type': 'date'}),
            'description': forms.Textarea(attrs={**FC, 'rows': 3}),
        }
