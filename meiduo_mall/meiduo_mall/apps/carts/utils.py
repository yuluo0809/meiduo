import pickle, base64
from django_redis import get_redis_connection


def merge_cart_cookie_to_redis(request, response):
    """购物车合并"""
    cart_str = request.COOKIES.get('carts')
    # 如果没有cookie购物车数据,什么也不做
    if cart_str is None:
        return
    # str ---> dict
    cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))

    user = request.user
    # 创建redis连接对象
    redis_conn = get_redis_connection('carts')
    for sku_id in cart_dict:
        # 将cookie中的sku_id和count向redis的hash中存储
        redis_conn.hset('carts_%s' % user.id, sku_id, cart_dict[sku_id]['count'])
        if cart_dict[sku_id]['selected']:  # 如果cookie中当前商品是勾选
            redis_conn.sadd('selected_%s' % user.id, sku_id)
        else:
            redis_conn.srem('selected_%s' % user.id, sku_id)

    # 删除已合并的cookie购物车数据
    response.delete_cookie('carts')

