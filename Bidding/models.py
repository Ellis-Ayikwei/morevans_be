from django.db import models

from Driver.models import Driver
from Request.models import Request

class Bid(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
        ('withdrawn', 'Withdrawn'),
    ]

    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='bids')
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    proposed_pickup_time = models.DateTimeField()
    estimated_completion_time = models.DateTimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    notes = models.TextField(blank=True)
    counter_offer = models.BooleanField(default=False)

    def __str__(self):
        return f"Bid by {self.driver.user.username} for {self.amount}" 

    class Meta:
        ordering = ['-created_at']
