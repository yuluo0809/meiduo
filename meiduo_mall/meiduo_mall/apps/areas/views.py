from django.shortcuts import render
from django.views import View
from django.http import *
from django.core.cache import cache

from .models import Area
from meiduo_mall.utils.response_code import RETCODE


class AreaView(View):
    """省市区查询"""

    def get(self, request):
        # 1. 获取area_id查询参数
        area_id = request.GET.get('area_id')
        # 2. 判断是否有area_id 如果没有说明查询所有省数据
        if area_id is None:
            # 先尝试去缓存中查询所有省数据
            province_list = cache.get('province_list')
            if province_list is None:
                province_qs = Area.objects.filter(parent=None)  # 获取所有省
                # 模型转字典: 序列化输出
                province_list = []
                for province in province_qs:
                    province_list.append(
                        {
                            'id': province.id,
                            'name': province.name
                        }
                    )
                cache.set('province_list', province_list, 3600)
            return JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'province_list': province_list})
        else:
            data_dict = cache.get('data_dict_' + area_id)  # 读取市或区缓存数据
            if data_dict is None:  # 去mysql查询市或区数据
                try:
                    # 如果有area_id查询area_id指定的下级所有行政区
                    parent_model = Area.objects.get(id=area_id)  # 查询市或区的父级 parent_model查的是省下面的行政区
                    # 查询area_id对待行政区的下级所有行政区
                    sub_qs = parent_model.subs.all()  # 查询市或区的下级  sub_qs查的是行政区下面地级区
                except Area.DoesNotExist:
                    return HttpResponseForbidden('area_id不存在')

                # 将sub_qs查询中的模型转字典
                sub_list = []
                for sub in sub_qs:
                    sub_list.append(
                        {
                            'id': sub.id,
                            'name': sub.name
                        }
                    )
                # 包装行政区及下级行政区数据, 把指定的某个行政区及下面所有地级区展示出来
                data_dict = {
                    'id': parent_model.id,
                    'name': parent_model.name,
                    'subs': sub_list
                }
                cache.set('data_dict_' + area_id, data_dict, 3600)   # 储存市或区缓存数据
            return JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'sub_data': data_dict})


