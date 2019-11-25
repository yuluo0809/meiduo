from django.db import models


# 在自关联模型外键中related_name 必须修改在一的那方隐式生成的字段名,

class Area(models.Model):
    """省市区"""
    name = models.CharField(max_length=20, verbose_name='名称')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, related_name='subs', null=True, blank=True,
                               verbose_name='上级行政区')

    class Meta:
        db_table = 'tb_areas'
        verbose_name = '省市区'
        verbose_name_plural = '省市区'

    def __str__(self):
        return self.name


# 查询所有省的数据
# Area.objects.filter(parent__isnull=True)
# Area.objects.filter(parent=None)
# Area.objects.get(id=130000)  # 河北省
#
# # 查询指定省下面的所有市
# Area.objects.filter(parent_id=130000)  # 查询指定省下面的所有省 (parent_id=指定省的id)
# Area.objects.get(id=130100)  # 石家庄市
# hbs.sbus.all()
# sjz.parent
#
# # 查询指定市下面的所有区县
# Area.objects.filter(parent_id=130100)  # 查询指定市下面的所有区县(parent_id=指定市的id)
# baq.parent
# szs.subs.all()g