from django.shortcuts import render, redirect
from django.views import View
from django import http
import re
from django.contrib.auth import login, authenticate, logout
from django_redis import get_redis_connection
from django.db.models import Q
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
import json
from django.db.utils import DataError, DatabaseError

from .models import *
from meiduo_mall.utils.views import LoginRequiredView
from meiduo_mall.utils.response_code import RETCODE
from celery_tasks.email.tasks import send_verify_url
from .utils import generate_email_verify_url, get_user_token
import logging

logger = logging.getLogger('django')


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
        response = redirect(request.GET.get('next') or '/')
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


# 方案一：
# class InfoView(View):
#     """用户中心"""
#     def get(self, request):
#         # if isinstance(request.user, User):  # 判断request.user属性值是不是User类型或子类创建出来的实例对象
#         if request.user.is_authenticated:  # 判断用户登录
#             return render(request, 'user_center_info.html')
#         else:
#             return redirect('/login/?next=/info/')

# 优化方案

class InfoView(LoginRequiredMixin, View):
    """用户中心"""

    def get(self, request):
        return render(request, 'user_center_info.html')


class EmailView(LoginRequiredView):
    """设置邮箱"""

    def put(self, request):
        # 1.接收json数据
        json_str_bytes = request.body
        # 解码byte数据
        json_str = json_str_bytes.decode()
        # 转成字典
        json_dict = json.loads(json_str)
        # 得到字典中的邮箱
        email = json_dict.get('email')
        # 2.校验
        if not re.match(r'^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$', email):
            return http.HttpResponseForbidden('邮箱格式有误')
        # 3. 修改user的email字段，然后保存（save()）
        user = request.user  # request 中的用户信息哪里来的？
        if user.email == '':  # 数据库里用户邮箱为空时,再设置。
            user.email = email
            user.save()

        # 给用户的邮箱发送激活邮件

        from django.core.mail import send_mail
        # send_mail(subject='主题/标题', message='普通邮件内容', from_email='发件人邮箱', recipient_list=['收件人邮箱列表'],
        # html_message='超文本邮箱内容')
        # send_mail('hello', '', '美多商城<itcast99@163.com>', [email],
        #           html_message='<a href="http://www.baidu.com">百度一下</a>')
        verify_url = generate_email_verify_url(user)
        # send_verify_url.delay(email, verify_url)
        send_verify_url(email, verify_url)
        # 4.响应
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})


class EmailVerifyView(View):
    """激活邮箱"""

    def get(self, request):
        # 1.接收查询参数token
        token = request.GET.get('token')
        # 2. 对token进行解密
        user = get_user_token(token)
        # 判断是否拿到user,如果有
        if user is None:
            return http.HttpResponseForbidden('邮箱激活失败')
        # 将user的email_active改国True 再save
        user.email_active = True
        user.save()
        # 响应
        # return render(request, 'user_center_info.html')
        return redirect('/info/')


class AddressView(LoginRequiredView):
    """用户收货地址"""

    def get(self, request):
        user = request.user
        # 查询当前用户未逻辑删除的所有收货地址
        address_qs = Address.objects.filter(user=user, is_deleted=False)

        # 模型转字典并包装到列表中
        address_list = []
        for address in address_qs:
            address_list.append({
                'id': address.id,
                'title': address.title,
                'receiver': address.receiver,
                'province_id': address.province_id,
                'province': address.province.name,
                'city_id': address.city_id,
                'city': address.city.name,
                'district_id': address.district_id,
                'district': address.district.name,
                'place': address.place,
                'mobile': address.mobile,
                'tel': address.tel,
                'email': address.email,
            })

        context = {
            'addresses': address_list,  # 用户的所有收货地址
            'default_address_id': user.default_address_id
        }
        return render(request, 'user_center_site.html', context)


