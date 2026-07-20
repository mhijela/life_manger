from django import forms
from .models import InventoryItem, StockMovement, Unit

FC = {'class': 'form-control'}
FS = {'class': 'form-select'}


class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = ['name', 'category', 'quantity', 'unit', 'purchase_price', 'selling_price', 'supplier', 'min_stock', 'notes']
        widgets = {f: forms.TextInput(attrs=FC) for f in ['name', 'category', 'supplier']}
        widgets.update({
            'quantity': forms.NumberInput(attrs=FC),
            'unit': forms.Select(attrs=FS),
            'purchase_price': forms.NumberInput(attrs={**FC, 'step': '0.01'}),
            'selling_price': forms.NumberInput(attrs={**FC, 'step': '0.01'}),
            'min_stock': forms.NumberInput(attrs=FC),
            'notes': forms.Textarea(attrs={**FC, 'rows': 2}),
        })


class StockMovementForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ['item', 'movement_type', 'quantity', 'date', 'notes']
        widgets = {
            'item': forms.Select(attrs=FS),
            'movement_type': forms.Select(attrs=FS),
            'quantity': forms.NumberInput(attrs=FC),
            'date': forms.DateInput(attrs={**FC, 'type': 'date'}),
            'notes': forms.Textarea(attrs={**FC, 'rows': 2}),
        }
