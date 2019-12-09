from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadData
from django.conf import settings


def get_account_token(token):
    serializer = Serializer(secret_key=settings.SECRET_KEY, expires_in=3600)
    try:
        data = serializer.loads(token)
    except BadData:
        return None
    else:
        return data
