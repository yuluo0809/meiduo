# 此文件中编写celery客户端代码
from celery import Celery
import os
# celery模块中尽可能不要导入celery模块以外的其它模块,可能会出现未知bug
# 解决: 1.要么变为一家 2. 加上下面这行代码再重新启动celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meiduo_mall.settings.developing")

# 1. 创建celery客户端对象
celery_app = Celery('meiduo')

# 2. 加载celery配置信息(仓库/消息队列是谁?在哪里?)
celery_app.config_from_object('celery_tasks.config')

# 3. celery可以生产什么任务
celery_app.autodiscover_tasks(['celery_tasks.sms', 'celery_tasks.email'])