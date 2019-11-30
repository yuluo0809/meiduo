from django.shortcuts import render
from django.views import View
from django import http
from django.core.paginator import Paginator, EmptyPage
from django.utils import timezone

from contents.utils import get_categories
from .models import GoodsCategory, SKU, GoodsVisitCount
from .utils import get_breadcrumb
import logging
from meiduo_mall.utils.response_code import RETCODE


logger = logging.getLogger('django')

class ListView(View):
    """商品列表界面"""
    def get(self, request, category_id, page_num):

        try:
            cat3 = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return http.HttpResponseForbidden('category_id不存在')
        # 获取查询参数
        sort = request.GET.get('sort', 'default')
        if sort == 'hot':
            sort_field = 'sales'
        elif sort == 'price':
            sort_field = '-price'
        else:
            sort = 'default'
            sort_field = '-create_time'
        # 把当前三级类型下的所有sku拿到
        sku_qs = cat3.sku_set.filter(is_launched=True).order_by(sort_field)
        # 创建分页器对象Paginator(要分页的所有数据, 每页显示多少条数据)
        paginator = Paginator(sku_qs, 5)
        # 获取总页数
        total_page = paginator.num_pages
        # 获取指定页的数据
        try:
            page_skus = paginator.page(page_num)
        except EmptyPage as e:

            logger.error(e)
            return http.HttpResponseForbidden('没得玩了')
        # page = 5  # 每页显示5条
        # # sku_qs[0:5]  # 1页 [(page_num - 1) * page: page_num * page]
        # # sku_qs[5:10]  # 2页
        # # sku_qs[10:15]  # 3页
        # page_num = int(page_num)
        # page_skus = sku_qs[(page_num - 1) * page: page_num * page]
        # total_page = sku_qs.count() // page + 1 if sku_qs.count() % page else 0

        # 包装面包屑导航数据
        # breadcrumb = {}
        # breadcrumb['cat3'] = cat3
        # breadcrumb['cat2'] = cat3.parent
        # cat1 = cat3.parent.parent
        # cat1.url = cat1.goodschannel_set.all()[0].url
        # breadcrumb['cat1'] = cat1

        context = {
            'categories': get_categories(),  # 商品类别数据
            'breadcrumb': get_breadcrumb(cat3),  # 面包屑导航数据
            'category': cat3,  # 三级类别模型对象
            'sort': sort,  # 排序字段
            'page_skus': page_skus,  # 指定页的sku数据
            'page_num': page_num,  # 当前显示的是第几页
            'total_page': total_page,  # 总页数
        }
        return render(request, 'list.html', context)



class HotGoodsView(View):
    """热销排行"""
    def get(self, request, category_id):

        # 1. 校验
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return http.HttpResponseForbidden('category_id不存在')
        # 2. 查询当前三级类型下销量最好的前两个sku
        sku_qs = category.sku_set.filter(is_launched=True).order_by('-sales')[0:2]

        sku_list = []  # 包装sku字典
        # 模型转字典
        for sku in sku_qs:
            sku_list.append({
                'id': sku.id,
                'name': sku.name,
                'default_image_url': sku.default_image.url,
                'price': sku.price
            })
        # 响应
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'hot_skus': sku_list})


class DetailView(View):
    """商品详情界面"""
    def get(self, request, sku_id):
        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return render(request, '404.html')

        category = sku.category  # 获取当前sku所对应的三级分类

        # 查询当前sku所对应的spu
        spu = sku.spu

        """1.准备当前商品的规格选项列表 [8, 11]"""
        # 获取出当前正显示的sku商品的规格选项id列表
        current_sku_spec_qs = sku.specs.order_by('spec_id')
        current_sku_option_ids = []  # [8, 11]
        for current_sku_spec in current_sku_spec_qs:
            current_sku_option_ids.append(current_sku_spec.option_id)

        """2.构造规格选择仓库
        {(8, 11): 3, (8, 12): 4, (9, 11): 5, (9, 12): 6, (10, 11): 7, (10, 12): 8}
        """
        # 构造规格选择仓库
        temp_sku_qs = spu.sku_set.all()  # 获取当前spu下的所有sku
        # 选项仓库大字典
        spec_sku_map = {}  # {(8, 11): 3, (8, 12): 4, (9, 11): 5, (9, 12): 6, (10, 11): 7, (10, 12): 8}
        for temp_sku in temp_sku_qs:
            # 查询每一个sku的规格数据
            temp_spec_qs = temp_sku.specs.order_by('spec_id')
            temp_sku_option_ids = []  # 用来包装每个sku的选项值
            for temp_spec in temp_spec_qs:
                temp_sku_option_ids.append(temp_spec.option_id)
            spec_sku_map[tuple(temp_sku_option_ids)] = temp_sku.id

        """3.组合 并找到sku_id 绑定"""
        spu_spec_qs = spu.specs.order_by('id')  # 获取当前spu中的所有规格

        for index, spec in enumerate(spu_spec_qs):  # 遍历当前所有的规格
            spec_option_qs = spec.options.all()  # 获取当前规格中的所有选项
            temp_option_ids = current_sku_option_ids[:]  # 复制一个新的当前显示商品的规格选项列表
            for option in spec_option_qs:  # 遍历当前规格下的所有选项
                temp_option_ids[index] = option.id  # [8, 12]
                option.sku_id = spec_sku_map.get(tuple(temp_option_ids))  # 给每个选项对象绑定下他sku_id属性

            spec.spec_options = spec_option_qs  # 把规格下的所有选项绑定到规格对象的spec_options属性上

        context = {
            'categories': get_categories(),  # 商品分类
            'breadcrumb': get_breadcrumb(category),  # 面包屑导航
            'sku': sku,  # 当前要显示的sku模型对象
            'category': category,  # 当前的显示sku所属的三级类别
            'spu': spu,  # sku所属的spu
            'spec_qs': spu_spec_qs,  # 当前商品的所有规格数据
        }
        return render(request, 'detail.html', context)


class GoodsVisitView(View):
    """统计三级类别每日访问类"""
    def post(self, request, category_id):


        # 1. 校验
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return http.HttpResponseForbidden('category_id不存在')

        # date = timezone.localdate()  # 获取当前日期
        # date = timezone.localtime()  # 获取当前时间
        date = timezone.now()  # 获取日期时间
        # 2.查询当前三级类型今日是否访问过
        try:
            goods_visit = GoodsVisitCount.objects.get(date=date, category_id=category_id)
        except GoodsVisitCount.DoesNotExist:
            # 如果没有访问过就新增一条访问记录保存
            goods_visit = GoodsVisitCount(
                category=category
            )

        # 如果今日已经访问过,就修改count
        goods_visit.count += 1
        goods_visit.save()
        # 响应
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})