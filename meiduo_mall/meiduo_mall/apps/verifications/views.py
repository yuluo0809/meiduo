from django.shortcuts import render
from django.views import View
from django import http
from django_redis import get_redis_connection
from random import randint
from django.db.models import Q
from django.conf import settings

from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadData

from meiduo_mall.utils.response_code import RETCODE, err_msg
from meiduo_mall.libs.captcha.captcha import captcha
# from meiduo_mall.libs.yuntongxun.sms import CCP
from users.models import User
from . import constants
from celery_tasks.sms.tasks import send_sms_code
from .utils import get_account_token

import logging

# 创建日志输出器对象
logger = logging.getLogger('django')


class ImageCodeView(View):
    """图形验证码"""

    def get(self, request, uuid):
        """
        :param request:
        :param uuid: 用来当 图形验证码字符存储到redis key ,目的是用于区别redis的图形验证码是那个用户
        :return:
        """

        # 1. 调用sdk 生成图形验证码
        # name: 唯一标识, text: 图形验证码字符串, image: 图形验证码图形bytes数据
        name, text, image = captcha.generate_captcha()
        # 2. 创建redis连接对象
        redis_conn = get_redis_connection('verify_codes')
        # 3. 将图形验证码 字符串存储到redis中
        redis_conn.setex(uuid, 300, text)
        # 4. 响应图片数据
        return http.HttpResponse(image, content_type='image/png')


class SMSCodeView(View):
    """短信验证码"""

    def get(self, request, mobile):
        # 0. 创建redis连接对象
        redis_conn = get_redis_connection('verify_codes')
        # 先尝试获取redis中此手机号60s内是否发送短信标识
        send_flag = redis_conn.get('send_flag_%s' % mobile)
        # 判断是否有标识,如果有提前响应
        if send_flag:
            return http.JsonResponse({'code': RETCODE.THROTTLINGERR, 'errmsg': '频繁发送短信'})

        # 1. 接收
        query_dict = request.GET
        image_code_client = query_dict.get('image_code')
        uuid = query_dict.get('uuid')

        # 2. 校验
        if all([image_code_client, uuid]) is False:
            return http.HttpResponseForbidden('缺少必传参数')

        # 2.2 获取redis中图形验证码字符
        image_code_server_bytes = redis_conn.get(uuid)

        pl = redis_conn.pipeline()
        # 2.2.1 将redis中的图形验证码删除,让它是一次性
        pl.delete(uuid)
        # 3.2 判断redis中的图形验证码是否已过期
        if image_code_server_bytes is None:
            return http.JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图形验证码已过期'})
        # 3.3 将bytes类型转换成str (从redis中获取出来的数据都是bytes  str, dict, list, set)
        image_code_server = image_code_server_bytes.decode()
        # 判断用户填写验证码和redis取的是否一致
        if image_code_client.lower() != image_code_server.lower():
            return http.JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图形验证码填写错误'})

        # 3. 生成6位随机数字做为短信验证码
        sms_code = '%06d' % randint(0, 999999)
        logger.info(sms_code)

        # CCP().send_template_sms('接收收短信手机号', ['验证码', '提示用户的过期时间:单秒分钟'], 1)
        # 3.1 发送短信
        # CCP().send_template_sms(mobile, [sms_code, 5], 1)
        # send_sms_code.delay(mobile, sms_code)  # 触发异步任务
        send_sms_code(mobile, sms_code)
        # 3.2 存储短信验证码到redis,以备注册时验证短信验证码
        pl.setex('sms_%s' % mobile, constants.SMS_CODE_EXPIRE, sms_code)

        # 3.3 向redis存储一个此手机号60s内发过短信标识
        pl.setex('send_flag_%s' % mobile, 60, 1)

        pl.execute()
        # 4. 响应
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})


# 验证账户
class VerifyAccountsView(View):
    def get(self, request, accounts):
        image_code_client = request.GET.get('text')
        uuid = request.GET.get('image_code_id')
        if all([accounts, image_code_client, uuid]) is False:
            return http.HttpResponseForbidden('缺少必传参数')
        qs = User.objects.filter(Q(username=accounts) | Q(mobile=accounts))
        if qs.exists():
            user = qs[0]
        else:
            return http.HttpResponseForbidden('用户名输入不正确')

        redis_conn = get_redis_connection('verify_codes')
        image_code_server_bytes = redis_conn.get(uuid)
        # "删除uuid，保证一次有效性"
        redis_conn.delete(uuid)
        if image_code_server_bytes is None:
            return http.HttpResponseForbidden('图形验证码已过期')
        image_code_server = image_code_server_bytes.decode()
        if image_code_client.lower() != image_code_server.lower():
            return http.HttpResponseForbidden('图形验证码填写错误')
        data = {'user_id': user.id, 'mobile': user.mobile}
        serializer = Serializer(secret_key=settings.SECRET_KEY, expires_in=3600)
        access_token = serializer.dumps(data).decode()

        mobile = str(user.mobile)
        mobile = mobile[:3] + '****' + mobile[7:]
        return http.JsonResponse({'mobile': mobile, 'access_token': access_token})


# 发送短信
class AccountSMSView(View):
    def get(self, request):
        token = request.GET.get('access_token')
        data = get_account_token(token)
        mobile = data['mobile']
        # 0. 创建redis连接对象
        redis_conn = get_redis_connection('verify_codes')
        # 先尝试获取redis中此手机号60s内是否发送短信标识
        send_flag = redis_conn.get('send_flag_%s' % mobile)
        # 判断是否有标识,如果有提前响应
        if send_flag:
            return http.JsonResponse({'code': RETCODE.THROTTLINGERR, 'errmsg': '频繁发送短信'})

        sms_code = '%06d' % randint(0, 999999)
        logger.info(sms_code)
        send_sms_code(mobile, sms_code)
        redis_conn.setex('sms_%s' % mobile, constants.SMS_CODE_EXPIRE, sms_code)
        redis_conn.setex('send_flag_%s' % mobile, 60, 1)
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})


# 验证短信
class VerifySMSCodeView(View):

    def get(self, request, accounts):
        user = User.objects.get(Q(username=accounts) | Q(mobile=accounts))
        mobile = user.mobile
        sms_code_client = request.GET.get('sms_code')
        # 创建redis连接
        redis_conn = get_redis_connection('verify_codes')
        # 获取redis的当前手机号对应的短信验证码
        sms_code_server = redis_conn.get('sms_%s' % mobile)
        if sms_code_server is None:
            return render(request, 'find_password.html', {'find_password_errmsg': '短信验证码已过期'})
        if sms_code_client != sms_code_server.decode():
            return render(request, 'find_password.html', {'find_password_errmsg': '短信验证码填写错误'})
        data = {'user_id': user.id, 'mobile': user.mobile}
        serializer = Serializer(secret_key=settings.SECRET_KEY, expires_in=3600)
        access_token = serializer.dumps(data).decode()
        return http.JsonResponse({'user_id': user.id, 'access_token': access_token})
