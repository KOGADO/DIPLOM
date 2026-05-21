from django.conf import settings
from django.urls import path

from grading import views

urlpatterns = [
    path('courses/', views.CourseListView.as_view(), name='course_list'),
    path('courses/add/', views.CourseCreateView.as_view(), name='course_add'),
    path('courses/<int:pk>/', views.CourseDetailView.as_view(), name='course_detail'),
    path('courses/<int:pk>/journal/', views.course_journal_view, name='course_journal'),
    path('courses/<int:pk>/edit/', views.CourseUpdateView.as_view(), name='course_edit'),
    path('courses/<int:pk>/delete/', views.CourseDeleteView.as_view(), name='course_delete'),
    path('courses/<int:course_id>/lessons/add/', views.LessonCreateView.as_view(), name='lesson_add'),
    path('lessons/<int:lesson_id>/attendance/', views.attendance_mark_view, name='attendance_mark'),
]

if not settings.IS_FROZEN:
    from grading import api_views

    urlpatterns += [
        path('api/my-grades/', api_views.MyGradesApiView.as_view(), name='api_my_grades'),
        path('api/my-courses/', api_views.TeacherCoursesApiView.as_view(), name='api_teacher_courses'),
    ]
