# 编写异步/耗时任务代码
from meiduo_mall.libs.yuntongxun.sms import CCP
from celery_tasks.main import celery_app


# from celery_tasks.sms.yuntongxun.sms import CCP

@celery_app.task(name='send_sms_code')  # 只有用此装饰器装饰过的函数celery才能识别
def send_sms_code(mobile, sms_code):
    """
    发短信的异步任务
    :param mobile: 要收短信的手机号
    :param sms_code: 验证码
    """
    CCP().send_template_sms(mobile, [sms_code, 5], 1)
