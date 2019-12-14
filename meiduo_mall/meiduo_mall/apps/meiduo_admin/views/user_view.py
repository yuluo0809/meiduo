from rest_framework.generics import ListAPIView, CreateAPIView
from users.models import User

from meiduo_admin.serializers.user_serializers import UserModelSerializer
from meiduo_admin.paginations import UserPageNum


class UserListCreateView(ListAPIView, CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserModelSerializer

    pagination_class = UserPageNum

    def get_queryset(self):
        keyword = self.request.query_params.get('keyword')

        if keyword:
            return self.queryset.filter(username__contains=keyword, is_staff=True).order_by('id')

        return self.queryset.filter(is_staff=True).order_by('id')
