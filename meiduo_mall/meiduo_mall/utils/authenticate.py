from django.contrib.auth.backends import ModelBackend
import re
from users.models import User
from django.db.models import Q


class MeiduoModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if request is None:
            try:
                user = User.objects.get(Q(username=username) | Q(mobile=username), is_staff=True)
            except:
                return None
            if user.check_password(password):
                return user
        else:
            try:
                user = User.objects.get(Q(username=username) | Q(mobile=username))
            except:
                return None
            if user.check_password(password):
                return user
