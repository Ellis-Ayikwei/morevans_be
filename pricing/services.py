from datetime import date, datetime, timedelta
import holidays
from rest_framework.response import Response
from rest_framework import status
import logging
from django.core.cache import cache
from django.db.models import Q
from .models import (
    PricingConfiguration,
    DistancePricing,
    WeightPricing,
    TimePricing,
    WeatherPricing,
    VehicleTypePricing,
    SpecialRequirementsPricing,
    ServiceLevelPricing,
    StaffRequiredPricing,
    PropertyTypePricing,
    InsurancePricing,
    LoadingTimePricing,
)
import uuid
from .defaults import (
    DEFAULT_PRICING_CONFIG,
    DEFAULT_DISTANCE_PRICING,
    DEFAULT_WEIGHT_PRICING,
    DEFAULT_TIME_PRICING,
    DEFAULT_WEATHER_PRICING,
    DEFAULT_VEHICLE_PRICING,
    DEFAULT_SPECIAL_REQUIREMENTS_PRICING,
    DEFAULT_SERVICE_LEVEL_PRICING,
    DEFAULT_STAFF_REQUIRED_PRICING,
    DEFAULT_PROPERTY_TYPE_PRICING,
    DEFAULT_INSURANCE_PRICING,
    DEFAULT_LOADING_TIME_PRICING,
)
from decimal import Decimal
import random
from types import SimpleNamespace

logger = logging.getLogger(__name__)


