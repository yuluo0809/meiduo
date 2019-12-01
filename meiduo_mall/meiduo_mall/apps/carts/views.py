from django.shortcuts import render
from django.views import View
import json, pickle, base64
from django import http
from django_redis import get_redis_connection

from goods.models import SKU
import logging
from meiduo_mall.utils.response_code import RETCODE

logger = logging.getLogger('django')


class CartView(View):
    """购物车"""

    def post(self, request):
        """添加购物车"""
        # 1. 接收
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected', True)

        # 2. 校验
        try:
            sku = SKU.objects.get(id=sku_id, is_launched=True)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('sku_id不存在')
        try:
            count = int(count)
        except Exception as e:
            logger.error(e)
            return http.HttpResponseForbidden('变量类型有误')

        if isinstance(selected, bool) is False:
            return http.HttpResponseForbidden('变量类型有误')

        response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})
        # 获取user
        user = request.user
        # 3. 判断用户是否登录
        if user.is_authenticated:
            # 登录用户存储购物车数据到redis
            """
            dict: {sku_id_1: count, sku_id_2: count}
            set: {sku_id, sku_id}
            """
            # 创建redis连接对象
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()
            # 调用hash hincrby()  如果要添加的sku_id不存在,就是新增,存在会将对应的count取出和本次的count累加再存储
            pl.hincrby('carts_%s' % user.id, sku_id, count)
            # 判断当前商品是否勾选
            if selected:
                # 将勾选商品的id添加到set集合
                pl.sadd('selected_%s' % user.id, sku_id)
            pl.execute()


        else:
            # 未登录用户存储购物车数据到cookie
            """
            {
                'sku_id_1': {'count': 1, 'selected': True},
                'sku_id_2': {'count': 1, 'selected': False},

            }
            """
            # 先获取cookie购物车数据
            cart_str = request.COOKIES.get('carts')
            # 判断是否获取到cookie购物车数据
            if cart_str:
                # 如果有cookie购物车数据,将str ---> dict
                cart_str_bytes = cart_str.encode()  # str ---> b'str'
                cart_str_bytes_un = base64.b64decode(cart_str_bytes)  # b'str' --> b'uncode'
                cart_dict = pickle.loads(cart_str_bytes_un)  # b'uncode' --> dict
                # pickle.loads(base64.b64decode(cart_str.encode()))
                # 判断本次要添加的商品在原本的购物车中是否已存在,如果存在就做count增量
                if sku_id in cart_dict:
                    origin_count = cart_dict[sku_id]['count']
                    count += origin_count
            else:
                # 如果没有cookie购物车数据就定义一个字典
                cart_dict = {}
            # 增加/修改新的商品
            cart_dict[sku_id] = {'count': count, 'selected': selected}
            # 将cookie dict ---> str
            cart_str = base64.b64encode(pickle.dumps(cart_dict)).decode()
            # 设置cookie
            response.set_cookie('carts', cart_str)

        # 响应
        return response

    def get(self, request):
        """展示购物车数据"""
        # 获取user
        user = request.user
        # 判断用户是否登录
        if user.is_authenticated:
            # 把登录redis购物车数据获取出来后,转换成和cookie购物车数据格式一样的大字典'
            """
            {
                'sku_id_1': {'count': 1, 'selected': True},
                'sku_id_2': {'count': 1, 'selected': False},
            }

            hash: {sku_id_1: 1, sku_id_2: 1}
            set: {sku_id}
            """
            # 1. 创建redis连接对象
            redis_conn = get_redis_connection('carts')
            # 2.获取hash和set数据
            redis_carts = redis_conn.hgetall('carts_%s' % user.id)
            selected_ids = redis_conn.smembers('selected_%s' % user.id)
            # 3. 定义一个字典包装购物车数据
            cart_dict = {}
            # 4. 遍历hash数据
            for sku_id_bytes in redis_carts:
                cart_dict[int(sku_id_bytes)] = {
                    'count': int(redis_carts[sku_id_bytes]),
                    'selected': sku_id_bytes in selected_ids
                }

        else:
            # 未登录用户,获取cookie购物车数据 str ---> dict
            cart_str = request.COOKIES.get('carts')
            if cart_str:
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                # 如果没有cookie购物车数据就响应一个空的购物车界面
                return render(request, 'cart.html')

        # 根据sku_id查询sku模型
        sku_qs = SKU.objects.filter(id__in=cart_dict.keys())
        sku_list = []  # 包装sku字典
        # 包装模板渲染数据
        for sku in sku_qs:
            count = cart_dict[sku.id]['count']
            sku_list.append({
                'id': sku.id,
                'name': sku.name,
                'price': str(sku.price),  # 为了让js中能正常解析
                'default_image_url': sku.default_image.url,
                'selected': str(cart_dict[sku.id]['selected']),  # 为了js判断  true false
                'count': count,
                'amount': str(sku.price * count)  # 为了让js中能正常解析
            })

        context = {
            'cart_skus': sku_list
        }
        return render(request, 'cart.html', context)

    def put(self, request):
        """购物车修改"""

        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected')

        try:
            sku = SKU.objects.get(id=sku_id, is_launched=True)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('sku_id不存在')
        try:
            count = int(count)
        except Exception as e:
            logger.error(e)
            return http.HttpResponseForbidden('参数类型有误')

        if isinstance(selected, bool) is False:
            return http.HttpResponseForbidden('参数类型有误')

        # 包装修改后的sku数据
        sku_dict = {
            'id': sku.id,
            'name': sku.name,
            'price': sku.price,
            'default_image_url': sku.default_image.url,
            'count': count,
            'selected': selected,
            'amount': sku.price * count
        }
        response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'cart_sku': sku_dict})

        user = request.user
        if user.is_authenticated:
            # 登录用户修改redis
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()
            # 修改hash中的数据 直接覆盖旧数据
            pl.hset('carts_%s' % user.id, sku_id, count)
            if selected:
                pl.sadd('selected_%s' % user.id, sku_id)
            else:
                pl.srem('selected_%s' % user.id, sku_id)
            pl.execute()
        else:
            # 未登录用户修改cookie
            cart_str = request.COOKIES.get('carts')
            if cart_str:
                # str --> dict
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))

            else:
                # 如果没有获取到cookie购物车数据
                return http.HttpResponseForbidden('数据异常')
            # 直接修改
            cart_dict[sku_id] = {'count': count, 'selected': selected}
            # dict --> str
            cart_str = base64.b64encode(pickle.dumps(cart_dict)).decode()
            response.set_cookie('carts', cart_str)
        return response

    def delete(self, request):
        """购物车删除"""
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')

        try:
            sku = SKU.objects.get(id=sku_id, is_launched=True)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('sku_id不存在')

        response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})

        user = request.user
        if user.is_authenticated:
            # 删除redis购物车数据
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()
            pl.hdel('carts_%s' % user.id, sku_id)
            pl.srem('selected_%s' % user.id, sku_id)
            pl.execute()

        else:
            # 删除cookie购物车数据
            cart_str = request.COOKIES.get('carts')
            if cart_str:
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                return http.HttpResponseForbidden('数据异常')

            # 判断当前要删除的sku_id在字典中是否存在
            if sku_id in cart_dict:
                del cart_dict[sku_id]

            if not cart_dict:  # 如果cookie购物车已经删空
                response.delete_cookie('carts')
                return response

            cart_str = base64.b64encode(pickle.dumps(cart_dict)).decode()
            response.set_cookie('carts', cart_str)

        return response


