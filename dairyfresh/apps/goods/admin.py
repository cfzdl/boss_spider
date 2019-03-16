from django.contrib import admin
from django.core.cache import cache
from goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner


# Register your models here.
class BaseModelAdmin(admin.ModelAdmin):

    def save_model(self, request, obj, form, change):

        super().save_model(request, obj, form, change)

        from celery_tasks.tasks import genegrate_static_index_html
        genegrate_static_index_html.delay()

        cache.delete('index_page_data')

    def delete_model(self, request, obj):
        super().delete_model(request,obj)

        from celery_tasks.tasks import genegrate_static_index_html
        genegrate_static_index_html.delay()
        cache.delete('index_page_data')

class IndexPromotionBannerAdmin(BaseModelAdmin):
    pass

class GoodsTypeAdmin(BaseModelAdmin):
    pass

class IndexGoodsBannerAdmin(BaseModelAdmin):
    pass

class IndexTypeGoodsBannerAdmin(BaseModelAdmin):
    pass



admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin)
admin.site.register(GoodsType, GoodsTypeAdmin)
admin.site.register(IndexGoodsBanner, IndexGoodsBannerAdmin)
admin.site.register(IndexTypeGoodsBanner,IndexTypeGoodsBannerAdmin)