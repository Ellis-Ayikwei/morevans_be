from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from User.models import User
from User.serializer import UserSerializer
from rest_framework import status, permissions
from rest_framework.views import  APIView
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.backends import TokenBackend
from rest_framework_simplejwt.settings import api_settings
import logging

from .serializer import LoginSerializer, PasswordChangeSerializer, PasswordRecoverySerializer, PasswordResetConfirmSerializer,  RegisterSerializer

logger = logging.getLogger(__name__)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

class RegisterAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Send verification email here
            return Response(
                {'message': 'User created successfully. Please check your email for verification.'},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        print("user.......", user)
        
        # Create refresh token for the user
        refresh = RefreshToken.for_user(user)
        
        # Validate the generated refresh token by decoding it
        try:
            token_backend = TokenBackend(
                algorithm=api_settings.ALGORITHM,
                signing_key=api_settings.SIGNING_KEY,
            )
            # Decode the refresh token; this will raise a TokenError if invalid
            decoded_payload = token_backend.decode(str(refresh), verify=True)
            logger.debug(f"Decoded refresh token payload: {decoded_payload}")
        except TokenError as e:
            logger.exception("Error: Generated refresh token is invalid.")
            return Response(
                {"detail": "Generated token is invalid."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })

class LogoutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # Retrieve the refresh token from the request data
        refresh_token = request.data.get("refresh_token")
        logger.debug(f"Received refresh token: {refresh_token}")  # For debugging only

        if not refresh_token:
            return Response(
                {"detail": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            token = RefreshToken(refresh_token)
            # Extract user_id from token payload
            user_id = token.payload.get('user_id')
            logger.debug(f"Token user_id: {user_id}, Request user id: {request.user.id}")

            # Ensure the token belongs to the requesting user
            if str(user_id) != str(request.user.id):
                return Response(
                    {"detail": "Invalid token for this user."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Blacklist the token
            token.blacklist()
            return Response(
                {"detail": "Logout successful."},
                status=status.HTTP_205_RESET_CONTENT
            )
        except TokenError as e:
            logger.exception("Error blacklisting token")
            return Response(
                {"detail": "Invalid token or token already blacklisted."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception("Unexpected error during logout")
            return Response(
                {"detail": "Internal server error."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
class PasswordRecoveryAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordRecoverySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = User.objects.filter(email=serializer.validated_data['email']).first()
        if user:
            token_generator = PasswordResetTokenGenerator()
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = token_generator.make_token(user)
            
            reset_url = reverse('password_reset_confirm', kwargs={
                'uidb64': uid,
                'token': token
            })
            absolute_url = request.build_absolute_uri(reset_url)
            
            send_mail(
                'Password Reset Request',
                f'Use this link to reset your password: {absolute_url}',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
        
        return Response({'detail': 'Password reset link sent if account exists'}, 
                       status=status.HTTP_200_OK)

class PasswordResetConfirmAPIView(APIView):
    """
    API endpoint for confirming a password reset.

    - Accepts a JSON payload with the following format:
      {
        "password": "<new password>",
        "uidb64": "<base64 encoded user id>",
        "token": "<reset token>"
      }

    - Returns a JSON response with the following format:
      {
        "detail": "Password reset successfully"
      }

    - If the token is invalid, returns a JSON response with the following format:
      {
        "detail": "Invalid token"
      }
      with a 400 status code.

    :param request: The request object.
    :param uidb64: The base64 encoded user id.
    :param token: The token to verify the user.
    :return: A JSON response with the result of the operation.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, uidb64, token):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            uid = force_str(urlsafe_base64_decode(serializer.validated_data['uidb64']))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
            
        token_generator = PasswordResetTokenGenerator()
        if user and token_generator.check_token(user, serializer.validated_data['token']):
            user.set_password(serializer.validated_data['password'])
            user.save()
            return Response({'detail': 'Password reset successfully'})
        
        return Response({'detail': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


class PasswordChangeAPIView(APIView):
    """
    API endpoint for changing the current user's password.

    - Accepts a JSON payload with the following format:
      {
        "old_password": "<current password>",
        "new_password": "<new password>"
      }

    - Returns a JSON response with the following format:
      {
        "detail": "Password updated successfully"
      }

    - Returns a JSON response with the following format in case of an error:
      {
        "old_password": "<error message>"
      }

    - Requires the "is_authenticated" permission.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Handles the POST request to change the current user's password.
        """
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check if the old password is correct
        if not request.user.check_password(serializer.validated_data['old_password']):
            return Response({'old_password': 'Wrong password'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        # Update the user's password
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        
        # Return a success response
        return Response({'detail': 'Password updated successfully'})