class CartSelectedAllView(View):
    """全选/取消全选"""

    def put(self, request):
        # 1. 接收
        json_dict = json.loads(request.body.decode())
        selected = json_dict.get('selected')
        # 2. 校验
        if isinstance(selected, bool) is False:
            return http.HttpResponseForbidden('参数类型有误')

        response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})
        user = request.user
        if user.is_authenticated:
            # 登录用户修改redis
            redis_conn = get_redis_connection('carts')
            if selected:  # 全选
                # 将hash获取出来,并将hash中的所有sku_id,并添加到set中
                # redis_carts = redis_conn.hgetall('carts_%s' % user.id)
                # sku_ids = redis_carts.keys()
                sku_ids = redis_conn.hkeys('carts_%s' % user.id)
                redis_conn.sadd('selected_%s' % user.id, *sku_ids)
            else:
                # 取消全选,将当前往用户的set集合直接删除
                redis_conn.delete('selected_%s' % user.id)


        else:
            # cookie购物车数据
            cart_str = request.COOKIES.get('carts')
            if cart_str:
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                return http.HttpResponseForbidden('数据异常')

            # 遍历cookie大字典,将里面的每个小字典中的selected修改
            for sku_dict in cart_dict.values():
                sku_dict['selected'] = selected

            cart_str = base64.b64encode(pickle.dumps(cart_dict)).decode()
            response.set_cookie('carts', cart_str)

        return response


class CartSimpleView(View):
    """展示简单版购物车数据"""

    def get(self, request):
        # 获取user
        user = request.user
        # 判断用户是否登录
        if user.is_authenticated:
            # 把登录redis购物车数据获取出来后,转换成和cookie购物车数据格式一样的大字典'
            """
            {
                'sku_id_1': {'count': 1, 'selected': True},
                'sku_id_2': {'count': 1, 'selected': False},
            }

            hash: {sku_id_1: 1, sku_id_2: 1}
            set: {sku_id}
            """
            # 1. 创建redis连接对象
            redis_conn = get_redis_connection('carts')
            # 2.获取hash和set数据
            redis_carts = redis_conn.hgetall('carts_%s' % user.id)
            selected_ids = redis_conn.smembers('selected_%s' % user.id)
            # 3. 定义一个字典包装购物车数据
            cart_dict = {}
            # 4. 遍历hash数据
            for sku_id_bytes in redis_carts:
                cart_dict[int(sku_id_bytes)] = {
                    'count': int(redis_carts[sku_id_bytes]),
                    'selected': sku_id_bytes in selected_ids
                }

        else:
            # 未登录用户,获取cookie购物车数据 str ---> dict
            cart_str = request.COOKIES.get('carts')
            if cart_str:
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                # 如果没有cookie购物车数据就响应一个空的购物车界面
                return http.JsonResponse({'code': RETCODE.NODATAERR, 'errmsg': '没有购物车数据'})

        # 根据sku_id查询sku模型
        sku_qs = SKU.objects.filter(id__in=cart_dict.keys())
        sku_list = []  # 包装sku字典
        # 包装模板渲染数据
        for sku in sku_qs:
            count = cart_dict[sku.id]['count']
            sku_list.append({
                'id': sku.id,
                'name': sku.name,
                'default_image_url': sku.default_image.url,
                'count': count,
            })

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'cart_skus': sku_list})