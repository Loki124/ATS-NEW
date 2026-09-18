"""码表库 (G46) 路由：/api/v1/code-tables/"""
from rest_framework.routers import DefaultRouter

from .views import (
    CountryViewSet,
    EthnicityViewSet,
    LanguageViewSet,
    RegionViewSet,
    BusinessCodeViewSet,
)

router = DefaultRouter()
router.register(r'regions', RegionViewSet, basename='code-region')
router.register(r'countries', CountryViewSet, basename='code-country')
router.register(r'ethnicities', EthnicityViewSet, basename='code-ethnicity')
router.register(r'languages', LanguageViewSet, basename='code-language')
router.register(r'business', BusinessCodeViewSet, basename='code-business')

urlpatterns = router.urls
