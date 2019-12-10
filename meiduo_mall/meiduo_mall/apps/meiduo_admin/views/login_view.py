from rest_framework.response import Response
from rest_framework.views import APIView
from meiduo_admin.serializers.login_serializer import LoginSerializer


class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        return Response({
            'username': serializer.validated_data['user'].username,
            'user_id': serializer.validated_data['user'].id,
            'token': serializer.validated_data['token'],
        })
