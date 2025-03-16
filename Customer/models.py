# customers/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from Basemodel.models import Basemodel
from encrypted_fields import fields
from phonenumber_field.modelfields import PhoneNumberField

User = get_user_model()

class Customer(Basemodel):
    COMMUNICATION_PREF = (
        ('email', _('Email')),
        ('sms', _('SMS')),
        ('none', _('No Notifications'))
    )
       

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='customer_profile'
    )
    phone_number = PhoneNumberField(blank=True)
    profile_image = models.ImageField(
        upload_to='customer_profiles/',
        blank=True,
        null=True
    )
    language = models.CharField(
        max_length=10,
        choices=[
            ('en', 'English'),
            ('fr', 'Français'),
            ('de', 'Deutsch'),
        ],
        default='en'
    )
    communication_preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Notification preferences settings")
    )
    marketing_opt_in = models.BooleanField(
        default=False,
        verbose_name=_("Marketing Communications")
    )
    loyalty_points = models.PositiveIntegerField(default=0)
    referral_code = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Customer")
        verbose_name_plural = _("Customers")

    def __str__(self):
        return f"{self.user.email}"

class Address(Basemodel):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='addresses'
    )
    address_type = models.CharField(
        max_length=20,
        choices=[
            ('billing', _('Billing Address')),
            ('shipping', _('Shipping Address')),
            ('both', _('Billing & Shipping'))
        ],
        default='both'
    )
    street_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    location = models.PointField(null=True, blank=True)

    class Meta:
        verbose_name = _("Address")
        verbose_name_plural = _("Addresses")
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f"{self.street_address}, {self.city}"

class PaymentMethod(Basemodel):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='payment_methods'
    )
    encrypted_card_number = fields.EncryptedCharField(max_length=255)
    card_brand = models.CharField(max_length=50)
    expiration_month = models.PositiveSmallIntegerField()
    expiration_year = models.PositiveSmallIntegerField()
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    stripe_payment_method_id = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Stripe payment method identifier")
    )

    class Meta:
        verbose_name = _("Payment Method")
        verbose_name_plural = _("Payment Methods")

    def __str__(self):
        return f"{self.card_brand} ending in {self.encrypted_card_number[-4:]}"

  