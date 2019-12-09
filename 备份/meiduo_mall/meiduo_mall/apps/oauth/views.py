from django.shortcuts import render, redirect
from django.views import View
from QQLoginTool.QQtool import OAuthQQ
from django import http
from django.conf import settings
from django.contrib.auth import login
import re
from django_redis import get_redis_connection

from meiduo_mall.utils.response_code import RETCODE
from .models import OAuthQQUser
from users.models import User
from .utils import generate_open_id_signature, check_open_id
from carts.utils import merge_cart_cookie_to_redis


class QQAuthURLView(View):
    """拼接QQ登录url"""

    def get(self, request):
        # 1. 接收查询参数
        next = request.GET.get('next') or '/'

        # 2. 创建OAuthQQ 对象
        # auth_tool = OAuthQQ(client_id='appid', client_secret='appkey', redirect_uri='回调地址', state='把它当成next')
        # auth_tool = OAuthQQ(client_id='101568493', client_secret='e85ad1fa847b5b79d07e40f8f876b211', redirect_uri='http://www.meiduo.site:8000/oauth_callback', state=next)
        auth_tool = OAuthQQ(client_id=settings.QQ_CLIENT_ID,
                            client_secret=settings.QQ_CLIENT_SECRET,
                            redirect_uri=settings.QQ_REDIRECT_URI,
                            state=next)
        # 3. 调用OAuthQQ 里面的get_qq_url方法得到拼接好的QQ登录url
        login_url = auth_tool.get_qq_url()

        # 4. 响应json
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'login_url': login_url})


class QQAuthView(View):
    """QQ登录成功回调处理"""

    def get(self, request):
        # 1. 获取查询参数中的code
        code = request.GET.get('code')
        # 2. 校验
        if code is None:
            return http.HttpResponseForbidden('缺少code')
        # 3. 创建QQ登录工具对象
        auth_tool = OAuthQQ(client_id=settings.QQ_CLIENT_ID,
                            client_secret=settings.QQ_CLIENT_SECRET,
                            redirect_uri=settings.QQ_REDIRECT_URI)

        # 4. 调用get_access_token
        access_token = auth_tool.get_access_token(code)
        #  调用get_openid
        openid = auth_tool.get_open_id(access_token)
        # 查询openid是否和美多中的user有关联
        try:
            # 查询openid是否和美多中的user有关联
            oauth_model = OAuthQQUser.objects.get(openid=openid)
            # 如果openid查询到了(openid已绑定用户, 代表登录成功)
            user = oauth_model.user
            # 状态保持
            login(request, user)
            # 向cookie中存储username
            response = redirect(request.GET.get('state') or '/')
            response.set_cookie('username', user.username, max_age=settings.SESSION_COOKIE_AGE)
            # 合并购物车
            merge_cart_cookie_to_redis(request, response)

            # 重定向到来源
            return response
        except OAuthQQUser.DoesNotExist:
            # 如果openid没有查询到(openid还没有绑定用户, 没有绑定,渲染一个绑定用户界面)
            # 对openid进行加密
            openid = generate_open_id_signature(openid)
            context = {'openid': openid}
            return render(request, 'oauth_callback.html', context)

    def post(self, request):
        """openid绑定用户"""
        # 1. 接收表单中的数据
        query_dict = request.POST
        # dict1 = query_dict.dict()
        # dict1.values()
        mobile = query_dict.get('mobile')
        password = query_dict.get('password')
        sms_code = query_dict.get('sms_code')
        openid = query_dict.get('openid')
        # 2. 校验
        if all([mobile, password, sms_code, openid]) is False:
            return http.HttpResponseForbidden('缺少必传参数')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('手机号格式有误')
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('请输入8-20个字符的密码')

        # 校验短信验证码
        redis_conn = get_redis_connection('verify_codes')
        sms_code_server = redis_conn.get('sms_%s' % mobile)
        redis_conn.delete('sms_%s' % mobile)
        if sms_code_server is None:
            return http.HttpResponseForbidden('短信验证码已过期')
        if sms_code != sms_code_server.decode():
            return http.HttpResponseForbidden('短信验证码填写错误')
        try:
            # 3. 查询手机号是否已注册过
            user = User.objects.get(mobile=mobile)
            # 4. 注册过再校验传入的密码是否正确
            if user.check_password(password) is False:
                return http.HttpResponseForbidden('绑定失败')
        except User.DoesNotExist:
            # 5. 如果手机号是新的,就创建一个新用户
            user = User.objects.create_user(username=mobile, password=password, mobile=mobile)
        # 对openid进行解密
        openid = check_open_id(openid)
        if openid is None:
            return http.HttpResponseForbidden('openid无效')  # 可以自己制作一个页面专门处理该事件
        # 6.openid绑定美多新老用户
        OAuthQQUser.objects.create(
            openid=openid,
            user=user,
        )
        # 7. 状态保持
        login(request, user)

        # 8. 存储cookie中的username
        response = redirect(request.GET.get('state') or '/')
        response.set_cookie('username', user.username, max_age=settings.SESSION_COOKIE_AGE)

        # 合并购物车
        merge_cart_cookie_to_redis(request, response)

        # 9. 重定向到来源
        return response
