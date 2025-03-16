from unittest.mock import Base
from django.db import models
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point


from django.db import models
from Basemodel.models import Basemodel
from User.models import User
from encrypted_fields import fields
from Provider.models import ServiceArea

class Driver(Basemodel):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20)
    location = gis_models.PointField(srid=4326, null=True, blank=True)
    
    
    def __str__(self):
        return self.name


    class Meta:
        managed=True
        verbose_name = "Driver"
        verbose_name_plural = "Drivers"
        db_table = "driver"
    

class DriverLocation(Basemodel):
    driver = models.ForeignKey('Driver', on_delete=models.CASCADE)
    location = gis_models.PointField(geography=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Additional tracking metadata
    speed = models.FloatField(null=True)
    heading = models.FloatField(null=True)
    accuracy = models.FloatField(null=True)
    
    class Meta:
        get_latest_by = 'timestamp'
        ordering = ['-timestamp']


class DriverAvailability(Basemodel):
    """Detailed driver availability schedule"""
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='availability_slots')
    date = models.DateField()
    time_slots = models.JSONField()  # Available time slots
    service_areas = models.ManyToManyField(ServiceArea)
    max_jobs = models.IntegerField(default=1)
    notes = models.TextField(blank=True)


class ServiceArea(Basemodel):
    """Define service areas with pricing multipliers"""
    name = models.CharField(max_length=100)
    postcodes = models.JSONField()  # List of postcodes
    price_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)
    is_active = models.BooleanField(default=True)
    special_requirements = models.TextField(blank=True)
    restricted_hours = models.JSONField(null=True)  # Time restrictions