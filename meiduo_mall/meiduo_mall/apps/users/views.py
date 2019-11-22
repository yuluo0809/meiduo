from django.shortcuts import render, redirect, reverse
from django.views import View
from django import http
import re
from .models import *
from django.contrib.auth import login, authenticate, logout
from django_redis import get_redis_connection
from django.db.models import Q
from django.conf import settings


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

        # 短信验证码的验证
        # 创建redis连接
        redis_conn = get_redis_connection('verify_codes')
        # 获取redis的当前手机号对应的短信验证码
        sms_code_server = redis_conn.get('sms_%s' % mobile)
        # 将获取出来的短信验证码从redis删除(让短信验证码是一次性)
        redis_conn.delete('sms_%s' % mobile)
        # 判断短信验证码是否过期
        if sms_code_server is None:
            return render(request, 'register.html', {'register_errmsg': '短信验证码已过期'})
        # 判断用户填写短信验证码是否正确
        if sms_code != sms_code_server.decode():
            return render(request, 'register.html', {'register_errmsg': '短信验证码填写错误'})

        # 3.新增用户
        user = User.objects.create_user(username=username, password=password, mobile=mobile)
        # 登入用户，实现状态保持
        login(request, user)
        # 响应注册结果
        response = redirect('/')
        response.set_cookie('username', user.username, max_age=settings.SESSION_COOKIE_AGE)
        return response


class UsernameCountView(View):
    """判断用户名是否重复注册"""

    def get(self, request, username):
        """
        :param request: 请求对象
        :param username: 用户名
        :return: JSON
        """
        count = User.objects.filter(username=username).count()
        return http.JsonResponse({'count': count})


class MobileCountView(View):
    """判断手机号是否重复注册"""

    def get(self, request, mobile):
        """
        :param request: 请求对象
        :param mobile: 手机号
        :return: JSON
        """
        count = User.objects.filter(mobile=mobile).count()
        return http.JsonResponse({'count': count})


class LoginView(View):
    """用户登录"""

    def get(self, request):
        return render(request, 'login.html')

    def post(self, request):
        """用户登录"""
        # 1. 接收
        query_dict = request.POST
        username = query_dict.get('username')
        password = query_dict.get('password')
        remembered = query_dict.get('remembered')
        # 2. 校验
        if all([username, password]) is False:
            return http.HttpResponseForbidden('缺少必传参数')

        # 3. 判断用户名及密码是否正确
        qs = User.objects.filter(Q(username=username) | Q(mobile=username))
        if qs.exists():
            user = qs[0]
            if user.check_password(password) is False:
                return http.HttpResponseForbidden('用户名或密码错误')
        else:
            return http.HttpResponseForbidden('用户名或密码错误')

        # 用户认证,通过认证返回user 反之返回None
        # user = authenticate(request, username=username, password=password)
        # if user is None:
        #     return http.HttpResponseForbidden('用户名或密码错误')

        # 4. 状态保持
        login(request, user)
        if remembered is None:
            request.session.set_expiry(0)
        # 5. 重定向
        response = redirect('/')
        response.set_cookie('username', user.username,
                            max_age=settings.SESSION_COOKIE_AGE if remembered == 'on' else None)
        return response


class LogoutView(View):
    """退出登录"""

    def get(self, request):
        # 1. 清除状态操持
        logout(request)
        # 2. 删除cookie中的username
        response = redirect('/login/')
        response.delete_cookie('username')
        # 3. 重定向到login
        return response
