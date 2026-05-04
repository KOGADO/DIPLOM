from django import forms

from users.models import ChatMessage, Parent, Student, Teacher


class TeacherForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = ['user']


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['user', 'group', 'date_of_birth']


class ParentForm(forms.ModelForm):
    class Meta:
        model = Parent
        fields = ['user', 'children']


class ChatDialogForm(forms.Form):
    teacher = forms.ModelChoiceField(label='Преподаватель', queryset=Teacher.objects.none())
    title = forms.CharField(label='Тема', max_length=255)
    message = forms.CharField(label='Сообщение', widget=forms.Textarea(attrs={'rows': 4}))

    def __init__(self, *args, student=None, grade=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.student = student
        self.grade = grade
        teachers = Teacher.objects.none()
        if student:
            teachers = Teacher.objects.filter(courses__group=student.group).select_related('user').distinct()
        if grade:
            teachers = Teacher.objects.filter(pk=grade.course.teacher_id).select_related('user')
            self.fields['teacher'].initial = grade.course.teacher_id
            self.fields['teacher'].disabled = True
            self.fields['title'].initial = f'Вопрос по оценке {grade.value} — {grade.course.subject}'
        self.fields['teacher'].queryset = teachers
        for field in self.fields.values():
            if getattr(field.widget, 'input_type', '') == 'select':
                field.widget.attrs.setdefault('class', 'form-select')
            else:
                field.widget.attrs.setdefault('class', 'form-control')

    def clean_teacher(self):
        teacher = self.cleaned_data['teacher']
        if self.grade and teacher.pk != self.grade.course.teacher_id:
            raise forms.ValidationError('Для вопроса по оценке выбран неверный преподаватель.')
        return teacher


class ChatMessageForm(forms.ModelForm):
    class Meta:
        model = ChatMessage
        fields = ['message', 'attachment']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Введите сообщение...'}),
            'attachment': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


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
