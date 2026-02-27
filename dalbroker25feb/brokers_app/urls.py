from django.urls import path
from . views import *
from . import permissions_views
from Api.views import intrast_page

urlpatterns = [
    path('', login_view, name='root'),
    path('login/', login_view, name='login'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('logout/', logout_view, name='logout'),
    
    # Role-specific dashboards
    path('dashboard/buyer/', buyer_dashboard_view, name='buyer_dashboard'),
    path('dashboard/seller/', seller_dashboard_view, name='seller_dashboard'),
    path('dashboard/transporter/', transporter_dashboard_view, name='transporter_dashboard'),
    path('dashboard/both_sellerandbuyer/', both_sellerandbuyer_dashboard_view, name='both_sellerandbuyer_dashboard'),
    
    # User Management
    path('users/', user_list_view, name='user_list'),
    path('tags/', tag_master_view, name='tag_master'),
    path('users/create/', user_create_view, name='user_create'),
    path('users/<int:user_id>/edit/', user_update_view, name='user_update'),
    path('users/<int:user_id>/delete/', user_delete_view, name='user_delete'),
    
    # Category Management
    path('categories/', category_list_view, name='category_list'),
    path('api/categories/create/', category_create_ajax, name='category_create_ajax'),
    path('api/categories/<int:category_id>/', category_get_ajax, name='category_get_ajax'),
    path('api/categories/<int:category_id>/update/', category_update_ajax, name='category_update_ajax'),
    path('api/categories/<int:category_id>/delete/', category_delete_ajax, name='category_delete_ajax'),
    path('api/categories/tree/', category_tree_ajax, name='category_tree_ajax'),
    path('api/categories/<int:parent_id>/children/', category_children_ajax, name='category_children_ajax'),
    path('api/categories/<int:category_id>/path/', category_path_ajax, name='category_path_ajax'),
    path('api/categories/search/', category_search_ajax, name='category_search_ajax'),
    
    # SubCategory Management
    path('subcategories/', subcategory_list_view, name='subcategory_list'),
    path('api/subcategories/create/', subcategory_create_ajax, name='subcategory_create_ajax'),
    path('api/subcategories/<int:subcategory_id>/', subcategory_get_ajax, name='subcategory_get_ajax'),
    path('api/subcategories/<int:subcategory_id>/update/', subcategory_update_ajax, name='subcategory_update_ajax'),
    path('api/subcategories/<int:subcategory_id>/delete/', subcategory_delete_ajax, name='subcategory_delete_ajax'),

    # Brand Management
    path('brands/', brand_list_view, name='brand_list'),
    path('api/brands/create/', brand_create_ajax, name='brand_create_ajax'),
    path('api/brands/<int:brand_id>/', brand_get_ajax, name='brand_get_ajax'),
    path('api/brands/<int:brand_id>/update/', brand_update_ajax, name='brand_update_ajax'),
    path('api/brands/<int:brand_id>/delete/', brand_delete_ajax, name='brand_delete_ajax'),
    
    # Product Management
    path('offers/', product_list_view, name='product_list'),
    path('offers/add/', product_create_view, name='product_create'),
    path('api/offers/create/', product_create_ajax, name='product_create_ajax'),
    path('api/offers/<int:product_id>/', product_get_ajax, name='product_get_ajax'),
    path('api/offers/<int:product_id>/update/', product_update_ajax, name='product_update_ajax'),
    path('api/offers/<int:product_id>/delete/', product_delete_ajax, name='product_delete_ajax'),
    path('api/offers/<int:product_id>/toggle/', product_toggle_ajax, name='product_toggle_ajax'),
    path('api/offers/<int:product_id>/update-stock/', product_update_stock_ajax, name='product_update_stock_ajax'),
    
    # Interest/Offer Management
    path('api/products/<int:product_id>/show-interest/', product_show_interest_ajax, name='product_show_interest_ajax'),
    path('api/products/<int:product_id>/toggle-interest/', product_toggle_interest_ajax, name='product_toggle_interest_ajax'),
    path('api/products/<int:product_id>/interests/', product_interests_ajax, name='product_interests_ajax'),
    path('api/products/<int:product_id>/approve/', product_accept_buyer_ajax, name='product_accept_buyer_ajax'),
    path('api/products/<int:product_id>/reject/', product_reject_buyer_ajax, name='product_reject_buyer_ajax'),
    path('api/products/<int:product_id>/confirm-deal/', product_confirm_deal_ajax, name='product_confirm_deal_ajax'),
    path('api/products/<int:product_id>/buyer-confirm/', product_buyer_confirm_ajax, name='product_buyer_confirm_ajax'),
    path('api/offers/list/', offers_list_ajax, name='offers_list_ajax'),
    
    # Contracts
    path('api/contracts/list/', contracts_list_ajax, name='contracts_list_ajax'),
    path('api/contracts/<int:contract_id>/', contract_detail_ajax, name='contract_detail_ajax'),
    path('api/contracts/<int:contract_id>/update/', contract_update_ajax, name='contract_update_ajax'),
    path('api/contracts/export/', contracts_export_csv, name='contracts_export_csv'),

    # Product Image Management
    path('product-images/', product_image_list_view, name='product_image_list'),
    path('api/product-images/create/', product_image_create_ajax, name='product_image_create_ajax'),
    path('api/product-images/<int:image_id>/', product_image_get_ajax, name='product_image_get_ajax'),
    path('api/product-images/<int:image_id>/delete/', product_image_delete_ajax, name='product_image_delete_ajax'),
    
    # User AJAX endpoints
    path('api/users/<int:user_id>/', get_user_data, name='get_user_data'),
    path('api/users/create/', user_create_ajax, name='user_create_ajax'),
    path('api/users/<int:user_id>/update/', user_update_ajax, name='user_update_ajax'),
    path('api/users/<int:user_id>/status/', user_update_status_ajax, name='user_update_status_ajax'),
    path('api/users/<int:user_id>/delete/', user_delete_ajax, name='user_delete_ajax'),
    
    # Permissions Management
    path('permissions/', permissions_views.role_permissions_view, name='role_permissions'),
    path('api/permissions/matrix/', permissions_views.permissions_matrix_view, name='permissions_matrix'),
    path('api/permissions/update/', permissions_views.update_permission, name='update_permission'),

    # Branch Master
    path('dashboard/branch-master/', branch_master_view, name='branch_master'),

    # Location APIs
    path('api/location/states/', location_states_ajax, name='location_states_ajax'),
    path('api/location/cities/', location_cities_ajax, name='location_cities_ajax'),
    path('api/location/areas/', location_areas_ajax, name='location_areas_ajax'),

    # Branch APIs
    path('api/branch/create/', branch_create_ajax, name='branch_create_ajax'),
    path('api/branch/update/<int:branch_id>/', branch_update_ajax, name='branch_update_ajax'),
    path('api/branch/toggle/<int:branch_id>/', branch_toggle_status_ajax, name='branch_toggle_status_ajax'),
    path('api/branch/delete/<int:branch_id>/', branch_delete_ajax, name='branch_delete_ajax'),
    
    # Intrast/Offers Page
    path('contracts/', intrast_page, name='intrast_page'),
]