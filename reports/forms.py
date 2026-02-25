from django import forms

from core.models import Group
from grading.models import Course


class StatementReportForm(forms.Form):
    group = forms.ModelChoiceField(queryset=Group.objects.all())
    subject_course = forms.ModelChoiceField(queryset=Course.objects.select_related('subject', 'group'))
    semester = forms.CharField(max_length=20)


class GroupForm(forms.Form):
    group = forms.ModelChoiceField(queryset=Group.objects.all())
