from django.contrib import admin

# Register your models here.
from .models import DaalUser
from .models import *

@admin.register(DaalUser)
class DaalUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'last_name', 'email', 'mobile', 'role', 'is_buyer', 'is_seller', 'is_admin','is_superuser', 'is_staff', 'is_active', 'is_transporter', 'is_both_sellerandbuyer', 'pan_number', 'gst_number', 'char_password')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'mobile')
    list_filter = ('role', 'is_buyer', 'is_seller', 'is_admin', 'is_staff', 'is_active', 'is_transporter', 'is_both_sellerandbuyer')
    ordering = ('username',)

@admin.register(CategoryMaster)
class CategoryMasterAdmin(admin.ModelAdmin):
    list_display = ('category_name', 'parent', 'level', 'is_active', 'created_at')
    list_filter = ('level', 'is_active', 'parent')
    search_fields = ('category_name',)
    ordering = ('path', 'category_name')
    raw_id_fields = ('parent',)
    
admin.site.register(TagMaster)
admin.site.register(BrandMaster)
admin.site.register(Product)
admin.site.register(ProductImage)
admin.site.register(RolePermission)
admin.site.register(ProductInterest)
admin.site.register(BranchMaster)

