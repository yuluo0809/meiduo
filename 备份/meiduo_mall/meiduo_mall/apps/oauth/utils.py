from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadData
from django.conf import settings



def generate_open_id_signature(openid):
    """
    对原始openid进行加密
    :param openid: 原始openid
    :return: 加密后的openid
    """
    # 1. 创建Serializer 实例对象 (密钥, 过期时间:秒)
    serializer = Serializer(secret_key=settings.SECRET_KEY, expires_in=600)

    # 2. 调用加密实例对象中dumps({})  返回bytes类型
    data = {'openid': openid}
    openid_sign = serializer.dumps(data) # 输出 序列化: 模型转字典

    # 3. 把bytes类型转换成str并返回
    return openid_sign.decode()


def check_open_id(openid_sign):
    """
    对原始openid进行解密
    :param openid_sign: 要解密的openid
    :return: 原始openid
    """
    # 1. 创建Serializer 实例对象 (密钥, 过期时间:秒)
    serializer = Serializer(secret_key=settings.SECRET_KEY, expires_in=600)

    # 2. 对象数据进行解密  loads(要解密)
    try:
        data = serializer.load(openid_sign) # 输入 反序列化: 字典转模型
        return data.get('openid')
    except BadData:
        return None