from django.contrib import admin

from users.models import Student, Teacher


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'department', 'source', 'is_active')
    list_filter = ('department', 'source', 'is_active')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'group', 'date_of_birth')
    list_filter = ('group',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
