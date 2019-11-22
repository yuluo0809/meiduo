from django.shortcuts import render
from django.views import View
from QQLoginTool.QQtool import OAuthQQ
from django import http

from meiduo_mall.utils.response_code import RETCODE


class QQAuthURLView(View):
    """拼接QQ登录url"""
    def get(self, request):
        # 1. 接收查询参数
        next = request.GET.get('next') or '/'

        # 2. 创建OAuthQQ 对象
        # auth_tool = OAuthQQ(client_id='appid', client_secret='appkey', redirect_uri='回调地址', state='把它当成next')
        auth_tool = OAuthQQ(client_id='101568493', client_secret='e85ad1fa847b5b79d07e40f8f876b211', redirect_uri='http://www.meiduo.site:8000/oauth_callback', state=next)

        # 3. 调用OAuthQQ 里面的get_qq_url方法得到拼接好的QQ登录url
        login_url = auth_tool.get_qq_url()

        # 4. 响应json
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'login_url': login_url})
