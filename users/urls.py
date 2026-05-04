from django.urls import path

from users import views

urlpatterns = [
    path('chats/', views.ChatListView.as_view(), name='chat_list'),
    path('chats/new/', views.ChatCreateView.as_view(), name='chat_new'),
    path('chats/<int:pk>/', views.ChatDetailView.as_view(), name='chat_detail'),
    path('groups/<int:group_id>/import-students/', views.import_students_to_group_view, name='group_students_import'),
    path('teachers/', views.TeacherListView.as_view(), name='teacher_list'),
    path('teachers/add/', views.TeacherCreateView.as_view(), name='teacher_add'),
    path('teachers/<int:pk>/edit/', views.TeacherUpdateView.as_view(), name='teacher_edit'),
    path('teachers/<int:pk>/delete/', views.TeacherDeleteView.as_view(), name='teacher_delete'),
    path('parents/', views.ParentListView.as_view(), name='parent_list'),
    path('parents/add/', views.ParentCreateView.as_view(), name='parent_add'),
    path('parents/<int:pk>/edit/', views.ParentUpdateView.as_view(), name='parent_edit'),
    path('parents/<int:pk>/delete/', views.ParentDeleteView.as_view(), name='parent_delete'),
    path('parent-dashboard/', views.ParentDashboardView.as_view(), name='parent_dashboard'),
    path('students/', views.StudentListView.as_view(), name='student_list'),
    path('students/add/', views.StudentCreateView.as_view(), name='student_add'),
    path('students/<int:pk>/edit/', views.StudentUpdateView.as_view(), name='student_edit'),
    path('students/<int:pk>/delete/', views.StudentDeleteView.as_view(), name='student_delete'),
    path(
        'students/<int:student_id>/courses/<int:course_id>/journal/',
        views.StudentCourseJournalView.as_view(),
        name='student_course_journal',
    ),
    path('students/<int:pk>/', views.StudentDetailView.as_view(), name='student_detail'),
]