class AddressCreateView(LoginRequiredView):
    """新增收货地址"""

    def post(self, request):
        # 1. 接收数据
        json_dict = json.loads(request.body.decode())
        title = json_dict.get('title')
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.pop('tel')
        email = json_dict.pop('email')

        # 2. 校验
        if all(json_dict.values()) is False:
            return http.HttpResponseForbidden('缺少必传参数')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('手机格式有误')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden('参数email有误')
        # 获取user
        user = request.user
        # 3. 新增收货地址
        address = Address()
        address.user = user
        address.title = title
        address.receiver = receiver
        address.province_id = province_id
        address.city_id = city_id
        address.district_id = district_id
        address.place = place
        address.mobile = mobile
        address.tel = tel
        address.email = email
        try:
            address.save()
        except DatabaseError as e:
            logger.error(e)
            return http.HttpResponseForbidden('数据有误')

        # 模型转字典
        address_dict = {
            'id': address.id,
            'title': address.title,
            'receiver': address.receiver,
            'province_id': address.province_id,
            'province': address.province.name,
            'city_id': address.city_id,
            'city': address.city.name,
            'district_id': address.district_id,
            'district': address.district.name,
            'place': address.place,
            'mobile': address.mobile,
            'tel': address.tel,
            'email': address.email,
        }
        # 如果用户还没有默认地址,就把当前新增的地址设置为它的默认地址
        if user.default_address is None:
            user.default_address = address
            user.save()
        # 4. 响应
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'address': address_dict})


class AddressDeleteAndUpdateView(LoginRequiredView):
    """删除和修改收货地址"""

    # 处理前端发起的delete请求
    def delete(self, request, addresses_id):
        user = request.user

        address = Address.objects.get(user=user, id=addresses_id)
        address.is_deleted = True
        address.save()
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '删除成功'})

    # 处理前端发起的put请求
    def put(self, request, addresses_id):
        # 1. 接收数据
        json_dict = json.loads(request.body.decode())
        title = json_dict.get('title')
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.pop('tel')
        email = json_dict.pop('email')

        # 2. 校验
        if all([title, receiver, province_id, city_id, district_id, place, mobile]) is False:
            return http.HttpResponseForbidden('缺少必传参数')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('手机格式有误')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden('参数email有误')

        # 3. 更新数据
        new_address = Address.objects.get(id=addresses_id)
        new_address.title = title
        new_address.receiver = receiver
        new_address.province_id = province_id
        new_address.city_id = city_id
        new_address.district_id = district_id
        new_address.place = place
        new_address.mobile = mobile
        new_address.tel = tel
        new_address.email = email
        try:
            new_address.save()
        except DatabaseError as e:
            logger.error(e)
            return http.HttpResponseForbidden('数据有误')

        # 模型转字典
        new_address_dict = {
            'id': addresses_id,
            'title': new_address.title,
            'receiver': new_address.receiver,
            'province_id': new_address.province_id,
            'province': new_address.province.name,
            'city_id': new_address.city_id,
            'city': new_address.city.name,
            'district_id': new_address.district_id,
            'district': new_address.district.name,
            'place': new_address.place,
            'mobile': new_address.mobile,
            'tel': new_address.tel,
            'email': new_address.email,
        }
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '修改成功', 'address': new_address_dict})


# 设置默认地址
class SetDefaultAddressView(LoginRequiredView):
    def put(self, request, addresses_id):
        user = request.user
        address = Address.objects.get(user=user, id=addresses_id)
        user.default_address = address
        user.save()

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '设置成功'})


# 修改地址标题
class ChangeAddressTitleView(LoginRequiredView):
    def put(self, request, addresses_id):
        json_dict = json.loads(request.body.decode())
        title = json_dict.get('title')
        user = request.user
        address = Address.objects.get(user=user, id=addresses_id)
        address.title = title
        address.save()

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '修改成功'})


# 修改密码
class ChangePasswordView(LoginRequiredView):
    def get(self, request):
        """进入密码修改界面"""
        return render(request, 'user_center_pass.html')

    def post(self, request):
        query_dict = request.POST
        password = query_dict.get('old_pwd')
        new_password = query_dict.get('new_pwd')
        new_password2 = query_dict.get('new_cpwd')

        user = request.user

        if user.check_password(password) is False:
            return render(request, 'user_center_pass.html', {'origin_pwd_errmsg': '原密码输入不正确'})
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('请输入8-20个字符的密码~~!')
        if new_password != new_password2:
            return http.HttpResponseForbidden('两次密码输入不一致~~!')

        user.set_password(new_password)
        user.save()
        logout(request)
        response = redirect('/login/')
        response.delete_cookie('username')
        return response