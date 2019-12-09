

def get_breadcrumb(cat3):
    """包装面包屑导航数据"""

    # 包装面包屑导航数据
    breadcrumb = {}
    breadcrumb['cat3'] = cat3
    breadcrumb['cat2'] = cat3.parent
    cat1 = cat3.parent.parent
    cat1.url = cat1.goodschannel_set.all()[0].url
    breadcrumb['cat1'] = cat1

    return breadcrumb