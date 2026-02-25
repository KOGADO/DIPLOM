from django import forms

from grading.models import Attendance, Grade, Lesson


class GradeForm(forms.ModelForm):
    class Meta:
        model = Grade
        fields = ['student', 'course', 'value', 'date', 'comment']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_value(self):
        value = self.cleaned_data['value']
        if value < 2 or value > 5:
            raise forms.ValidationError('Оценка должна быть в диапазоне 2-5.')
        return value


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['course', 'date', 'topic']


class BulkGradeForm(forms.Form):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    comment = forms.CharField(required=False)


class AttendanceRowForm(forms.Form):
    status = forms.ChoiceField(choices=Attendance.Status.choices)
    comment = forms.CharField(required=False)
