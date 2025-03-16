from django.db import models

class ServiceCategory(models.Model):
    slug = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=30, null=True)

    def __str__(self):
        return self.name