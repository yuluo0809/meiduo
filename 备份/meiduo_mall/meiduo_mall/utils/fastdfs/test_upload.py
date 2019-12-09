from fdfs_client.client import Fdfs_client

# 1.创建客户端(指定配置文件)
client = Fdfs_client('./client.conf')
# 2. 上传
ret = client.upload_by_filename(r'C:\Users\Windows\Pictures\Saved Pictures\timg.jpg')

print(ret)

# {'Group name': 'group1',
#  'Remote file_id': 'group1/M00/00/00/wKhn0l3eJXuAAhxlAAC4j90Tziw66.jpeg',
#  'Status': 'Upload successed.',
#  'Local file name': '/Users/chao/Desktop/01.jpeg',
#  'Uploaded size': '46.00KB',
#  'Storage IP': '192.168.103.210'}

# http://192.168.103.210:8888
