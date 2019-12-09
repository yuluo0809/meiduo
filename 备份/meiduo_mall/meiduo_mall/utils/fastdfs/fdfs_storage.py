from django.core.files.storage import Storage


class FastDFSStorage(Storage):
    """自定义文件存储类"""

    def _open(self, name, mode='rb'):
        """
        当要打开某个文件时,会自动调用此方法
        :param name: 打开文件名
        :param mode: 打开模式
        :return: 文件对象
        """
        pass

    def _save(self, name, content):
        """
        当上传图片时就会自动调用此方法
        :param name: 要上传的图片名
        :param content: 要上传的图片bytes类型数据
        :return: file_id
        """
        pass

    def exists(self, name):
        """
        当上传图片时会自动调用此方法判断图片是否存在
        :param name: 要判断的图片名
        :return: False 要上传  True 不上传
        """
        return False

    def url(self, name):
        """
        当要下载图片 当image.url时就会调用此方法
        :param name: file_id
        :return: 完整图片下载路径 'http://image.meiduo.site:8888/' + name
        """
        return 'http://image.meiduo.site:8888/' + name