from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from datetime import datetime, timedelta
from django.core.exceptions import ValidationError
from django.db.models import Case, When, Value, IntegerField
from django.utils.timezone import now

from numpy import save
from .models import Doctor, Patient, Appointment, Consultation
from .forms import (DoctorRegistrationForm, DoctorLoginForm, PatientForm, 
AppointmentForm, ConsultationForm)

from .models import Prescription, Patient
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from datetime import datetime, timedelta
from django.utils import timezone
import json
from .models import Doctor, Patient, Prescription, Medicine

# PDF Generation imports
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO

# Authentication Views
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = DoctorLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            try:
                user = User.objects.get(email=email)
                user = authenticate(request, username=user.username, password=password)
                
                if user is not None:
                    login(request, user)
                    messages.success(request, f'Welcome back, Dr. {user.first_name}!')
                    return redirect('dashboard')
                else:
                    messages.error(request, 'Invalid email or password.')
            except User.DoesNotExist:
                messages.error(request, 'User not found.')
        else:
            messages.error(request, 'Please fill in all fields correctly.')
    else:
        form = DoctorLoginForm()
    
    return render(request, 'login.html', {'form': form})

def home_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')

    
def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    
    if request.method == 'POST':
        form = DoctorRegistrationForm(request.POST)
        if form.is_valid():
            try:
                # Create User
                user = User.objects.create_user(
                    username=form.cleaned_data['email'].split('@')[0],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                )
                
                # Create Doctor
                doctor = Doctor.objects.create(
                    user=user,
                    license_number=form.cleaned_data['license_number'],
                    specialty=form.cleaned_data['specialty'],
                    phone=form.cleaned_data['phone'],
                )
                
                messages.success(request, 'Account created successfully! Please log in.')
                return redirect('login')
            except Exception as e:
                messages.error(request, f'Error creating account: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = DoctorRegistrationForm()
    
    return render(request, 'signup.html', {'form': form})

def logout_view(request):
    user_name = request.user.first_name if request.user.first_name else request.user.username
    logout(request)
    messages.success(request, f'Goodbye, Dr. {user_name}! You have been logged out successfully.')
    return redirect('login')

# Landing Page
def landing_page(request):
    return render(request, 'landingPage.html')


# Dashboard View
@login_required(login_url='login')
def dashboard(request):
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        return redirect('login')
    
    # Get statistics
    total_patients = doctor.patients.count()
    total_appointments = doctor.appointments.count()
    total_consultations = doctor.consultations.count()
    pending_follow_ups = doctor.patients.filter(status='pending').count()
    
    # Get today's appointments
    today = datetime.now().date()
    todays_appointments = doctor.appointments.filter(
        scheduled_date=today,
        status='scheduled'
    ).select_related('patient')[:4]
    
    # Get recent patients
    recent_patients = doctor.patients.all()[:5]
    
    # Get appointment stats
    appointments_today = doctor.appointments.filter(
        scheduled_date=today
    ).count()
    
    context = {
        'total_patients': total_patients,
        'appointments_today': appointments_today,
        'total_consultations': total_consultations,
        'pending_follow_ups': pending_follow_ups,
        'todays_appointments': todays_appointments,
        'recent_patients': recent_patients,
        'doctor': doctor,
    }
    
    return render(request, 'dashboard.html', context)


# Patient Views
@login_required(login_url='login')
def patients_list(request):
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        return redirect('login')
    
    patients = doctor.patients.all()
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        patients = patients.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        patients = patients.filter(status=status_filter)
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(patients, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'patients': page_obj.object_list,
        'doctor': doctor,
        'search_query': search_query,
        'status_filter': status_filter,
    }
    
    return render(request, 'Patients/patients.html', context)


@login_required(login_url='login')
def add_patient(request):
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        return redirect('login')
    
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            patient.doctor = doctor
            patient.save()
            messages.success(request, 'Patient added successfully!')
            return redirect('patients_list')
    else:
        form = PatientForm()
    
    context = {
        'form': form,
        'doctor': doctor,
        'page_title': 'Add New Patient',
    }
    
    return render(request, 'Patients/add_patient.html', context)


@login_required(login_url='login')
def edit_patient(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    doctor = Doctor.objects.get(user=request.user)
    
    if patient.doctor != doctor:
        return redirect('patients_list')
    
    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, 'Patient updated successfully!')
            return redirect('patients_list')
    else:
        form = PatientForm(instance=patient)
    
    context = {
        'form': form,
        'patient': patient,
        'doctor': doctor,
        'page_title': f'Edit {patient.first_name} {patient.last_name}',
    }
    
    return render(request, 'Patients/add_patient.html', context)


@login_required(login_url='login')
def patient_detail(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    doctor = Doctor.objects.get(user=request.user)
    
    if patient.doctor != doctor:
        return redirect('patients_list')
    
    appointments = patient.appointments.all().order_by('-scheduled_date')
    consultations = patient.consultations.all().order_by('-created_at')
    
    context = {
        'patient': patient,
        'doctor': doctor,
        'appointments': appointments,
        'consultations': consultations,
    }
    
    return render(request, 'Patients/patient_detail.html', context)


@login_required(login_url='login')
def delete_patient(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    doctor = Doctor.objects.get(user=request.user)
    
    if patient.doctor != doctor:
        return redirect('patients_list')
    
    if request.method == 'POST':
        patient.delete()
        messages.success(request, 'Patient deleted successfully!')
        return redirect('patients_list')
    
    context = {
        'patient': patient,
        'doctor': doctor,
    }
    
    return render(request, 'delete_patient.html', context)


# Appointment Views
@login_required(login_url='login')
def appointments_list(request):
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        return redirect('login')
        
    today = now().date()

    appointments = doctor.appointments.all().select_related('patient').annotate(
        # 1️⃣ Status priority
        status_priority=Case(
            When(status='scheduled', then=Value(0)),
            When(status='completed', then=Value(1)),
            When(status='cancelled', then=Value(2)),
            default=Value(3),
            output_field=IntegerField(),
        ),
        # 2️⃣ Past vs future
        is_past=Case(
            When(scheduled_date__lt=today, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by(
        'status_priority',   # scheduled → completed → cancelled
        'is_past',           # future first
        'scheduled_date',    # closest date
        'scheduled_time'     # closest time
    )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    
    # Filter by date range
    date_filter = request.GET.get('date', '')
    today = datetime.now().date()
    
    if date_filter == 'today':
        appointments = appointments.filter(scheduled_date=today)
    elif date_filter == 'tomorrow':
        tomorrow = today + timedelta(days=1)
        appointments = appointments.filter(scheduled_date=tomorrow)
    elif date_filter == 'week':
        week_end = today + timedelta(days=7)
        appointments = appointments.filter(scheduled_date__range=[today, week_end])
    elif date_filter == 'month':
        month_end = today + timedelta(days=30)
        appointments = appointments.filter(scheduled_date__range=[today, month_end])
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        appointments = appointments.filter(
            Q(patient__first_name__icontains=search_query) |
            Q(patient__last_name__icontains=search_query)
        )
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(appointments, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'appointments': page_obj.object_list,
        'doctor': doctor,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'search_query': search_query,
    }
    
    return render(request, 'Appointments/appointments.html', context)

def update_appointment_status(request, pk, status):
    appointment = get_object_or_404(Appointment, pk=pk)

    valid_statuses = ['scheduled', 'completed', 'cancelled', 'no-show']
    if status in valid_statuses:
        appointment.status = status
        appointment.save()
        messages.success(request, "Appointment status updated successfully.")
    else:
        messages.error(request, "Invalid status.")

    return redirect('appointments_list')


@login_required(login_url='login')
def add_appointment(request):
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        return redirect('login')
    
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            try:
                appointment = form.save(commit=False)
                appointment.doctor = doctor  # Set doctor first
                
                # Check if patient belongs to this doctor
                if appointment.patient.doctor != doctor:
                    messages.error(request, 'You can only schedule appointments for your own patients.')
                    form.fields['patient'].queryset = doctor.patients.all()
                    return render(request, 'Appointments/add_appointment.html', {'form': form, 'doctor': doctor})
                
                # Call custom validation method
                appointment.validate_appointment_overlap()
                appointment.save()
                messages.success(request, f'Appointment with {appointment.patient.first_name} {appointment.patient.last_name} scheduled successfully!')
                return redirect('appointments_list')
            except ValidationError as e:
                if isinstance(e.message, list):
                    for msg in e.message:
                        messages.error(request, str(msg))
                else:
                    messages.error(request, str(e.message))
                form.fields['patient'].queryset = doctor.patients.all()
                return render(request, 'Appointments/add_appointment.html', {'form': form, 'doctor': doctor})
            except Exception as e:
                messages.error(request, f'Error scheduling appointment: {str(e)}')
                form.fields['patient'].queryset = doctor.patients.all()
                return render(request, 'Appointments/add_appointment.html', {'form': form, 'doctor': doctor})
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = AppointmentForm()
        form.fields['patient'].queryset = doctor.patients.all()
    
    context = {
        'form': form,
        'doctor': doctor,
        'page_title': 'Schedule New Appointment',
    }
    
    return render(request, 'Appointments/add_appointment.html', context)

def appointment_detail(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    return render(request, 'Appointments/appointment_detail.html', {'appointment': appointment})

@login_required(login_url='login')
def edit_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    doctor = Doctor.objects.get(user=request.user)
    
    if appointment.doctor != doctor:
        messages.error(request, 'You can only edit your own appointments.')
        return redirect('appointments_list')
    
    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=appointment)
        if form.is_valid():
            try:
                updated_appointment = form.save(commit=False)
                updated_appointment.doctor = doctor
                
                if updated_appointment.patient.doctor != doctor:
                    messages.error(request, 'You can only schedule appointments for your own patients.')
                    form.fields['patient'].queryset = doctor.patients.all()
                    return render(request, 'Appointments/add_appointment.html', {'form': form, 'appointment': appointment, 'doctor': doctor})
                
                # Call custom validation method
                updated_appointment.validate_appointment_overlap()
                updated_appointment.save()
                messages.success(request, 'Appointment updated successfully!')
                return redirect('appointments_list')
            except ValidationError as e:
                if isinstance(e.message, list):
                    for msg in e.message:
                        messages.error(request, str(msg))
                else:
                    messages.error(request, str(e.message))
                form.fields['patient'].queryset = doctor.patients.all()
                return render(request, 'Appointments/add_appointment.html', {'form': form, 'appointment': appointment, 'doctor': doctor})
            except Exception as e:
                messages.error(request, f'Error updating appointment: {str(e)}')
                form.fields['patient'].queryset = doctor.patients.all()
                return render(request, 'Appointments/add_appointment.html', {'form': form, 'appointment': appointment, 'doctor': doctor})
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = AppointmentForm(instance=appointment)
        form.fields['patient'].queryset = doctor.patients.all()
    context = {
        'form': form,
        'appointment': appointment,
        'doctor': doctor,
        'page_title': 'Edit Appointment',
    }
    
    return render(request, 'Appointments/add_appointment.html', context)

# @login_required(login_url='login')
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    doctor = Doctor.objects.get(user=request.user)
    
    if appointment.doctor != doctor:
        messages.error(request, 'You can only cancel your own appointments.')
        return redirect('appointments_list')
    
    try:
        appointment.status = 'cancelled'
        appointment.save()
        messages.success(request, f'Appointment with {appointment.patient.first_name} {appointment.patient.last_name} has been cancelled.')
    except Exception as e:
        messages.error(request, f'Error cancelling appointment: {str(e)}')
    
    return redirect('appointments_list')

# Calendar View
@login_required(login_url='login')
def calendar_view(request):
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        return redirect('login')
    
    year = request.GET.get('year', datetime.now().year)
    month = request.GET.get('month', datetime.now().month)
    
    from calendar import monthcalendar, month_name
    from datetime import date
    
    year = int(year)
    month = int(month)
    
    cal = monthcalendar(year, month)
    
    # Create a dictionary for easier access
    appointments_dict = {}
    for day in range(1, 32):
        try:
            date_obj = date(year, month, day)
            appointments = doctor.appointments.filter(
                scheduled_date=date_obj,
                status__in=['scheduled', 'completed']  # Only show scheduled and completed
            ).select_related('patient').order_by('scheduled_time')
            if appointments.exists():
                appointments_dict[day] = list(appointments)
        except ValueError:
            break
    
    # Get today's appointments
    today = datetime.now().date()
    today_appointments = doctor.appointments.filter(
        scheduled_date=today,
        status__in=['scheduled', 'completed']
    ).select_related('patient').order_by('scheduled_time')
    
    context = {
        'doctor': doctor,
        'year': year,
        'month': month,
        'month_name': month_name[month],
        'calendar': cal,
        'appointments_dict': appointments_dict,
        'today': today,
        'today_appointments': list(today_appointments),
    }
    
    return render(request, 'Appointments/calendar.html', context)

# Consultation Views
@login_required(login_url='login')
def consultations_list(request):
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        return redirect('login')
    
    consultations = doctor.consultations.all().select_related('patient', 'appointment')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        consultations = consultations.filter(status=status_filter)
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        consultations = consultations.filter(
            Q(patient__first_name__icontains=search_query) |
            Q(patient__last_name__icontains=search_query)
        )
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(consultations, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'consultations': page_obj.object_list,
        'doctor': doctor,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    
    return render(request, 'Consultations/consultations.html', context)


@login_required(login_url='login')
def add_consultation(request):
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        return redirect('login')
    
    if request.method == 'POST':
        form = ConsultationForm(request.POST)
        if form.is_valid():
            consultation = form.save(commit=False)
            consultation.doctor = doctor
            consultation.patient = consultation.appointment.patient
            consultation.save()
            messages.success(request, 'Consultation added successfully!')
            return redirect('consultations_list')
    else:
        form = ConsultationForm()
        # Limit appointments to doctor's appointments
        form.fields['appointment'].queryset = doctor.appointments.filter(
            status='scheduled'
        ).select_related('patient')
    
    context = {
        'form': form,
        'doctor': doctor,
        'page_title': 'Add Consultation',
    }
    
    return render(request, 'Consultations/add_consultation.html', context)


@login_required(login_url='login')
def edit_consultation(request, consultation_id):
    consultation = get_object_or_404(Consultation, id=consultation_id)
    doctor = Doctor.objects.get(user=request.user)
    
    if consultation.doctor != doctor:
        return redirect('consultations_list')
    
    if request.method == 'POST':
        form = ConsultationForm(request.POST, instance=consultation)
        if form.is_valid():
            form.save()
            messages.success(request, 'Consultation updated successfully!')
            return redirect('consultations_list')
    else:
        form = ConsultationForm(instance=consultation)
    
    context = {
        'form': form,
        'consultation': consultation,
        'doctor': doctor,
        'page_title': 'Edit Consultation',
    }
    
    return render(request, 'Consultations/add_consultation.html', context)


@login_required(login_url='login')
def consultation_detail(request, consultation_id):
    
    
    consultation = get_object_or_404(Consultation, id=consultation_id)
    doctor = Doctor.objects.get(user=request.user)
    
    if consultation.doctor != doctor:
        return redirect('consultations_list')
    
    context = {
        'consultation': consultation,
        'doctor': doctor,
    }
    
    return render(request, 'Consultations/consultation_detail.html', context)


# ============================================================
# PRESCRIPTION VIEWS
# ============================================================

@login_required(login_url='login')
def create_prescription(request):
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        return redirect('login')

    patients = doctor.patients.all()

    if request.method == 'POST':
        patient_id = request.POST.get('patient')
        prescription_date = request.POST.get('prescription_date')
        instructions = request.POST.get('instructions', '')
        medicines_data = request.POST.get('medicines_data', '[]')

        try:
            patient = Patient.objects.get(id=patient_id, doctor=doctor)
            
            # Create prescription
            prescription = Prescription.objects.create(
                doctor=doctor,
                patient=patient,
                prescription_date=prescription_date,
                notes=instructions
            )

            # Parse and create medicines
            medicines = json.loads(medicines_data)
            for med in medicines:
                Medicine.objects.create(
                    prescription=prescription,
                    name=med.get('name'),
                    dosage=med.get('dosage'),
                    frequency=med.get('frequency'),
                    duration=med.get('duration')
                )

            return JsonResponse({
                'success': True,
                'message': 'Prescription created successfully!',
                'prescription_id': prescription.id
            })

        except Patient.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Patient not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)

    context = {
        'patients': patients,
        'doctor': doctor
    }
    return render(request, 'Prescriptions/create_prescription.html', context)


@login_required(login_url='login')
def prescription_list(request):
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        return redirect('login')

    # Get all prescriptions for this doctor
    prescriptions = doctor.prescriptions.select_related('patient').prefetch_related('medicines').order_by('-created_at')

    # Get filter parameters
    search_query = request.GET.get('search', '').strip()
    patient_filter = request.GET.get('patient', '')
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')

    # Apply search filter
    if search_query:
        prescriptions = prescriptions.filter(
            Q(patient__first_name__icontains=search_query) |
            Q(patient__last_name__icontains=search_query) |
            Q(patient__email__icontains=search_query)
        )

    # Apply patient filter
    if patient_filter:
        prescriptions = prescriptions.filter(patient_id=patient_filter)

    # Apply date range filters
    if from_date:
        prescriptions = prescriptions.filter(created_at__gte=from_date)
    
    if to_date:
        # Add one day to include the entire end date
        to_date_obj = datetime.strptime(to_date, '%Y-%m-%d')
        to_date_obj = to_date_obj + timedelta(days=1)
        prescriptions = prescriptions.filter(created_at__lt=to_date_obj)

    # Calculate statistics
    total_prescriptions = doctor.prescriptions.count()
    
    today = timezone.now().date()
    today_prescriptions = doctor.prescriptions.filter(
        created_at__date=today
    ).count()
    
    week_start = today - timedelta(days=today.weekday())
    week_prescriptions = doctor.prescriptions.filter(
        created_at__date__gte=week_start
    ).count()
    
    unique_patients = doctor.prescriptions.values('patient').distinct().count()

    # Get all patients for filter dropdown
    all_patients = doctor.patients.all().order_by('first_name', 'last_name')

    # Pagination
    paginator = Paginator(prescriptions, 10)  # 10 prescriptions per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'prescriptions': page_obj,
        'all_patients': all_patients,
        'total_prescriptions': total_prescriptions,
        'today_prescriptions': today_prescriptions,
        'week_prescriptions': week_prescriptions,
        'unique_patients': unique_patients,
        'doctor': doctor,
    }

    return render(request, 'Prescriptions/prescription_list.html', context)


@login_required(login_url='login')
def patient_prescriptions(request, patient_id):
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        return redirect('login')
        
    patient = get_object_or_404(Patient, id=patient_id, doctor=doctor)
    prescriptions = patient.prescriptions.prefetch_related('medicines').order_by('-created_at')

    # Pagination
    paginator = Paginator(prescriptions, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'patient': patient,
        'prescriptions': page_obj,
        'doctor': doctor,
    }

    return render(request, 'Prescriptions/patient_prescriptions.html', context)


@login_required(login_url='login')
def prescription_view(request, prescription_id):
    """AJAX endpoint to get prescription details as JSON"""
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        return JsonResponse({'error': 'Doctor not found'}, status=404)

    prescription = get_object_or_404(
        Prescription.objects.select_related('patient', 'doctor').prefetch_related('medicines'),
        id=prescription_id,
        doctor=doctor
    )

    medicines_data = [
        {
            'name': med.name,
            'dosage': med.dosage,
            'frequency': med.frequency,
            'duration': med.duration
        }
        for med in prescription.medicines.all()
    ]

    data = {
        'id': prescription.id,
        'patient_name': f"{prescription.patient.first_name} {prescription.patient.last_name}",
        'patient_email': prescription.patient.email,
        'doctor_name': f"{prescription.doctor.user.first_name} {prescription.doctor.user.last_name}",
        'date': prescription.created_at.strftime('%B %d, %Y'),
        'notes': prescription.notes or '',
        'medicines': medicines_data
    }

    return JsonResponse(data)


@login_required(login_url='login')
def prescription_delete(request, prescription_id):
    """AJAX endpoint to delete a prescription"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Doctor not found'}, status=404)

    prescription = get_object_or_404(Prescription, id=prescription_id, doctor=doctor)
    
    try:
        prescription.delete()
        return JsonResponse({
            'success': True,
            'message': 'Prescription deleted successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting prescription: {str(e)}'
        }, status=500)


@login_required(login_url='login')
def prescription_download(request, prescription_id):
    """
    Generate and download prescription as PDF using ReportLab
    """
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        return HttpResponse('Unauthorized', status=401)
    
    # Get prescription or return 404
    prescription = get_object_or_404(
        Prescription.objects.select_related('patient', 'doctor').prefetch_related('medicines'),
        id=prescription_id,
        doctor=doctor
    )
    
    # Create PDF in memory
    buffer = BytesIO()
    
    # Create the PDF object using ReportLab
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Container for PDF elements
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1abc9c'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=6
    )
    
    # Add clinic/hospital header
    clinic_name = Paragraph("<b>MedCare Clinic</b>", title_style)
    elements.append(clinic_name)
    elements.append(Spacer(1, 0.2*inch))
    
    # Add prescription title
    prescription_title = Paragraph("MEDICAL PRESCRIPTION", heading_style)
    elements.append(prescription_title)
    elements.append(Spacer(1, 0.3*inch))
    
    # Patient and Doctor Information
    info_data = [
        ['Prescription ID:', f'#{prescription.id}', 'Date:', prescription.created_at.strftime('%B %d, %Y')],
        ['Patient Name:', f'{prescription.patient.first_name} {prescription.patient.last_name}', 
         'Patient ID:', f'#{prescription.patient.id}'],
        ['Email:', prescription.patient.email, 'Phone:', getattr(prescription.patient, 'phone', 'N/A')],
        ['Doctor:', f'Dr. {prescription.doctor.user.first_name} {prescription.doctor.user.last_name}', 
         'Specialty:', getattr(prescription.doctor, 'specialty', 'General Medicine')],
    ]
    
    info_table = Table(info_data, colWidths=[1.5*inch, 2.5*inch, 1.5*inch, 2*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#ecf0f1')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7'))
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 0.4*inch))
    
    # Medicines Section
    medicines_header = Paragraph("PRESCRIBED MEDICATIONS", heading_style)
    elements.append(medicines_header)
    elements.append(Spacer(1, 0.1*inch))
    
    # Get prescription medicines
    medicines = prescription.medicines.all()
    
    # Create medicines table
    medicine_data = [['#', 'Medicine Name', 'Dosage', 'Frequency', 'Duration']]
    
    for idx, med in enumerate(medicines, 1):
        medicine_data.append([
            str(idx),
            med.name,
            med.dosage,
            med.frequency,
            med.duration
        ])
    
    medicine_table = Table(medicine_data, colWidths=[0.5*inch, 2.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    medicine_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1abc9c')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        
        # Data rows
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#2c3e50')),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (1, 1), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 10),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
        
        # Alternating row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
    ]))
    
    elements.append(medicine_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Instructions/Notes
    if prescription.notes:
        notes_header = Paragraph("INSTRUCTIONS & NOTES", heading_style)
        elements.append(notes_header)
        elements.append(Spacer(1, 0.1*inch))
        
        notes_text = Paragraph(prescription.notes, normal_style)
        elements.append(notes_text)
        elements.append(Spacer(1, 0.3*inch))
    
    # Footer with signature
    elements.append(Spacer(1, 0.5*inch))
    
    signature_data = [
        ['', ''],
        ['_________________________', '_________________________'],
        ['Doctor Signature', 'Date & Stamp'],
    ]
    
    signature_table = Table(signature_data, colWidths=[3.5*inch, 3*inch])
    signature_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#7f8c8d')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    elements.append(signature_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Disclaimer
    disclaimer = Paragraph(
        "<i>This is a computer-generated prescription. "
        "Please consult your doctor before taking any medication.</i>",
        ParagraphStyle(
            'Disclaimer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#95a5a6'),
            alignment=TA_CENTER
        )
    )
    elements.append(disclaimer)
    
    # Build PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer and return it
    pdf = buffer.getvalue()
    buffer.close()
    
    # Create response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="prescription_{prescription.id}_{prescription.patient.last_name}.pdf"'
    response.write(pdf)
    
    return response


@login_required(login_url='login')
def settings_view(request):
    """
    Display settings page with all user preferences
    """
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        return redirect('login')
    
    # Get statistics for account section
    total_patients = doctor.patients.count()
    total_appointments = doctor.appointments.count()
    total_prescriptions = doctor.prescriptions.count()
    
    context = {
        'doctor': doctor,
        'total_patients': total_patients,
        'total_appointments': total_appointments,
        'total_prescriptions': total_prescriptions,
    }
    
    return render(request, 'settings.html', context)


@login_required(login_url='login')
def update_profile(request):
    """
    Update doctor profile information
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
    
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Doctor not found'}, status=404)
    
    try:
        # Update User model fields
        user = request.user
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        
        # Check if email is being changed and if it's already taken
        new_email = request.POST.get('email', '').strip()
        if new_email != user.email:
            if User.objects.filter(email=new_email).exclude(id=user.id).exists():
                return JsonResponse({
                    'success': False,
                    'message': 'This email is already in use by another account'
                })
            user.email = new_email
        
        user.save()
        
        # Update Doctor model fields
        doctor.phone = request.POST.get('phone', '').strip()
        doctor.license_number = request.POST.get('license_number', '').strip()
        doctor.specialty = request.POST.get('specialty', '').strip()
        doctor.bio = request.POST.get('bio', '').strip()
        
        # Handle profile picture upload if provided
        if 'profile_picture' in request.FILES:
            doctor.profile_picture = request.FILES['profile_picture']
        
        doctor.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Profile updated successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating profile: {str(e)}'
        }, status=500)


@login_required(login_url='login')
def change_password(request):
    """
    Change user password with validation
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
    
    current_password = request.POST.get('current_password', '')
    new_password = request.POST.get('new_password', '')
    confirm_password = request.POST.get('confirm_password', '')
    
    # Verify current password
    if not request.user.check_password(current_password):
        return JsonResponse({
            'success': False,
            'message': 'Current password is incorrect'
        })
    
    # Check if new passwords match
    if new_password != confirm_password:
        return JsonResponse({
            'success': False,
            'message': 'New passwords do not match'
        })
    
    # Validate new password
    try:
        validate_password(new_password, request.user)
    except DjangoValidationError as e:
        return JsonResponse({
            'success': False,
            'message': ', '.join(e.messages)
        })
    
    # Update password
    try:
        request.user.set_password(new_password)
        request.user.save()
        
        # Update session to prevent logout
        update_session_auth_hash(request, request.user)
        
        return JsonResponse({
            'success': True,
            'message': 'Password changed successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error changing password: {str(e)}'
        }, status=500)


@login_required(login_url='login')
def update_notifications(request):
    """
    Update notification preferences
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
    
    try:
        doctor = Doctor.objects.get(user=request.user)
        
        # Update notification preferences
        # Store as JSON in a preferences field or create a separate NotificationPreferences model
        preferences = {
            'email_notifications': 'email_notifications' in request.POST,
            'appointment_reminders': 'appointment_reminders' in request.POST,
            'new_patient_alerts': 'new_patient_alerts' in request.POST,
            'system_updates': 'system_updates' in request.POST,
        }
        
        # Save to doctor model (you may need to add a preferences field)
        # For now, we'll just return success
        # doctor.notification_preferences = json.dumps(preferences)
        # doctor.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Notification preferences updated successfully'
        })
        
    except Doctor.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Doctor not found'}, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating preferences: {str(e)}'
        }, status=500)


