from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Main dashboard
    path('', views.dashboard_view, name='dashboard'),

    # Employee views
    path('employee/', views.employee_dashboard_view, name='employee_dashboard'),
    path('submit/', views.submit_report_view, name='submit_report'),
    path('report/<int:pk>/edit/', views.submit_report_view, name='edit_report'),
    path('my-reports/', views.my_reports_view, name='my_reports'),

    # Report detail
    path('report/<int:pk>/', views.report_detail_view, name='report_detail'),

    # Manager views
    path('manager/', views.manager_dashboard_view, name='manager_dashboard'),
    path('manager/export/', views.export_reports_excel, name='export_reports_excel'),
    path('review/<int:pk>/', views.review_report_view, name='review_report'),
]
