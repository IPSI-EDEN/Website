from django import forms
from django.forms.models import inlineformset_factory
from .models import *

class RaspberryForm(forms.ModelForm):
    class Meta:
        model = Raspberry
        fields = ['device_id', 'group','location_description','active','status']
        labels = {
            'device_id': 'Device ID',
            'group': 'Group',
            'location_description': 'Location Description',
            'active': 'Active',
            'status': 'Status'
        }
        widgets = {
            'device_id': forms.TextInput(attrs={'class': 'form-control'}),
            'group': forms.Select(attrs={'class': 'form-control'}),
            'location_description': forms.Textarea(attrs={'class': 'form-control'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'status': forms.Select(attrs={'class': 'form-control'})
        }