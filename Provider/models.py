from django.db import models
from django.db import models
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point

from Basemodel.models import Basemodel
from Services.models import ServiceCategory



class ServiceArea(models.Model):
    """Define service areas with pricing multipliers"""
    name = models.CharField(max_length=100)
    postcodes = models.JSONField()  # List of postcodes
    price_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)
    is_active = models.BooleanField(default=True)
    special_requirements = models.TextField(blank=True)
    restricted_hours = models.JSONField(null=True)  # Time restrictions




from django.db import models
from django.contrib.auth import get_user_model


from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.gis.db import models as gis_models
from encrypted_fields import fields





class ServiceProvider(Basemodel):
    # --- Core Identity ---
    user = models.OneToOneField(
        'User.User',
        on_delete=models.CASCADE,
        related_name='service_provider'
    )

    # --- Business Details ---
    BUSINESS_TYPES = [
        ('limited', 'Limited Company'),
        ('sole_trader', 'Sole Trader'),
        ('partnership', 'Partnership'),
    ]
    
    business_type = models.CharField(max_length=20, choices=BUSINESS_TYPES)
    company_name = models.CharField(max_length=200)
    company_reg_number = models.CharField(max_length=50, blank=True)
    vat_registered = models.BooleanField(default=False)
    vat_number = models.CharField(max_length=20, blank=True)
    description = models.TextField(max_length=2000, blank=True)

    # --- Service Offerings ---
    # SERVICE_CATEGORIES = [
    #     ('furniture', 'Furniture & Appliances'),
    #     ('removals', 'Home Removals'),
    #     ('specialist', 'Specialist & Antiques'),
    #     ('vehicles', 'Cars & Vehicles'),
    #     # ... add all categories from account details
    # ]
    
    
    service_categories = models.ManyToManyField(
        ServiceCategory,
        related_name='providers',
        verbose_name='Service Categories'
    )
    
    specialization_categories = models.ManyToManyField(
        ServiceCategory,
        related_name='specializing_providers',
        verbose_name='Specializations',
        limit_choices_to={'is_specialization': True},  # Add field to ServiceCategory if needed
        blank=True,
        help_text="Select categories that you specialize in"
    )
    
    service_image = models.ImageField(upload_to='service_images/', null=True, blank=True)
    service_location = gis_models.PointField(srid=4326, null=True, blank=True)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    accepts_instant_bookings = models.BooleanField(default=True)

    # --- Geographic Coverage ---
    service_areas = gis_models.MultiPolygonField()
    service_radius = models.PositiveIntegerField(help_text="Max service radius in km")
    postcode_blacklist = models.JSONField(default=list, blank=True)
    Vehicle = models.OneToOneField('ProviderVehicle', on_delete=models.SET_NULL, null=True, blank=True)
    
    # --- Insurance & Certifications ---
    goods_in_transit_insurance = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    cmr_insurance = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    insurance_documents = models.ManyToManyField('Document', related_name='insurance_providers')
    certifications = models.ManyToManyField('Certification', blank=True)
    trade_associations = models.JSONField(default=list)

    # --- Financial Details ---
    bank_account = fields.EncryptedJSONField(null=True)  # {name, number, sort_code}
    payment_methods = models.JSONField(default=list)  # ['cash', 'bank_transfer', ...]
    stripe_connect_id = models.CharField(max_length=100, blank=True)
    tax_identification_number = fields.EncryptedCharField(max_length=50, blank=True)

    # --- Operational Preferences ---
    availability_schedule = models.JSONField(default=dict)
    preferred_working_hours = models.JSONField(default=dict)
    minimum_job_value = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    maximum_job_distance = models.PositiveIntegerField(null=True)  # km

    # --- Ratings & Performance ---
    provider_rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.0)
    success_rate = models.DecimalField(max_digits=5, decimal_places=2, default=100.0)
    total_completed = models.PositiveIntegerField(default=0)
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # --- Compliance & Verification ---
    background_check_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected')
        ],
        default='pending'
    )
    documents_verified = models.BooleanField(default=False)
    verification_status = models.CharField(
        max_length=20,
        choices=[
            ('unverified', 'Unverified'),
            ('verified', 'Verified'),
            ('premium', 'Premium Verified')
        ],
        default='unverified'
    )

    # --- Communication Preferences ---
    notification_preferences = models.JSONField(default=dict)
    marketing_opt_in = models.BooleanField(default=True)
    allow_customer_invites = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Service Provider"
        verbose_name_plural = "Service Providers"

    def __str__(self):
        return f"{self.company_name} ({self.get_vehicle_type_display()})"

    @property
    def full_address(self):
        return f"{self.address_line1}, {self.city}, {self.postcode}"

    def get_service_area_names(self):
        return [area.name for area in self.service_areas.all()]

class Document(models.Model):
    provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=50)
    file = models.FileField(upload_to='provider_documents/')
    issue_date = models.DateField()
    expiry_date = models.DateField(null=True)
    verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.document_type} - {self.provider.company_name}"

class Certification(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    required_for_categories = models.JSONField(default=list)

    def __str__(self):
        return self.name
    
    


class ProviderVehicle(models.Model):
    
    # --- Vehicle Information ---
    VEHICLE_TYPES = [
        ('van', 'Van'),
        ('truck', 'Truck'),
        ('cargo bike', 'Cargo Bike'),
        ('special', 'Specialized Vehicle'),
        ('heavy', 'Heavy Haulage'),
        ('urban', 'Urban Delivery'),
        ('cold', 'Cold Chain'),
    ]
    
    FUEL_TYPES =[
        ('diesel', 'Diesel'),
        ('gas', 'Gas'),
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid'),
        ('lpg', 'LPG'),
        ('cng', 'CNG'),
    ]
    
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES)
    vehicle_registration = models.CharField(max_length=20)
    description = models.TextField()
    vehicle_make_model = models.CharField(max_length=100)
    vehicle_year = models.PositiveIntegerField()
    max_load_capacity = models.DecimalField(max_digits=8, decimal_places=2)  # kg
    pallet_capacity = models.PositiveIntegerField(null=True)
    fuel_type = models.CharField(
        max_length=20,
        choices=FUEL_TYPES,
        default=FUEL_TYPES[0][0]
    )
    
    provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.vehicle_make_model} - {self.vehicle_registration}"