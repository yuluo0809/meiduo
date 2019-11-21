from django.shortcuts import render
from django.views import View
from django import http
from django_redis import get_redis_connection

from meiduo_mall.meiduo_mall.libs.captcha.captcha import captcha
from meiduo_mall.meiduo_mall.utils.response_code import RETCODE, err_msg


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

        # 1. 接收
        query_dict = request.GET
        image_code_client = query_dict.get('image_code')
        uuid = query_dict.get('uuid')

        # 2. 校验
        if all([image_code_client, uuid]) is False:
            return http.HttpResponseForbidden('缺少必传参数')
        # 2.1 创建redis连接对象
        redis_conn = get_redis_connection('verify_codes')
        # 2.2 获取redis中图形验证码字符
        image_code_server_bytes = redis_conn.get(uuid)
        # 3.2 判断redis中的图形验证码是否已过期
        if image_code_server_bytes is None:
            return http.JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图形验证码已过期'})
        # 3.3 将bytes类型转换成str (从redis中获取出来的数据都是bytes  str, dict, list, set)
        image_code_server = image_code_server_bytes.decode()
        # 判断用户填写验证码和redis取的是否一致
        if image_code_client.lower() != image_code_server.lower():
            return http.JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图形验证码填写错误'})


        # 3. 发短信
        # 3.1 创建redis连接对象
        # 3.2 存储短信验证码到redis

        # 响应

        pass

