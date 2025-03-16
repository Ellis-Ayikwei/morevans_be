from django.db import models

class Location(models.Model):
    address = models.TextField()
    postcode = models.CharField(max_length=10)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    contact_name = models.CharField(max_length=100)
    contact_phone = models.CharField(max_length=15)
    special_instructions = models.TextField(blank=True)
