from django.contrib import admin

from grading.models import Attendance, Course, Grade, Lesson, StudentCourse


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'teacher', 'group', 'semester', 'year')
    list_filter = ('semester', 'year', 'subject', 'teacher', 'group')
    search_fields = ('subject__name', 'group__name', 'teacher__user__username')


@admin.register(StudentCourse)
class StudentCourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'course')
    list_filter = ('course',)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('id', 'course', 'date', 'topic')
    list_filter = ('course', 'date')


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('id', 'lesson', 'student', 'status')
    list_filter = ('status',)


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'course', 'value', 'date')
    list_filter = ('course',)
