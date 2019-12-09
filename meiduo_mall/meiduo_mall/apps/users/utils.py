from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadData
from django.conf import settings
from .models import User


def generate_email_verify_url(user):
    """
    生成邮箱激活url
    :param user: 那个用户要生成激活url
    :return: 邮箱激活url
    """
    # 创建加密实例对象
    serializer = Serializer(secret_key=settings.SECRET_KEY, expires_in=3600)
    # 包装要加密的字典数据
    data = {'user_id': user.id, 'email': user.email}
    # loads方法加密,并把byte型数据转为str
    token = serializer.dumps(data).decode()
    # 拼接激活url
    verify_url = settings.EMAIL_VERIFY_URL + '?token=' + token  # EMAIL_VERIFY_URL 为自己设置的拼接
    # 返回拼接后的地址
    return verify_url


def get_user_token(token):
    """
    对token进行解密,并查询出对应的user
    :param token: 要解密的用户数据
    :return: user or None
    """
    # 创建解密实例对象
    serializer = Serializer(secret_key=settings.SECRET_KEY, expires_in=3600)
    try:
        # 解密
        data = serializer.loads(token)
    except BadData:
        return None
    else:
        user_id = data.get('user_id')
        email = data.get('email')
        try:
            user = User.objects.get(id=user_id, email=email)
            return user
        except User.DoesNotExist:
            return None

