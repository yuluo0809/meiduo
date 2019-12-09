from django.shortcuts import render
from meiduo_mall.utils.views import LoginRequiredView
from django import http
from alipay import AliPay
from django.conf import settings
import os

from orders.models import OrderInfo
from meiduo_mall.utils.response_code import RETCODE
from .models import Payment


class PaymentURLView(LoginRequiredView):
    """拼接支付链接"""

    def get(self, request, order_id):
        # 1. 校验
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=request.user)
        except OrderInfo.DoesNotExist:
            return http.HttpResponseForbidden('订单有误')

        # 2. 创建 Alipay支付对象
        alipay = AliPay(
            appid=settings.ALIPAY_APPID,  # 应用id
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                              'keys/app_private_key.pem'),
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,)
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                'keys/alipay_public_key.pem'),
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=settings.ALIPAY_DEBUG  # 默认False
        )

        # 3. 调用此方法api_alipay_trade_page_pay得到支付url的查询参数部分
        # 电脑网站支付，需要跳转到https://openapi.alipay.com/gateway.do? + order_string
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,  # 要支付的美多订单编号
            total_amount=str(order.total_amount),  # 支付金额,注意转换类型
            subject='美多商城:%s' % order_id,
            return_url=settings.ALIPAY_RETURN_URL,  # 回调url
        )
        # 4. 拼接支付登录url
        # 真实支付宝登录url: https://openapi.alipay.com/gateway.do? + order_string
        # 沙箱支付宝登录url: https://openapi.alipaydev.com/gateway.do? + order_string
        alipay_url = settings.ALIPAY_URL + '?' + order_string
        # 5. 响应
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'alipay_url': alipay_url})


class PaymentStatusView(LoginRequiredView):
    """保存支付结果"""
    def get(self, request):

        # 1. 接收查询参数
        query_dict = request.GET
        # 2. 将QueryDict类型对象转换成字典
        data = query_dict.dict()
        # 3. 将sign签名从字典中移除 pop
        sign = data.pop('sign')
        # 4. 创建alipay对象
        alipay = AliPay(
            appid=settings.ALIPAY_APPID,  # 应用id
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'keys/app_private_key.pem'),
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,)
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                'keys/alipay_public_key.pem'),
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=settings.ALIPAY_DEBUG  # 默认False
        )

        # 5. 调用verify方法进行校验(data, sign)
        if alipay.verify(data, sign):
            # 获取美多订单编号
            order_id = data.get('out_trade_no')
            # 获取支付宝交易号
            trade_id = data.get('trade_no')
            # 保存支付结果
            try:
                Payment.objects.get(trade_id=trade_id)
            except Payment.DoesNotExist:
                Payment.objects.create(
                    order_id=order_id,
                    trade_id=trade_id
                )
                # 修改已支付订单状态
                OrderInfo.objects.filter(user=request.user,
                                         order_id=order_id,
                                         status=OrderInfo.ORDER_STATUS_ENUM['UNPAID']).update(
                    status=OrderInfo.ORDER_STATUS_ENUM['UNCOMMENT'])
            # 渲染支付成功界面
            return render(request, 'pay_success.html', {'trade_id': trade_id})
        else:
            return http.HttpResponseForbidden('非法请求')
