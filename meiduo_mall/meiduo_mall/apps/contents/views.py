from django.shortcuts import render
from django.views import View

from goods.models import GoodsCategory, GoodsChannel
from .utils import get_categories
from .models import ContentCategory, Content


class IndexView(View):
    """首页"""
    def get(self, request):


        # 定义字典变量用来包装所有广告数据
        contents = {}
        # 查询广告类别所有数据
        content_cat_qs = ContentCategory.objects.all()
        # 遍历广告类别模型
        for content_cat_model in content_cat_qs:
            contents[content_cat_model.key] = content_cat_model.content_set.filter(status=True).order_by('sequence')

        context = {
            'categories': get_categories(),  # 所有商品类别数据
            'contents': contents,  # 包装所有广告数据
        }
        return render(request, 'index.html', context)
