from goods.models import GoodsChannel


def get_categories():
    """包装商品类别数据"""
    # 定义一个用来包装所有商品类别数据大字典
    categories = {}
    # 查询商品频道表中的所有数据
    goods_channel_qs = GoodsChannel.objects.order_by('group_id', 'sequence')
    # 遍历goods_channel_qs 查询集
    for channel_model in goods_channel_qs:
        # 获取当前组号
        group_id = channel_model.group_id
        # 当组号key在大字典中不存在时,再去初始化
        if group_id not in categories:
            # 准备每一组的初始数据格式
            categories[group_id] = {'channels': [], 'sub_cats': []}

        # 获取当前频道中的一级类别
        cat1 = channel_model.category
        # 将频道中的url 赋值给cat1
        cat1.url = channel_model.url
        # 将cat1 添加到当前组中的 channels 键对应的列表中
        group_data = categories[group_id]  # 获取当前组中所有数据
        cat1_list = group_data['channels']  # 获取当前组中用来包装所有cat1列表
        cat1_list.append(cat1)

        # 查询出当前一级下的所有二级
        cat2_qs = cat1.subs.all()
        # 遍历cat2_qs 查询集,给每个二级模型对象,多定义一个sub_cats属性用于记录它下面的所有三级
        for cat2 in cat2_qs:
            # 查询二级下的所有三级
            cat3_qs = cat2.subs.all()
            # 将二级下的所有三级保存到cat2属性上
            cat2.sub_cats = cat3_qs
            # 将保存好三级的每一个一个的二级添加到列表中
            group_data['sub_cats'].append(cat2)

    return categories