class PricingService:
    """Service class to handle pricing logic separated from the views"""

    CACHE_TIMEOUT = 3600  # 1 hour cache timeout
    CACHE_KEY_PREFIX = "pricing_"

    @staticmethod
    def get_cache_key(key):
        """Generate a cache key with prefix"""
        return f"{PricingService.CACHE_KEY_PREFIX}{key}"

    @staticmethod
    def get_active_configuration():
        """Return the DB config or fallback to an in-memory default."""
        config = PricingConfiguration.objects.filter(is_default=True).first()
        if not config:
            config = PricingConfiguration.objects.filter(is_active=True).first()

        if config:
            return config

        # build a fake config from our DEFAULT_… dict
        fake = SimpleNamespace(**DEFAULT_PRICING_CONFIG)
        # attach in-memory lists of mock factors
        fake.distance_factors = [DistancePricing(**DEFAULT_DISTANCE_PRICING)]
        fake.weight_factors = [WeightPricing(**DEFAULT_WEIGHT_PRICING)]
        fake.time_factors = [TimePricing(**DEFAULT_TIME_PRICING)]
        fake.weather_factors = [WeatherPricing(**DEFAULT_WEATHER_PRICING)]
        fake.vehicle_factors = [VehicleTypePricing(**DEFAULT_VEHICLE_PRICING)]
        fake.special_requirement_factors = [
            SpecialRequirementsPricing(**DEFAULT_SPECIAL_REQUIREMENTS_PRICING)
        ]
        fake.service_level_factors = [
            ServiceLevelPricing(**DEFAULT_SERVICE_LEVEL_PRICING)
        ]
        fake.staff_factors = [StaffRequiredPricing(**DEFAULT_STAFF_REQUIRED_PRICING)]
        fake.property_type_factors = [
            PropertyTypePricing(**DEFAULT_PROPERTY_TYPE_PRICING)
        ]
        fake.insurance_factors = [InsurancePricing(**DEFAULT_INSURANCE_PRICING)]
        fake.loading_time_factors = [LoadingTimePricing(**DEFAULT_LOADING_TIME_PRICING)]
        return fake

    @staticmethod
    def ensure_default_config_exists():
        """
        Ensures that at least one default pricing configuration exists in the database.
        If no configuration exists, creates a default one with standard pricing factors.
        """
        # Check if any pricing configuration exists
        if PricingConfiguration.objects.count() == 0:
            logger.info(
                "No pricing configuration found. Creating default configuration..."
            )

            try:
                # Create default configuration
                config = PricingConfiguration.objects.create(**DEFAULT_PRICING_CONFIG)
                logger.info(
                    f"Created default pricing configuration: {config.name} (ID: {config.id})"
                )

                # Create all default factors
                factors = {
                    "distance": DistancePricing.objects.create(
                        **DEFAULT_DISTANCE_PRICING
                    ),
                    "weight": WeightPricing.objects.create(**DEFAULT_WEIGHT_PRICING),
                    "time": TimePricing.objects.create(**DEFAULT_TIME_PRICING),
                    "weather": WeatherPricing.objects.create(**DEFAULT_WEATHER_PRICING),
                    "vehicle": VehicleTypePricing.objects.create(
                        **DEFAULT_VEHICLE_PRICING
                    ),
                    "special_req": SpecialRequirementsPricing.objects.create(
                        **DEFAULT_SPECIAL_REQUIREMENTS_PRICING
                    ),
                    "service": ServiceLevelPricing.objects.create(
                        **DEFAULT_SERVICE_LEVEL_PRICING
                    ),
                    "staff": StaffRequiredPricing.objects.create(
                        **DEFAULT_STAFF_REQUIRED_PRICING
                    ),
                    "property_type": PropertyTypePricing.objects.create(
                        **DEFAULT_PROPERTY_TYPE_PRICING
                    ),
                    "insurance": InsurancePricing.objects.create(
                        **DEFAULT_INSURANCE_PRICING
                    ),
                    "loading_time": LoadingTimePricing.objects.create(
                        **DEFAULT_LOADING_TIME_PRICING
                    ),
                }

                # Associate factors with configuration
                config.distance_factors.add(factors["distance"])
                config.weight_factors.add(factors["weight"])
                config.time_factors.add(factors["time"])
                config.weather_factors.add(factors["weather"])
                config.vehicle_factors.add(factors["vehicle"])
                config.special_requirement_factors.add(factors["special_req"])
                config.service_level_factors.add(factors["service"])
                config.staff_factors.add(factors["staff"])
                config.property_type_factors.add(factors["property_type"])
                config.insurance_factors.add(factors["insurance"])
                config.loading_time_factors.add(factors["loading_time"])

                # For backward compatibility with active_factors
                config.active_factors = {
                    "distance": [str(factors["distance"].id)],
                    "weight": [str(factors["weight"].id)],
                    "time": [str(factors["time"].id)],
                    "weather": [str(factors["weather"].id)],
                    "vehicle_type": [str(factors["vehicle"].id)],
                    "special_requirements": [str(factors["special_req"].id)],
                    "service_level": [str(factors["service"].id)],
                    "staff_required": [str(factors["staff"].id)],
                    "property_type": [str(factors["property_type"].id)],
                    "insurance": [str(factors["insurance"].id)],
                    "loading_time": [str(factors["loading_time"].id)],
                }
                config.save()

                # Clear cache
                cache.delete(PricingService.get_cache_key("active_config"))

                logger.info(
                    f"Associated {len(factors)} default pricing factors with the configuration"
                )
                return config
            except Exception as e:
                logger.error(f"Error creating default configuration: {str(e)}")
                raise

        return None

    @staticmethod
    def calculate_price_forecast(forecast_request):
        """
        Calculate prices for different dates and staff requirements.
        Returns a calendar-friendly format with staff prices for each day.
        """
        try:
            # Ensure default configuration exists
            PricingService.ensure_default_config_exists()

            # Get request data
            data = (
                forecast_request.data
                if hasattr(forecast_request, "data")
                else forecast_request
            )

            # Get active configuration
            active_config = PricingService.get_active_configuration()
            if not active_config:
                raise ValueError("No active pricing configuration found")

            # Use default base_price if missing
            base_price = float(
                active_config.base_price
                if active_config.base_price is not None
                else DEFAULT_PRICING_CONFIG["base_price"]
            )

            # Get date range
            start_date = data.get("start_date", date.today())
            end_date = data.get("end_date", start_date + timedelta(days=90))

            # Get basic pricing parameters with validation
            distance = float(data.get("distance", random.uniform(5, 50)))
            weight = float(data.get("weight", 0))
            service_level = data.get("service_level", "standard")
            property_type = data.get("property_type", "house")
            vehicle_type = data.get("vehicle_type", "van")

            # Validate parameters
            if distance < 0:
                raise ValueError("Distance cannot be negative")
            if weight < 0:
                raise ValueError("Weight cannot be negative")

            # Get configuration factors with caching
            factors = PricingService._get_pricing_factors(
                active_config, service_level, property_type, vehicle_type
            )

            # Initialize result structure
            monthly_calendar = {}
            uk_holidays = holidays.GB()

            # Generate pricing for each day in the range
            current_date = start_date
            while current_date <= end_date:
                month_key = current_date.strftime("%Y-%m")
                if month_key not in monthly_calendar:
                    monthly_calendar[month_key] = []

                # Calculate day's prices
                day_data = PricingService._calculate_day_prices(
                    current_date,
                    distance,
                    weight,
                    data,
                    factors,
                    active_config,
                    uk_holidays,
                    forecast_request,
                )
                monthly_calendar[month_key].append(day_data)
                current_date += timedelta(days=1)

            return Response(
                {
                    "pricing_configuration": active_config.name,
                    "base_parameters": {
                        "distance": distance,
                        "weight": weight,
                        "service_level": service_level,
                        "property_type": property_type,
                        "vehicle_type": vehicle_type,
                    },
                    "monthly_calendar": monthly_calendar,
                },
                status=status.HTTP_200_OK,
            )

        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error calculating prices: {str(e)}")
            return Response(
                {"error": "An error occurred while calculating prices"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @staticmethod
    def _get_pricing_factors(active_config, service_level, property_type, vehicle_type):
        """Get all pricing factors with caching"""
        cache_key = PricingService.get_cache_key(f"factors_{active_config.id}")
        factors = cache.get(cache_key)

        if not factors:
            factors = {
                "distance": active_config.distance_factors.filter(is_active=True),
                "weight": active_config.weight_factors.filter(is_active=True),
                "property": active_config.property_type_factors.filter(
                    is_active=True, property_type=property_type
                ),
                "service_level": active_config.service_level_factors.filter(
                    is_active=True, service_level=service_level
                ),
                "vehicle": active_config.vehicle_factors.filter(
                    is_active=True, vehicle_type=vehicle_type
                ),
                "time": active_config.time_factors.filter(is_active=True),
                "weather": active_config.weather_factors.filter(is_active=True),
                "insurance": active_config.insurance_factors.filter(is_active=True),
                "staff": active_config.staff_factors.filter(is_active=True),
            }
            cache.set(cache_key, factors, PricingService.CACHE_TIMEOUT)

        return factors

    @staticmethod
    def _calculate_day_prices(
        current_date,
        distance,
        weight,
        data,
        factors,
        active_config,
        uk_holidays,
        forecast_request,
    ):
        """Calculate prices for a specific day"""
        # Check if it's a weekend or holiday
        is_weekend = current_date.weekday() >= 5
        is_holiday = current_date in uk_holidays

        # Calculate base components
        base_price = float(active_config.base_price)
        distance_cost = PricingService._calculate_distance_cost(
            distance, factors["distance"]
        )
        weight_cost = PricingService._calculate_weight_cost(weight, factors["weight"])
        property_cost = PricingService._calculate_property_cost(
            data, factors["property"]
        )

        # Calculate vehicle cost
        vehicle_cost, vehicle_multiplier = PricingService._calculate_vehicle_cost(
            factors["vehicle"]
        )

        # Calculate insurance cost if applicable
        insurance_cost = PricingService._calculate_insurance_cost(
            data, factors["insurance"]
        )

        # Calculate multipliers
        service_multiplier = PricingService._calculate_service_multiplier(
            factors["service_level"]
        )
        time_multiplier = PricingService._calculate_time_multiplier(
            is_weekend, is_holiday, factors["time"]
        )
        weather_multiplier, weather_type = (
            PricingService._calculate_weather_multiplier()
        )

        # Calculate staff prices
        staff_prices = PricingService._calculate_staff_prices(
            factors["staff"],
            is_weekend,
            is_holiday,
            base_price,
            distance_cost,
            weight_cost,
            property_cost,
            vehicle_cost,
            insurance_cost,
            service_multiplier,
            time_multiplier,
            weather_multiplier,
            vehicle_multiplier,
            active_config,
        )

        # Prepare day data
        day_data = {
            "date": current_date.strftime("%Y-%m-%d"),
            "day": current_date.day,
            "is_weekend": is_weekend,
            "is_holiday": is_holiday,
            "holiday_name": uk_holidays.get(current_date) if is_holiday else None,
            "weather_type": weather_type,
            "staff_prices": staff_prices,
            "status": "available",
        }

        if hasattr(forecast_request, "request_id"):
            day_data["request_id"] = forecast_request.request_id

        return day_data

    @staticmethod
    def _calculate_distance_cost(distance, factors):
        """Calculate distance-based cost"""
        total_cost = 0
        for factor in factors:
            if distance <= factor.additional_distance_threshold:
                total_cost += factor.calculate_price(distance)
            else:
                base_distance_cost = factor.calculate_price(
                    factor.additional_distance_threshold
                )
                additional_distance = distance - factor.additional_distance_threshold
                additional_cost = (
                    additional_distance
                    * float(factor.base_rate_per_km)
                    * float(factor.additional_distance_multiplier)
                )
                total_cost += base_distance_cost + additional_cost
        return total_cost

    @staticmethod
    def _calculate_weight_cost(weight, factors):
        """Calculate weight-based cost"""
        total_cost = 0
        for factor in factors:
            base_cost = factor.calculate_price(weight)
            if weight > factor.heavy_item_threshold:
                total_cost += float(factor.heavy_item_surcharge)
            total_cost += base_cost
        return total_cost

    @staticmethod
    def _calculate_property_cost(data, factors):
        """Calculate property type cost"""
        total_cost = 0
        for factor in factors:
            total_cost += float(factor.base_rate)
            if data.get("number_of_rooms"):
                total_cost += float(factor.rate_per_room) * data["number_of_rooms"]
            if data.get("floor_number"):
                floor_cost = float(factor.floor_rate) * data["floor_number"]
                if data.get("has_elevator", False):
                    floor_cost *= float(factor.elevator_discount)
                total_cost += floor_cost
        return total_cost

    @staticmethod
    def _calculate_vehicle_cost(factors):
        """Calculate vehicle cost and multiplier"""
        for factor in factors:
            return float(factor.base_rate), float(factor.capacity_multiplier)
        return 0, 1.0

    @staticmethod
    def _calculate_insurance_cost(data, factors):
        """Calculate insurance cost"""
        if not data.get("insurance_required", False):
            return 0

        total_cost = 0
        for factor in factors:
            declared_value = float(data.get("declared_value", 0))
            value_based_cost = declared_value * (float(factor.value_percentage) / 100)
            base_cost = max(value_based_cost, float(factor.min_premium))

            if data.get("premium_coverage", False):
                base_cost *= float(factor.premium_coverage_multiplier)

            if data.get("high_value_items", False):
                high_value_surcharge = declared_value * (
                    float(factor.high_value_item_rate) / 100
                )
                base_cost += high_value_surcharge

            total_cost += base_cost
        return total_cost

    @staticmethod
    def _calculate_service_multiplier(factors):
        """Calculate service level multiplier"""
        for factor in factors:
            return float(factor.price_multiplier)
        return 1.0

    @staticmethod
    def _calculate_time_multiplier(is_weekend, is_holiday, factors):
        """Calculate time-based multiplier"""
        for factor in factors:
            if is_holiday:
                return float(factor.holiday_multiplier)
            elif is_weekend:
                return float(factor.weekend_multiplier)
        return 1.0

    @staticmethod
    def _calculate_weather_multiplier():
        """Calculate weather multiplier"""
        weather_rand = random.random()
        if weather_rand < 0.02:
            return 2.00, "extreme"
        elif weather_rand < 0.07:
            return 1.50, "snow"
        elif weather_rand < 0.17:
            return 1.20, "rain"
        return 1.0, "normal"

    @staticmethod
    def _calculate_staff_prices(
        staff_factors,
        is_weekend,
        is_holiday,
        base_price,
        distance_cost,
        weight_cost,
        property_cost,
        vehicle_cost,
        insurance_cost,
        service_multiplier,
        time_multiplier,
        weather_multiplier,
        vehicle_multiplier,
        active_config,
    ):
        """Calculate prices for different staff counts"""
        staff_prices = []
        default_rate = float(DEFAULT_STAFF_REQUIRED_PRICING["base_rate_per_staff"])

        for staff_count in range(1, 5):
            staff_cost = 0

            # Use the factor's base_rate_per_staff or fallback default_rate
            for factor in staff_factors:
                if factor.min_staff <= staff_count <= factor.max_staff:
                    rate = float(getattr(factor, "base_rate_per_staff", default_rate))
                    staff_cost = rate * staff_count

                    # Apply overtime multiplier on weekends/holidays
                    if is_weekend or is_holiday:
                        staff_cost *= float(factor.overtime_rate_multiplier)

                    break

            total_price = (
                base_price
                + distance_cost
                + weight_cost
                + property_cost
                + vehicle_cost
                + insurance_cost
                + staff_cost
            )
            total_price *= service_multiplier
            total_price *= time_multiplier
            total_price *= weather_multiplier
            total_price *= vehicle_multiplier

            fuel_surcharge = total_price * (
                float(active_config.fuel_surcharge_percentage) / 100
            )
            total_price += fuel_surcharge

            carbon_offset = total_price * (
                float(active_config.carbon_offset_rate) / 100
            )
            total_price += carbon_offset

            total_price = max(total_price, float(active_config.min_price))
            max_price = base_price * float(active_config.max_price_multiplier)
            total_price = min(total_price, max_price)
            total_price = round(total_price, 2)

            staff_prices.append(
                {
                    "staff_count": staff_count,
                    "price": total_price,
                }
            )

        return staff_prices
