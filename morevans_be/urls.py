# urls.py
from django.urls import path, include
from django.contrib import admin

import ApiConnectionStatus
import ApiConnectionStatus.views
from Authentication.views import UserViewSet
from rest_framework import routers
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)

router = routers.DefaultRouter()
router.register(r'users', UserViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('status/', ApiConnectionStatus.views.ApiConnectionStatusView.as_view(), name='status'),
    path('admin/', admin.site.urls),
    path('auth/', include('Authentication.urls')),
]
