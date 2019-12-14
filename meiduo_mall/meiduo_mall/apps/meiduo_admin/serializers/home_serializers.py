from goods.models import GoodsVisitCount
from rest_framework import serializers


class GoodsVisitCountModelSerializer(serializers.ModelSerializer):
    # 模型类序列化器自动映射的外键字段类型
    # category = serializers.PrimaryKeyRelatedField() # 序列化的结果是主表的主键

    # 手动映射外键关联字段 -- 覆盖模型类自动映射
    category = serializers.StringRelatedField()

    class Meta:
        model = GoodsVisitCount
        fields = ['category', 'count']