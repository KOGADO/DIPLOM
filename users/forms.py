from django import forms

from users.models import Student, Teacher


class TeacherForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = ['user']


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['user', 'group', 'date_of_birth']


class StudentImportForm(forms.Form):
    file = forms.FileField(label='Excel файл (.xlsx) со списком ФИО')
    default_password = forms.CharField(
        label='Пароль для новых аккаунтов',
        required=False,
        initial='student123',
    )

    def clean_file(self):
        file_obj = self.cleaned_data['file']
        if not file_obj.name.lower().endswith('.xlsx'):
            raise forms.ValidationError('Поддерживается только формат .xlsx')
        return file_obj
