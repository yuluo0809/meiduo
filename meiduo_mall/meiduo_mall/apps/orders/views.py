from decimal import Decimal
import json

from django.shortcuts import render
from django_redis import get_redis_connection
from django import http
from django.utils import timezone
from django.db import transaction

from goods.models import SKU
from meiduo_mall.utils.views import LoginRequiredView
from users.models import Address
from .models import OrderInfo, OrderGoods
from meiduo_mall.utils.response_code import RETCODE
import logging

logger = logging.getLogger('django')

class OrderSettlementView(LoginRequiredView):
    """结算订单"""

    def get(self, request):
        """提供订单结算页面"""
        # 获取登录用户
        user = request.user
        # 查询地址信息

        addresses = Address.objects.filter(user=request.user, is_deleted=False)

        # 如果地址为空，渲染模板时会判断，并跳转到地址编辑页面
        addresses = addresses or None

        # 从Redis购物车中查询出被勾选的商品信息
        redis_conn = get_redis_connection('carts')
        redis_cart = redis_conn.hgetall('carts_%s' % user.id)
        cart_selected = redis_conn.smembers('selected_%s' % user.id)
        cart = {}
        for sku_id in cart_selected:
            cart[int(sku_id)] = int(redis_cart[sku_id])

        # 准备初始值
        total_count = 0
        total_amount = Decimal(0.00)
        # 查询商品信息
        skus = SKU.objects.filter(id__in=cart.keys())
        for sku in skus:
            sku.count = cart[sku.id]
            sku.amount = sku.count * sku.price
            # 计算总数量和总金额
            total_count += sku.count
            total_amount += sku.count * sku.price
        # 补充运费
        freight = Decimal('10.00')

        # 渲染界面
        context = {
            'addresses': addresses,
            'skus': skus,
            'total_count': total_count,
            'total_amount': total_amount,
            'freight': freight,
            'payment_amount': total_amount + freight
        }

        return render(request, 'place_order.html', context)


class OrderCommitView(LoginRequiredView):
    """提交订单"""

    def post(self, request):
        # 1. 接收
        json_dict = json.loads(request.body.decode())
        address_id = json_dict.get('address_id')
        pay_method = json_dict.get('pay_method')
        user = request.user
        # 2. 校验
        if not all([address_id, pay_method]):
            return http.HttpResponseForbidden('缺少必传参数')
        try:
            address = Address.objects.get(id=address_id, user=user, is_deleted=False)
        except Exception:
            return http.HttpResponseForbidden('收货地址有误')
        if pay_method not in [OrderInfo.PAY_METHODS_ENUM['CASH'], OrderInfo.PAY_METHODS_ENUM['ALIPAY']]:
            return http.HttpResponseForbidden('支付方式错误')

        order_id = timezone.now().strftime('%Y%m%d%H%M%S') + '%09d' % user.id
        # 手动开启事务
        with transaction.atomic():
            # 创建事务保存点
            save_point = transaction.savepoint()
            try:
                # 3. 新增订单基本信息记录 OrderInfo
                order = OrderInfo.objects.create(
                    order_id=order_id,
                    user_id=user.id,
                    address_id=address.id,
                    total_count=0,
                    total_amount=Decimal('0.00'),
                    freight=Decimal('10.00'),
                    pay_method=pay_method,
                    status=(OrderInfo.ORDER_STATUS_ENUM['UNPAID'] if OrderInfo.PAY_METHODS_ENUM['ALIPAY']
                            else OrderInfo.ORDER_STATUS_ENUM["UNSEND"])
                )
                # 创建redis连接
                redis_conn = get_redis_connection('carts')
                # 将hash set中所有数据获取出来
                redis_cart = redis_conn.hgetall('carts_%s' % user.id)
                selected = redis_conn.smembers('selected_%s' % user.id)
                # 将redis购物车数据过滤,只留下要购买商品id和count
                carts = {}
                for sku_id in selected:  # 查询sku模型
                    carts[int(sku_id)] = int(redis_cart[sku_id])   # 判断库存,如果库存不足就下单失败
                sku_ids = carts.keys()   # 修改sku 的库存和销量
                # 遍历购物车中被勾选的商品信息
                for sku_id in sku_ids:
                    while True:
                        # 查询SKU信息
                        sku = SKU.objects.get(id=sku_id)

                        # 获取用户此商品要购物车的数量
                        buy_count = carts[sku_id]
                        # 定义两个变量用来记录当前sku的原本库存和销量
                        origin_stock = sku.stock
                        origin_sales = sku.sales
                        # 判断当前要购物车的商品库存是否充足
                        if buy_count > origin_stock:
                            # 如果库存不足,提前响应
                            transaction.savepoint_rollback(save_point)  # 回滚指定的保存点
                            return http.JsonResponse({'code': RETCODE.STOCKERR, 'errmsg': '库存不足'})

                        # 如果能购买,计算新的库存和销量
                        new_stock = origin_stock - buy_count
                        new_sales = origin_sales + buy_count
                        # 使用乐观锁解决资源抢夺,超卖
                        result = SKU.objects.filter(id=sku_id, stock=origin_stock).update(stock=new_stock,
                                                                                          sales=new_sales)
                        if result == 0:  # 修改失败
                            continue
                        # 修改sku模型库存和销量
                        sku.stock = new_stock
                        sku.sales = new_sales
                        sku.save()

                        # 修改SPU销量
                        sku.spu.sales += buy_count

                        sku.spu.save()

                        # 保存订单商品信息 OrderGoods（多）
                        OrderGoods.objects.create(
                            order=order,
                            sku=sku,
                            count=buy_count,
                            price=sku.price,
                        )

                        # 保存商品订单中总价和总数量
                        order.total_count += buy_count
                        order.total_amount += (buy_count * sku.price)
                        break  # 执行到此说明当前商品下单成功,跳出死循环,进行下一个商品购买
                # 添加邮费和保存订单信息
                order.total_amount += order.freight
                order.save()
            except Exception as e:
                logger.error(e)
                # 暴力回滚
                transaction.savepoint_rollback(save_point)
                return http.JsonResponse({'code': RETCODE.STOCKERR, 'errmsg': '下单失败'})

            else:
                # transaction.commit()  # 提交
                transaction.savepoint_commit(save_point)
            # 清除购物车中已结算的商品
            pl = redis_conn.pipeline()
            pl.hdel('carts_%s' % user.id, *selected)
            pl.srem('selected_%s' % user.id, *selected)
            pl.execute()

        # 响应提交订单结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '下单成功', 'order_id': order.order_id})


class OrderSuccessView(LoginRequiredView):
    """订单提交成功界面"""
    def get(self, request):

        query_dict = request.GET

        payment_amount = query_dict.get('payment_amount')
        order_id = query_dict.get('order_id')
        pay_method = query_dict.get('pay_method')
        try:
            OrderInfo.objects.get(order_id=order_id, pay_method=pay_method, total_amount=payment_amount, user=request.user)
        except OrderInfo.DoesNotExist:
            return http.HttpResponseForbidden('请求信息有误')

        context = {
            'payment_amount': payment_amount,
            'order_id': order_id,
            'pay_method': pay_method
        }
        return render(request, 'order_success.html', context)







































