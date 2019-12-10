# 需要定义一个序列化器
# 来校验username和password，并且校验成功后需要生成token(有效数据)

from rest_framework import serializers
from rest_framework_jwt.utils import jwt_encode_handler, jwt_payload_handler

from django.contrib.auth import authenticate


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(write_only=True, required=True, max_length=30)
    password = serializers.CharField(write_only=True, required=True, max_length=30)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        user = authenticate(username=username, password=password)
        if not user or not user.is_active:
            raise serializers.ValidationError('传统验证失败')

        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)


        return {
            'user': user,
            'token': token
        }
