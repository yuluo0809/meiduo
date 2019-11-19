from django.shortcuts import render
from django.views import View
from django import http
import re
from .models import *


class RegisterView(View):
    """用户注册"""

    def get(self, request):
        """
        提供注册界面
        :param request: 请求对象
        :return: 注册界面
        """
        return render(request, 'register.html')

    def post(self, request):
        """处理POST请求，实现注册逻辑"""
        query_dict = request.POST
        username = query_dict.get('username')
        password = query_dict.get('password')
        password2 = query_dict.get('password2')
        mobile = query_dict.get('mobile')
        sms_code = query_dict.get('sms_code')
        allow = query_dict.get('allow')

        if all([username, password, password2, mobile, sms_code, allow]) is False:
            return http.HttpResponseForbidden('非正常访问')

        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('请输入5-20个字符的用户名（字母开头）')

        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('请输入8-20个字符的密码')
        if password != password2:
            return http.HttpResponseForbidden('两次密码输入不一致')
        if not re.match(r'^1[345789]\d{9}', mobile):
            return http.HttpResponseForbidden('您输入的手机号格式不正确')
        if allow != 'on':
            return http.HttpResponseForbidden('请勾选用户协议')

        # TODO 待增加

        user = User.objects.create_user(username=username, password=password, mobile=mobile)
        return http.HttpResponse('注册成功')


