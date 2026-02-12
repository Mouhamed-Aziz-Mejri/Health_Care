from django.urls import path
from . import views

urlpatterns = [
    # Auth URLs
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    
    # Landing
    # path('', views.landing_page, name='landing'),
    path('', views.home_page, name='home'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Patients
    path('patients/', views.patients_list, name='patients_list'),
    path('patients/add/', views.add_patient, name='add_patient'),
    path('patients/<int:patient_id>/', views.patient_detail, name='patient_detail'),
    path('patients/<int:patient_id>/edit/', views.edit_patient, name='edit_patient'),
    path('patients/<int:patient_id>/delete/', views.delete_patient, name='delete_patient'),
    
    # Appointments
    path('appointments/', views.appointments_list, name='appointments_list'),
    path('appointments/add/', views.add_appointment, name='add_appointment'),
    path('appointments/<int:appointment_id>/edit/', views.edit_appointment, name='edit_appointment'),
    path('appointments/<int:appointment_id>/cancel/', views.cancel_appointment, name='cancel_appointment'),
    path('appointment/<int:pk>/status/<str:status>/', views.update_appointment_status, name='update_appointment_status'),
    path('appointment/<int:pk>/', views.appointment_detail, name='appointment_detail'),

    # Calendar
    path('calendar/', views.calendar_view, name='calendar'),
    
    # Consultations
    path('consultations/', views.consultations_list, name='consultations_list'),
    path('consultations/add/', views.add_consultation, name='add_consultation'),
    path('consultations/<int:consultation_id>/edit/', views.edit_consultation, name='edit_consultation'),
    path('consultations/<int:consultation_id>/', views.consultation_detail, name='consultation_detail'),
    
    # Prescriptions
    path('prescriptions/', views.prescription_list, name='prescription_list'),
    path('prescriptions/create/', views.create_prescription, name='create_prescription'),
    path('prescriptions/<int:prescription_id>/view/', views.prescription_view, name='prescription_view'),
    path('prescriptions/<int:prescription_id>/delete/', views.prescription_delete, name='prescription_delete'),
path('prescriptions/<int:prescription_id>/download/', views.prescription_download, name='prescription_download'),
# path('prescriptions/details/', views.prescription_details, name='prescription_details'),
    path('prescriptions/patient/<int:patient_id>/', views.patient_prescriptions, name='patient_prescriptions'),
    
    #Settings
     path('settings/', views.settings_view, name='settings'),
    path('settings/update-profile/', views.update_profile, name='update_profile'),
    path('settings/change-password/', views.change_password, name='change_password'),
    path('settings/update-notifications/', views.update_notifications, name='update_notifications'),
    path('settings/update-preferences/', views.update_preferences, name='update_preferences'),
    path('settings/delete-account/', views.delete_account, name='delete_account'),

]