@login_required(login_url='login')
def update_preferences(request):
    """
    Update display and general preferences
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
    
    try:
        doctor = Doctor.objects.get(user=request.user)
        
        # Update display preferences
        preferences = {
            'language': request.POST.get('language', 'en'),
            'timezone': request.POST.get('timezone', 'UTC'),
            'date_format': request.POST.get('date_format', 'MM/DD/YYYY'),
            'time_format': request.POST.get('time_format', '12'),
            'dark_mode': 'dark_mode' in request.POST,
            'compact_view': 'compact_view' in request.POST,
        }
        
        # Save to doctor model (you may need to add a preferences field)
        # doctor.display_preferences = json.dumps(preferences)
        # doctor.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Display preferences updated successfully'
        })
        
    except Doctor.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Doctor not found'}, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating preferences: {str(e)}'
        }, status=500)


@login_required(login_url='login')
def delete_account(request):
    """
    Permanently delete user account and all associated data
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
    
    try:
        user = request.user
        doctor = Doctor.objects.get(user=user)
        
        # Delete all associated data
        # Patients, appointments, consultations, prescriptions will be deleted via CASCADE
        doctor.delete()
        user.delete()
        
        # Logout the user
        logout(request)
        
        return JsonResponse({
            'success': True,
            'message': 'Account deleted successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting account: {str(e)}'
        }, status=500)