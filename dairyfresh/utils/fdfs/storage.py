from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client
from django.conf import settings

class FDFSStorage(Storage):
    '''fast dfs文件存储类'''
    def __init__(self, client_conf=None, base_url=None):
        '''初始化'''
        if client_conf is None:
            client_conf = settings.FDFS_CLIENT_CONF
        self.client_conf = client_conf

        if base_url is None:
            base_url = settings.FDFS_URL
        self.base_url = base_url

    def _open(self, name, mode='rb'):
        '''打开文件时使用'''
        pass


    def _save(self, name, content):
        '''保存文件时使用'''
        # name 选择文件的名字
        # content 包含上传文件内容的File对象

        #创建一个Fdfs_client对象
        client = Fdfs_client(self.client_conf)

        #上传文件到fast dfs系统中
        res = client.upload_by_buffer(content.read())

        if res.get('Status') != 'Upload successed.':
            #上传失败

            raise Exception('上传文件到FASTDFS失败')

        filename = res.get('Remote file_id')

        return filename

    def exists(self, name):

        return  False

    def url(self, name):

        return self.base_url+name

'''

'''


