from django.urls import path
from .views import *
from rest_framework.routers import DefaultRouter

urlpatterns = [
    path('register/', registration_page, name='registration_page'),
    path('forgotpassword/', forgotpassword_page, name='forgotpassword_page'),
    path('kyc/', kyc_dashboard_page, name='kyc_dashboard_page'),
    path('intrast/', intrast_page, name='intrast_page_list'),  # ✅ YEH IMPORTANT HAI - template render karega
    path('product-video-list/', product_video_list_page, name='product_video_list'),

    path('auth/register/', register_api, name='api_register'),
    path('auth/login/', login_api, name='api_login'),
    path('auth/forgot-password/', forgot_password_api, name='api_forgot_password'),
    path('auth/change-password/', change_password_api, name='api_change_password'),
    path('auth/session-token/', session_token_api, name='api_session_token'),
    path('adduser/', add_user_api, name='api_add_user'),
    path('user/', current_user, name='api_current_user'),
    path('user/profile-image/', upload_profile_image_api, name='api_upload_profile_image'),
    path('profile/update/', profile_update_api, name='api_profile_update'),
    path('kyc/<int:user_id>/approve/', kyc_approve_api, name='api_kyc_approve'),
    path('kyc/<int:user_id>/reject/', kyc_reject_api, name='api_kyc_reject'),
    path('admin/tag/create/', admin_tag_create_api, name='api_admin_tag_create'),
    path('admin/tag/list/', admin_tag_list_api, name='api_admin_tag_list'),
    path('admin/tag/<int:tag_id>/update/', admin_tag_update_api, name='api_admin_tag_update'),
    path('admin/tag/<int:tag_id>/delete/', admin_tag_delete_api, name='api_admin_tag_delete'),
    path('products/filter/', product_filter_api, name='api_products_filter'),
    path('filter/', universal_filter_api, name='api_universal_filter'),
    path('admin/dashboard/', admin_dashboard_api, name='api_admin_dashboard'),
    path('buyer/dashboard/', buyer_dashboard_api, name='buyer_dashboard_api'),
    path('test-product/<int:product_id>/', test_product_api, name='test_product_api'),
]

router = DefaultRouter()
router.register(r'token', TokenViewSet, basename='token')
router.register(r'users', UserViewSet, basename='api-users')
router.register(r'categories', CategoryViewSet, basename='api-categories')
router.register(r'products', ProductViewSet, basename='api-products')
router.register(r'product-images', ProductImageViewSet, basename='api-product-images')
router.register(r'product-videos', ProductVideoViewSet, basename='api-product-videos')

urlpatterns += router.urls