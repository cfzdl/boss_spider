# 定义索引类
from haystack import indexes
# 导入你的模型类
from goods.models import GoodsSKU


#指定对于某个类的某些数据建立索引
# 索引类名：模型类名 + Index
class GoodsSKUIndex(indexes.SearchIndex, indexes.Indexable):

    text = indexes.CharField(document=True, use_template=True)  # 索引字段    use_template指定根据哪些字段建立索引

    def get_model(self):
        # 返回你的模型类
        return GoodsSKU

    # 建立索引数据
    def index_queryset(self, using=None):
        return  self.get_model().objects.all()

