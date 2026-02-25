from django.urls import path
from . import views
from . import permissions_views
from Api.views import intrast_page

urlpatterns = [
    path('', views.login_view, name='root'),
    path('login/', views.login_view, name='login'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    
    # Role-specific dashboards
    path('dashboard/buyer/', views.buyer_dashboard_view, name='buyer_dashboard'),
    path('dashboard/seller/', views.seller_dashboard_view, name='seller_dashboard'),
    path('dashboard/transporter/', views.transporter_dashboard_view, name='transporter_dashboard'),
    path('dashboard/both_sellerandbuyer/', views.both_sellerandbuyer_dashboard_view, name='both_sellerandbuyer_dashboard'),
    
    # User Management
    path('users/', views.user_list_view, name='user_list'),
    path('tags/', views.tag_master_view, name='tag_master'),
    path('users/create/', views.user_create_view, name='user_create'),
    path('users/<int:user_id>/edit/', views.user_update_view, name='user_update'),
    path('users/<int:user_id>/delete/', views.user_delete_view, name='user_delete'),
    
    # Category Management
    path('categories/', views.category_list_view, name='category_list'),
    path('api/categories/create/', views.category_create_ajax, name='category_create_ajax'),
    path('api/categories/<int:category_id>/', views.category_get_ajax, name='category_get_ajax'),
    path('api/categories/<int:category_id>/update/', views.category_update_ajax, name='category_update_ajax'),
    path('api/categories/<int:category_id>/delete/', views.category_delete_ajax, name='category_delete_ajax'),
    path('api/categories/tree/', views.category_tree_ajax, name='category_tree_ajax'),
    path('api/categories/<int:parent_id>/children/', views.category_children_ajax, name='category_children_ajax'),
    path('api/categories/<int:category_id>/path/', views.category_path_ajax, name='category_path_ajax'),
    path('api/categories/search/', views.category_search_ajax, name='category_search_ajax'),
    
    # SubCategory Management
    path('subcategories/', views.subcategory_list_view, name='subcategory_list'),
    path('api/subcategories/create/', views.subcategory_create_ajax, name='subcategory_create_ajax'),
    path('api/subcategories/<int:subcategory_id>/', views.subcategory_get_ajax, name='subcategory_get_ajax'),
    path('api/subcategories/<int:subcategory_id>/update/', views.subcategory_update_ajax, name='subcategory_update_ajax'),
    path('api/subcategories/<int:subcategory_id>/delete/', views.subcategory_delete_ajax, name='subcategory_delete_ajax'),

    # Brand Management
    path('brands/', views.brand_list_view, name='brand_list'),
    path('api/brands/create/', views.brand_create_ajax, name='brand_create_ajax'),
    path('api/brands/<int:brand_id>/', views.brand_get_ajax, name='brand_get_ajax'),
    path('api/brands/<int:brand_id>/update/', views.brand_update_ajax, name='brand_update_ajax'),
    path('api/brands/<int:brand_id>/delete/', views.brand_delete_ajax, name='brand_delete_ajax'),
    
    # Product Management
    path('offers/', views.product_list_view, name='product_list'),
    path('offers/add/', views.product_create_view, name='product_create'),
    path('api/offers/create/', views.product_create_ajax, name='product_create_ajax'),
    path('api/offers/<int:product_id>/', views.product_get_ajax, name='product_get_ajax'),
    path('api/offers/<int:product_id>/update/', views.product_update_ajax, name='product_update_ajax'),
    path('api/offers/<int:product_id>/delete/', views.product_delete_ajax, name='product_delete_ajax'),
    path('api/offers/<int:product_id>/toggle/', views.product_toggle_ajax, name='product_toggle_ajax'),
    path('api/offers/<int:product_id>/update-stock/', views.product_update_stock_ajax, name='product_update_stock_ajax'),
    
    # Interest/Offer Management
    path('api/products/<int:product_id>/show-interest/', views.product_show_interest_ajax, name='product_show_interest_ajax'),
    path('api/products/<int:product_id>/toggle-interest/', views.product_toggle_interest_ajax, name='product_toggle_interest_ajax'),
    path('api/products/<int:product_id>/interests/', views.product_interests_ajax, name='product_interests_ajax'),
    path('api/products/<int:product_id>/approve/', views.product_accept_buyer_ajax, name='product_accept_buyer_ajax'),
    path('api/products/<int:product_id>/reject/', views.product_reject_buyer_ajax, name='product_reject_buyer_ajax'),
    path('api/products/<int:product_id>/confirm-deal/', views.product_confirm_deal_ajax, name='product_confirm_deal_ajax'),
    path('api/products/<int:product_id>/buyer-confirm/', views.product_buyer_confirm_ajax, name='product_buyer_confirm_ajax'),
    path('api/offers/list/', views.offers_list_ajax, name='offers_list_ajax'),
    
    # Contracts
    path('api/contracts/list/', views.contracts_list_ajax, name='contracts_list_ajax'),
    path('api/contracts/<int:contract_id>/', views.contract_detail_ajax, name='contract_detail_ajax'),
    path('api/contracts/<int:contract_id>/update/', views.contract_update_ajax, name='contract_update_ajax'),
    path('api/contracts/export/', views.contracts_export_csv, name='contracts_export_csv'),

    # Product Image Management
    path('product-images/', views.product_image_list_view, name='product_image_list'),
    path('api/product-images/create/', views.product_image_create_ajax, name='product_image_create_ajax'),
    path('api/product-images/<int:image_id>/', views.product_image_get_ajax, name='product_image_get_ajax'),
    path('api/product-images/<int:image_id>/delete/', views.product_image_delete_ajax, name='product_image_delete_ajax'),
    
    # User AJAX endpoints
    path('api/users/<int:user_id>/', views.get_user_data, name='get_user_data'),
    path('api/users/create/', views.user_create_ajax, name='user_create_ajax'),
    path('api/users/<int:user_id>/update/', views.user_update_ajax, name='user_update_ajax'),
    path('api/users/<int:user_id>/delete/', views.user_delete_ajax, name='user_delete_ajax'),
    
    # Permissions Management
    path('permissions/', permissions_views.role_permissions_view, name='role_permissions'),
    path('api/permissions/matrix/', permissions_views.permissions_matrix_view, name='permissions_matrix'),
    path('api/permissions/update/', permissions_views.update_permission, name='update_permission'),

    # Branch Master
    path('dashboard/branch-master/', views.branch_master_view, name='branch_master'),

    # Location APIs
    path('api/location/states/', views.location_states_ajax, name='location_states_ajax'),
    path('api/location/cities/', views.location_cities_ajax, name='location_cities_ajax'),
    path('api/location/areas/', views.location_areas_ajax, name='location_areas_ajax'),

    # Branch APIs
    path('api/branch/create/', views.branch_create_ajax, name='branch_create_ajax'),
    path('api/branch/update/<int:branch_id>/', views.branch_update_ajax, name='branch_update_ajax'),
    path('api/branch/toggle/<int:branch_id>/', views.branch_toggle_status_ajax, name='branch_toggle_status_ajax'),
    path('api/branch/delete/<int:branch_id>/', views.branch_delete_ajax, name='branch_delete_ajax'),
    
    # Intrast/Offers Page
    path('contracts/', intrast_page, name='intrast_page'),
]