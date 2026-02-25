from django.urls import path

from reports import views

urlpatterns = [
    path('reports/group-statement/', views.group_statement_report, name='report_group_statement'),
    path('reports/top-students/', views.top_students_report, name='report_top_students'),
    path('reports/attendance/', views.attendance_report, name='report_attendance'),
]
