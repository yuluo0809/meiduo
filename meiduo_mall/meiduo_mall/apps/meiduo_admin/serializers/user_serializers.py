from rest_framework import serializers
from users.models import User
from django.contrib.auth.hashers import make_password


class UserModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'mobile',
            'email',

            'password',
        ]

        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate(self, attrs):
        # 在校验流程中

        # 1、密码加密
        password = attrs.get('password')
        password = make_password(password)  # 密文密码
        attrs['password'] = password  # 有效数据中的明文密码改为密闻密码

        # 2、额外添加is_staff=True有效数据
        attrs['is_staff'] = True

        return attrs
