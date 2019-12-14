from rest_framework import serializers
from goods.models import SKU, SKUSpecification


class SKUSpecModelSerializer(serializers.ModelSerializer):
    spec_id = serializers.IntegerField()
    option_id = serializers.IntegerField()

    class Meta:
        model = SKUSpecification
        fields = [
            'spec_id',
            'option_id'
        ]


class SkuModelSerializer(serializers.ModelSerializer):
    spu = serializers.CharField()
    spu_id = serializers.IntegerField()
    category = serializers.CharField()
    category_id = serializers.IntegerField()

    specs = SKUSpecModelSerializer(many=True)

    class Meta:
        model = SKU
        fields = "__all__"

    def create(self, validated_data):
        specs = validated_data
