from django.db import models
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from datetime import datetime
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta


class Doctor(models.Model):
    SPECIALTY_CHOICES = [
        ('cardiology', 'Cardiology'),
        ('dermatology', 'Dermatology'),
        ('orthopedics', 'Orthopedics'),
        ('neurology', 'Neurology'),
        ('pediatrics', 'Pediatrics'),
        ('psychiatry', 'Psychiatry'),
        ('general', 'General Practice'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    license_number = models.CharField(max_length=50, unique=True)
    specialty = models.CharField(max_length=20, choices=SPECIALTY_CHOICES)
    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$', message='Phone number must be between 9 and 15 digits.')
    phone = models.CharField(validators=[phone_regex], max_length=17)
    
    # Add these new fields
    address = models.TextField(default='')
    city = models.CharField(max_length=100, default='')
    email = models.EmailField(default='')
    
    profile_picture = models.ImageField(upload_to='doctor_profiles/', null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Dr. {self.user.first_name} {self.user.last_name}"

    class Meta:
        ordering = ['-created_at']


class Patient(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('pending', 'Pending'),
    ]

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='patients')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$', message='Phone number must be between 9 and 15 digits.')
    phone = models.CharField(validators=[phone_regex], max_length=17)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=10)
    emergency_contact = models.CharField(max_length=100)
    emergency_phone = models.CharField(max_length=17)
    medical_history = models.TextField(null=True, blank=True)
    allergies = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        ordering = ['-created_at']


class Appointment(models.Model):
    APPOINTMENT_TYPE_CHOICES = [
        ('checkup', 'Regular Checkup'),
        ('followup', 'Follow-up'),
        ('consultation', 'Consultation'),
        ('test', 'Test/Procedure'),
    ]

    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no-show', 'No Show'),
    ]

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='appointments')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    appointment_type = models.CharField(max_length=20, choices=APPOINTMENT_TYPE_CHOICES)
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField()
    duration = models.IntegerField(default=30, help_text="Duration in minutes")
    notes = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='scheduled')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient.first_name} - {self.appointment_type} on {self.scheduled_date}"
    
    def validate_appointment_overlap(self):
        """Validate that the appointment doesn't overlap with existing appointments"""
        from django.utils import timezone
        
        # Convert to datetime for easier calculation
        appointment_start = datetime.combine(self.scheduled_date, self.scheduled_time)
        appointment_end = appointment_start + timedelta(minutes=self.duration)
        
        # Check if appointment is in the past
        now = timezone.now()
        # Convert appointment_start to be timezone-aware for comparison
        from django.utils.timezone import make_aware
        appointment_start_aware = make_aware(appointment_start) if appointment_start.tzinfo is None else appointment_start
        
        if appointment_start_aware < now:
            raise ValidationError('Cannot schedule appointments in the past.')
        
        # Query overlapping appointments
        overlapping = Appointment.objects.filter(
            doctor=self.doctor,
            scheduled_date=self.scheduled_date,
            status__in=['scheduled', 'completed']  # Don't check cancelled appointments
        ).exclude(id=self.id)  # Exclude current appointment when editing
        
        for existing in overlapping:
            existing_start = datetime.combine(existing.scheduled_date, existing.scheduled_time)
            existing_end = existing_start + timedelta(minutes=existing.duration)
            
            # Check if there's any overlap
            if not (appointment_end <= existing_start or appointment_start >= existing_end):
                raise ValidationError(
                    f'This time slot is not available. There is already an appointment from '
                    f'{existing.scheduled_time.strftime("%H:%M")} to '
                    f'{existing_end.time().strftime("%H:%M")} on {existing.scheduled_date}.'
                )

    def save(self, *args, **kwargs):
        # self.validate_appointment_overlap()
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-scheduled_date', '-scheduled_time']


class Consultation(models.Model):
    STATUS_CHOICES = [
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('pending', 'Pending'),
    ]

    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='consultation')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='consultations')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='consultations')
    chief_complaint = models.TextField()
    diagnosis = models.TextField()
    treatment_plan = models.TextField()
    medications = models.TextField(null=True, blank=True)
    follow_up_notes = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Consultation - {self.patient.first_name} on {self.created_at.date()}"

    class Meta:
        ordering = ['-created_at']


class Prescription(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='prescriptions')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='prescriptions')
    prescription_date = models.DateField(default=timezone.now)
    notes = models.TextField(null=True, blank=True, help_text='Additional instructions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    bio = models.TextField(blank=True, null=True, help_text="Professional biography")
    notification_preferences = models.JSONField(default=dict, blank=True, null=True)
    display_preferences = models.JSONField(default=dict, blank=True, null=True)
    
    def __str__(self):
        return f"Prescription #{self.id} - {self.patient.first_name} {self.patient.last_name} ({self.prescription_date})"

    @property
    def medicine_count(self):
        """Return the count of medicines for this prescription"""
        return self.medicines.count()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['doctor', '-created_at']),
            models.Index(fields=['patient', '-created_at']),
        ]


class Medicine(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='medicines')
    name = models.CharField(max_length=200, help_text='Medicine name and strength')
    dosage = models.CharField(max_length=100, help_text='e.g., 500mg, 1 tablet')
    frequency = models.CharField(max_length=100, help_text='e.g., Twice daily, Every 8 hours')
    duration = models.CharField(max_length=100, help_text='e.g., 7 days, 2 weeks')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.dosage}"

    class Meta:
        ordering = ['created_at']