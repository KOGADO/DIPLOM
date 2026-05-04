from django.contrib import admin

from users.models import ChatDialog, ChatMessage, Parent, Student, Teacher


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


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    filter_horizontal = ('children',)


@admin.register(ChatDialog)
class ChatDialogAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'student', 'teacher', 'related_grade', 'updated_at')
    list_filter = ('teacher', 'student', 'related_grade')
    search_fields = ('title', 'student__user__username', 'teacher__user__username')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'chat', 'sender', 'sender_role', 'created_at', 'is_read')
    list_filter = ('sender_role', 'is_read')
    search_fields = ('message', 'sender__username', 'chat__title')
