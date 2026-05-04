from django.urls import path

from core import admin_panel

app_name = 'admin_panel'

urlpatterns = [
    path('', admin_panel.AdminIndexView.as_view(), name='index'),
    path('<str:model_key>/', admin_panel.AdminModelListView.as_view(), name='list'),
    path('<str:model_key>/add/', admin_panel.AdminObjectFormView.as_view(), name='add'),
    path('<str:model_key>/<int:pk>/change/', admin_panel.AdminObjectFormView.as_view(), name='change'),
    path('<str:model_key>/<int:pk>/delete/', admin_panel.AdminObjectDeleteView.as_view(), name='delete'),
    path('<str:model_key>/<int:pk>/history/', admin_panel.AdminObjectHistoryView.as_view(), name='history'),
]
