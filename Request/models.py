from datetime import timezone
import uuid
from django.db import models
from Driver.models import Driver
from Location.models import Location
from Notification.models import Notification
from Tracking.models import TrackingUpdate

from User.models import User
from django_fsm import FSMField, transition

class ItemCategory(models.Model):
    """Categories of items that can be transported"""
    name = models.CharField(max_length=100)
    requires_special_handling = models.BooleanField(default=False)
    restricted = models.BooleanField(default=False)
    insurance_required = models.BooleanField(default=False)
    price_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)
    special_instructions = models.TextField(blank=True)

class Request(models.Model):
    REQUEST_TYPE_CHOICES = [
        ('biddable', 'Biddable'),
        ('instant', 'Instant'),
        ('journey', 'Journey'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('bidding', 'Bidding in Progress'),
        ('accepted', 'Accepted'),
        ('in_transit', 'In Transit'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    PRIORITY_CHOICES = [
        ('normal', 'Normal'),
        ('express', 'Express'),
        ('same_day', 'Same Day'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True)
    request_type = models.CharField(max_length=10, choices=REQUEST_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    # status = FSMField(default='draft')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    
    # Locations
    pickup_locations = models.ManyToManyField(
        Location, 
        related_name='pickup_requests',
        through='PickupSchedule'
    )
    dropoff_locations = models.ManyToManyField(
        Location, 
        related_name='dropoff_requests',
        through='DropoffSchedule'
    )
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    preferred_pickup_date = models.DateField()
    preferred_pickup_time_window = models.JSONField()  # Store time window
    estimated_completion_time = models.DateTimeField(null=True)
    
    # Cargo Details
    items_description = models.TextField()
    total_weight = models.DecimalField(max_digits=8, decimal_places=2)  # in kg
    dimensions = models.JSONField()  # Store length, width, height
    requires_special_handling = models.BooleanField(default=False)
    special_instructions = models.TextField(blank=True)
    
    # Pricing
    base_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    price_factors = models.JSONField(null=True)  # Store factors affecting price
    
    # Additional Fields
    tracking_number = models.CharField(max_length=50, unique=True)
    insurance_required = models.BooleanField(default=False)
    insurance_value = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    payment_status = models.CharField(max_length=20, default='pending')
    cancellation_reason = models.TextField(blank=True)
    cancellation_time = models.DateTimeField(null=True)
    cancellation_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    route_optimization_data = models.JSONField(null=True)
    weather_conditions = models.JSONField(null=True)
    estimated_fuel_consumption = models.DecimalField(max_digits=6, decimal_places=2, null=True)
    carbon_footprint = models.DecimalField(max_digits=6, decimal_places=2, null=True)
    service_level = models.CharField(max_length=20, choices=[
        ('standard', 'Standard'),
        ('express', 'Express'),
        ('premium', 'Premium'),
    ])
    estimated_distance = models.DecimalField(max_digits=8, decimal_places=2)
    route_waypoints = models.JSONField(null=True)
    loading_time = models.DurationField(null=True)
    unloading_time = models.DurationField(null=True)
    # applied_promotions = models.ManyToManyField('Promotion')
    price_breakdown = models.JSONField(null=True)

    def generate_tracking_number(self):
        """Generate a unique tracking number for the request"""
        prefix = f"MOV{timezone.now().strftime('%Y%m%d')}"
        unique_id = str(uuid.uuid4().hex)[:6].upper()
        return f"{prefix}-{unique_id}"

    def calculate_base_price(self):
        """Calculate the base price based on distance, weight, and type"""
        # Implementation of pricing algorithm
        base_price = 0
        # Add distance factor
        # Add weight factor
        # Add priority factor
        # Add special handling factor
        return base_price

    def update_status(self, new_status):
        """Update request status and handle notifications"""
        old_status = self.status
        self.status = new_status
        self.save()

        # Create tracking update
        TrackingUpdate.objects.create(
            request=self,
            update_type='status',
            status_message=f"Status changed from {old_status} to {new_status}"
        )

        # Create notifications for relevant parties
        Notification.objects.create(
            user=self.user,
            notification_type='request_update',
            title='Request Status Update',
            message=f'Your request status has been updated to {new_status}',
            data={'request_id': self.id, 'status': new_status}
        )

        if self.driver:
            Notification.objects.create(
                user=self.driver.user,
                notification_type='request_update',
                title='Request Status Update',
                message=f'Request status has been updated to {new_status}',
                data={'request_id': self.id, 'status': new_status}
            )

    @transition(field=status, source='draft', target='pending')
    def submit(self):
        pass


    def __str__(self):
        return f"{self.user.username} - {self.request_type}"
    
    
class RequestItem(models.Model):
    """Individual items within a request"""
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='items')
    category = models.ForeignKey(ItemCategory, on_delete=models.PROTECT)
    quantity = models.IntegerField(default=1)
    weight = models.DecimalField(max_digits=8, decimal_places=2)
    dimensions = models.JSONField()
    special_instructions = models.TextField(blank=True)
    photos = models.JSONField(null=True)
    declared_value = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    
    
# request/models.py
class PickupSchedule(models.Model):
    request = models.ForeignKey(Request, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    scheduled_time = models.DateTimeField()

class DropoffSchedule(models.Model):
    request = models.ForeignKey(Request, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    scheduled_time = models.DateTimeField()