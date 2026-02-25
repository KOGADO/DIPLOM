from django.contrib import admin

from core.models import Department, Group, Subject


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'department', 'curator', 'source', 'is_active')
    list_filter = ('is_active', 'source', 'department')
    search_fields = ('name',)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'department', 'source', 'is_active')
    list_filter = ('is_active', 'source', 'department')
    search_fields = ('name',)
