from rest_framework.viewsets import ModelViewSet

from goods.models import *
from meiduo_admin.serializers.sku_serializers import *
from meiduo_admin.paginations import UserPageNum


class SKUViewSet(ModelViewSet):
    queryset = SKU.objects.all()
    serializer_class = SkuModelSerializer
    pagination_class = UserPageNum

    def get_queryset(self):
        keyword = self.request.query_params.get('keyword')
        if keyword:
            return self.queryset.filter(name__contains=keyword).order_by('id')
        return self.queryset.all().order_by("id")
