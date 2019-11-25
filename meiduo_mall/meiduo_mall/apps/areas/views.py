from django.shortcuts import render
from django.views import View
from django.http import *

from .models import Area
from meiduo_mall.utils.response_code import RETCODE

class AreaView(View):
    """省市区查询"""
    def get(self, request):
        # 1. 获取area_id查询参数
        area_id = request.GET.get('area_id')
        # 2. 判断是否有area_id 如果没有说明查询所有省数据
        if area_id is None:
            province_qs = Area.objects.filter(parent=None)
            # 模型转字典: 序列化输出
            province_list = []
            for province in province_qs:
                province_list.append(
                    {
                        'id': province.id,
                        'name': province.name
                    }
                )
                return JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'province_list': province_list})
        else:
            # 如果有area_id查询area_id指定的下级所有行政区

            pass