from User.models import User
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # fields = ('id', 'email', 'username', 'is_verified', 'created_at')
        # read_only_fields = ('is_verified', 'created_at')

