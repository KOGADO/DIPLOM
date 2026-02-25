from django import forms

from core.models import Group, Subject


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name', 'curator']


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name']
