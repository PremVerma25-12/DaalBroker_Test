from rest_framework import serializers
import re
from brokers_app.models import *
from .utils import normalize_role, _is_admin_user
from brokers_app.utils import get_contract_display_ids

PAN_REGEX = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$')
GST_REGEX = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9]Z[0-9A-Z]$')

ALLOWED_DOCUMENT_CONTENT_TYPES = {'image/jpeg', 'image/png', 'application/pdf'}
MAX_DOCUMENT_FILE_SIZE = 2 * 1024 * 1024


class CategorySerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.category_name', read_only=True, allow_null=True)
    children_count = serializers.SerializerMethodField()
    full_path = serializers.SerializerMethodField()
    is_root = serializers.BooleanField(read_only=True)
    is_leaf = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = CategoryMaster
        fields = ['id', 'category_name', 'parent', 'parent_name', 'level', 'path', 'is_active', 
                  'children_count', 'full_path', 'is_root', 'is_leaf', 'created_at', 'updated_at']
        read_only_fields = ['level', 'path']
    
    def get_children_count(self, obj):
        return obj.children.count()
    
    def get_full_path(self, obj):
        return obj.get_full_path()


class CategoryTreeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = CategoryMaster
        fields = ['id', 'category_name', 'level', 'path', 'is_active', 'children']
    
    def get_children(self, obj):
        children = obj.children.filter(is_active=True).order_by('category_name')
        return CategoryTreeSerializer(children, many=True).data


class SubCategorySerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(queryset=CategoryMaster.objects.all(), source='category', write_only=True)
    parent_name = serializers.CharField(source='parent.category_name', read_only=True, allow_null=True)
    full_path = serializers.SerializerMethodField()
    
    class Meta:
        model = CategoryMaster
        fields = ['id', 'category_name', 'parent', 'parent_name', 'category', 'category_id', 
                  'level', 'path', 'is_active', 'full_path', 'created_at', 'updated_at']
    
    def get_full_path(self, obj):
        return obj.get_full_path()


class ProductImageSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    image_url = serializers.SerializerMethodField()

    def get_image_url(self, obj):
        request = self.context.get('request')
        return request.build_absolute_uri(obj.image.url) if request else obj.image.url

    class Meta:
        model = ProductImage
        fields = ['id', 'product', 'product_title', 'image', 'image_url', 'is_primary', 'created_at']
        read_only_fields = ['created_at']


class ProductVideoSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    video_url = serializers.SerializerMethodField()

    def get_video_url(self, obj):
        request = self.context.get('request')
        if obj.video:
            return request.build_absolute_uri(obj.video.url) if request else obj.video.url
        return None
        
    class Meta:
        model = ProductVideo
        fields = ['id', 'product', 'product_title', 'video', 'video_url', 'title', 'is_primary', 'created_at']


class ProductSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=CategoryMaster.objects.all(),
        source='category',
        write_only=True,
        required=False,
    )
    root_category_id = serializers.PrimaryKeyRelatedField(
        queryset=CategoryMaster.objects.all(),
        source='root_category',
        write_only=True,
        required=False,
        allow_null=True,
    )
    
    category = serializers.SerializerMethodField()
    root_category = serializers.SerializerMethodField()
    category_path_data = serializers.SerializerMethodField()
    brand = serializers.SerializerMethodField()
    seller = serializers.SerializerMethodField()
    images = ProductImageSerializer(many=True, read_only=True)
    video = serializers.SerializerMethodField()
    interest_count = serializers.SerializerMethodField()
    
    # ✅ New fields for stock management
    available_quantity = serializers.SerializerMethodField()
    stock_status = serializers.SerializerMethodField()
     
    def to_representation(self, instance):
        try:
            print(f"Serializing product: {instance.id}")
            data = super().to_representation(instance)
            print(f"Serialization successful")
            return data
        except Exception as e:
            print(f"Serialization error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'id': instance.id, 'error': str(e)}
    def get_category(self, obj):
        if obj.category:
            return {'id': obj.category.id, 'name': obj.category.category_name}
        return None

    def get_root_category(self, obj):
        if obj.root_category:
            return {'id': obj.root_category.id, 'name': obj.root_category.category_name}
        return None

    def get_category_path_data(self, obj):
        if obj.category_path:
            import json
            try:
                return json.loads(obj.category_path)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    def get_seller(self, obj):
        if obj.seller:
            return {'id': obj.seller.id, 'username': obj.seller.username}
        return None

    def get_brand(self, obj):
        if obj.brand:
            return {'id': obj.brand.id, 'name': obj.brand.brand_name, 'unique_id': obj.brand.brand_unique_id}
        return None

    def get_interest_count(self, obj):
        return obj.interests.filter(
            is_active=True,
            status__in=[
                ProductInterest.STATUS_INTERESTED,
                ProductInterest.STATUS_SELLER_CONFIRMED,
            ],
        ).count()
    
    def get_available_quantity(self, obj):
        return str(obj.remaining_quantity or obj.original_quantity or '0')
    
    def get_stock_status(self, obj):
        if obj.remaining_quantity == 0:
            return 'out_of_stock'
        elif obj.remaining_quantity and obj.remaining_quantity < (obj.original_quantity or 0):
            return 'partially_available'
        return 'available'

    def get_video(self, obj):
        videos = obj.videos.all()
        if videos:
            request = self.context.get('request')
            return [
                {
                    'id': v.id,
                    'url': request.build_absolute_uri(v.video.url) if request else v.video.url,
                    'title': v.title,
                    'is_primary': v.is_primary
                }
                for v in videos
            ]
        return []

    class Meta:
        model = Product
        fields = [
            'id', 'title', 'description', 
            'category', 'category_id', 'root_category', 'root_category_id', 
            'category_path_data',
            'brand', 'seller', 'amount',  # ✅ Changed from base_amount to amount
            'amount_unit', 'original_quantity', 'remaining_quantity', 'available_quantity', 'stock_status',
            'quantity_unit', 'loading_from', 'loading_to', 'loading_location', 'remark', 
            'is_active', 'status', 'deal_status', 'created_at', 'updated_at', 'images', 
            'interest_count', 'video',
        ]
        read_only_fields = ['created_at', 'updated_at', 'root_category', 'category_path', 
                           'original_quantity', 'remaining_quantity']

    def validate(self, attrs):
        request = self.context.get('request')
        user = getattr(request, 'user', None)

        # Handle seller from form data
        if 'seller' in self.initial_data and self.initial_data.get('seller'):
            seller_val = self.initial_data.get('seller')
            if seller_val and str(seller_val).strip() not in ('', 'null'):
                try:
                    seller_id = str(seller_val).strip()
                    if seller_id.isdigit():
                        seller_id = int(seller_id)
                    attrs['seller'] = DaalUser.objects.get(pk=seller_id)
                except (DaalUser.DoesNotExist, ValueError, TypeError) as e:
                    raise serializers.ValidationError({'seller': f'Selected seller is invalid: {e}'})

        # Handle category - support sub-subcategory
        category_id = None
        if 'category_id' in self.initial_data and self.initial_data.get('category_id'):
            category_id = self.initial_data.get('category_id')
        elif 'category' in self.initial_data and self.initial_data.get('category'):
            category_id = self.initial_data.get('category')
        
        if category_id and str(category_id).strip() not in ('', 'null'):
            try:
                cat_id = str(category_id).strip()
                if cat_id.isdigit():
                    cat_id = int(cat_id)
                category_obj = CategoryMaster.objects.get(pk=cat_id)
                attrs['category'] = category_obj
                
                if category_obj:
                    root = category_obj.get_root_category()
                    attrs['root_category'] = root
                    
                    import json
                    attrs['category_path'] = json.dumps({
                        "root": root.category_name,
                        "selected": category_obj.category_name,
                        "full_path": category_obj.get_full_path()
                    })
            except (CategoryMaster.DoesNotExist, ValueError, TypeError):
                raise serializers.ValidationError({'category': 'Selected category is invalid.'})
        else:
            raise serializers.ValidationError({'category': 'Please select a category.'})

        # Handle brand (optional)
        brand_id = None
        if 'brand_id' in self.initial_data and self.initial_data.get('brand_id'):
            brand_id = self.initial_data.get('brand_id')
        elif 'brand' in self.initial_data and self.initial_data.get('brand'):
            brand_id = self.initial_data.get('brand')
        
        if brand_id and str(brand_id).strip() not in ('', 'null'):
            try:
                brand_val = str(brand_id).strip()
                if brand_val.isdigit():
                    brand_val = int(brand_val)
                attrs['brand'] = BrandMaster.objects.get(pk=brand_val)
            except (BrandMaster.DoesNotExist, ValueError, TypeError):
                pass

        # Handle quantity
        if 'quantity' in self.initial_data:
            quantity_val = self.initial_data.get('quantity')
            if quantity_val and str(quantity_val).strip():
                try:
                    quantity = float(quantity_val)
                    if quantity <= 0:
                        raise serializers.ValidationError({'quantity': 'Quantity must be greater than 0.'})
                    attrs['original_quantity'] = quantity
                    attrs['remaining_quantity'] = quantity
                except (ValueError, TypeError):
                    raise serializers.ValidationError({'quantity': 'Invalid quantity value.'})

        # Handle amount_unit
        if 'amount_unit' in self.initial_data and self.initial_data.get('amount_unit'):
            attrs['amount_unit'] = self.initial_data.get('amount_unit')

        # Handle loading from/to
        if 'loading_from' in self.initial_data:
            attrs['loading_from'] = self.initial_data.get('loading_from')
        if 'loading_to' in self.initial_data:
            attrs['loading_to'] = self.initial_data.get('loading_to')

        # Handle is_active checkbox
        if 'is_active' in self.initial_data:
            is_active_val = self.initial_data.get('is_active')
            attrs['is_active'] = is_active_val == 'on' or is_active_val is True

        # Seller assignment logic
        if user:
            if (user.is_seller or user.role in ('seller', 'both_sellerandbuyer')) and not _is_admin_user(user):
                if 'seller' in attrs and attrs.get('seller') and attrs['seller'] != user:
                    raise serializers.ValidationError({'seller': 'Sellers can only create products for themselves.'})
                attrs['seller'] = user
            elif _is_admin_user(user):
                if 'seller' not in attrs or not attrs.get('seller'):
                    raise serializers.ValidationError({'seller': 'Seller is required for admin users.'})
                if attrs.get('seller') and not (attrs['seller'].is_seller or attrs['seller'].role in ('seller', 'both_sellerandbuyer')):
                    raise serializers.ValidationError({'seller': 'Selected user does not have seller permissions.'})
            else:
                raise serializers.ValidationError({'non_field_errors': ['You do not have permission to create products.']})

        if self.instance is None and attrs.get('original_quantity') in (None, ''):
            raise serializers.ValidationError({'quantity': 'Quantity is required.'})
        
        return attrs


class UserSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()

    def get_tags(self, obj):
        return [{'id': tag.id, 'tag_name': tag.tag_name} for tag in obj.tags.all().order_by('tag_name')]

    class Meta:
        model = DaalUser
        fields = [
            'id', 'username', 'mobile', 'email', 'first_name', 'last_name',
            'role', 'pan_number', 'gst_number', 'profile_image', 'gender', 'dob',
            'pan_image', 'gst_image', 'shopact_image', 'adharcard_image',
            'tags',
            'kyc_status', 'kyc_submitted_at', 'kyc_approved_at',
            'kyc_rejected_at', 'kyc_rejection_reason', 'account_status', 'deactivated_at',
            'suspended_at', 'suspension_reason', 'is_active',
        ]


class RegistrationSerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=15)
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    role = serializers.CharField(max_length=30)
    pan_number = serializers.CharField(max_length=10, required=False, allow_blank=True, allow_null=True)
    gst_number = serializers.CharField(max_length=15, required=False, allow_blank=True, allow_null=True)
    gender = serializers.ChoiceField(choices=DaalUser.GENDER_CHOICES, required=False, allow_null=True)
    dob = serializers.DateField(required=False, allow_null=True)
    pan_image = serializers.FileField(required=False, allow_null=True)
    gst_image = serializers.FileField(required=False, allow_null=True)
    shopact_image = serializers.FileField(required=False, allow_null=True)
    adharcard_image = serializers.FileField(required=True, allow_null=False)

    def validate_mobile(self, value):
        mobile_digits = ''.join(ch for ch in str(value) if ch.isdigit())
        if len(mobile_digits) < 10:
            raise serializers.ValidationError('Enter a valid mobile number.')
        if DaalUser.objects.filter(mobile=value).exists():
            raise serializers.ValidationError('Mobile already exists.')
        return value

    def validate_email(self, value):
        if DaalUser.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email already exists.')
        return value

    def validate_role(self, value):
        try:
            from .utils import normalize_role
            return normalize_role(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))

    def validate_pan_number(self, value):
        if value in (None, ''):
            return value
        cleaned_value = str(value).strip().upper()
        if len(cleaned_value) != 10:
            raise serializers.ValidationError('PAN number must be exactly 10 characters.')
        if not PAN_REGEX.fullmatch(cleaned_value):
            raise serializers.ValidationError('Invalid PAN format. Use 5 letters + 4 digits + 1 letter (e.g., ABCDE1234F).')
        return cleaned_value

    def validate_gst_number(self, value):
        if value in (None, ''):
            return value
        cleaned_value = str(value).strip().upper()
        if len(cleaned_value) != 15:
            raise serializers.ValidationError('GST number must be exactly 15 characters.')
        if not GST_REGEX.fullmatch(cleaned_value):
            raise serializers.ValidationError('Invalid GST format. Use: 2 digits + PAN(10) + 1 digit + Z + 1 alphanumeric (e.g., 27ABCDE1234F1Z5).')
        return cleaned_value

    def validate(self, attrs):
        pan_number = attrs.get('pan_number')
        gst_number = attrs.get('gst_number')
        adharcard_image = attrs.get('adharcard_image')

        for field_name in ('pan_image', 'gst_image', 'shopact_image', 'adharcard_image'):
            uploaded = attrs.get(field_name)
            if not uploaded:
                continue
            content_type = str(getattr(uploaded, 'content_type', '')).lower()
            if content_type and content_type not in ALLOWED_DOCUMENT_CONTENT_TYPES:
                raise serializers.ValidationError({field_name: 'Only JPG, JPEG, PNG, or PDF files are allowed.'})
            if uploaded.size > MAX_DOCUMENT_FILE_SIZE:
                raise serializers.ValidationError({field_name: 'File size must be no more than 2MB.'})

        if not adharcard_image:
            raise serializers.ValidationError({'adharcard_image': 'Aadhaar Card document is required.'})

        if pan_number and gst_number and gst_number[2:12] != pan_number:
            raise serializers.ValidationError({
                'gst_number': 'GST PAN segment does not match the provided PAN number.'
            })
        return attrs


class LoginSerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=15)
    password = serializers.CharField(max_length=128)


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(max_length=128)
    new_password = serializers.CharField(max_length=128)
    confirm_password = serializers.CharField(max_length=128)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'New password and confirm password must match.'})
        return attrs


class KYCRejectSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(max_length=500)


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DaalUser
        fields = [
            'first_name', 'last_name', 'email', 'mobile', 'profile_image',
            'pan_number', 'gst_number', 'gender', 'dob'
        ]
        extra_kwargs = {
            'profile_image': {'required': False},
            'pan_number': {'required': False},
            'gst_number': {'required': False},
            'gender': {'required': False},
            'dob': {'required': False},
            'email': {'required': False, 'validators': []},
            'mobile': {'required': False, 'validators': []},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        user = request.user if request else None
        if user and user.role == 'admin':
            pass
        else:
            allowed_fields = {'first_name', 'last_name', 'email', 'mobile', 'profile_image'}
            for field_name in list(self.fields.keys()):
                if field_name not in allowed_fields:
                    self.fields.pop(field_name)

    def validate_email(self, value):
        if value and DaalUser.objects.exclude(pk=getattr(self.instance, 'pk', None)).filter(email=value).exists():
            raise serializers.ValidationError('Email already exists.')
        return value

    def validate_mobile(self, value):
        if value and DaalUser.objects.exclude(pk=getattr(self.instance, 'pk', None)).filter(mobile=value).exists():
            raise serializers.ValidationError('Mobile already exists.')
        return value


class ProductInterestListSerializer(serializers.ModelSerializer):
    """Serializer for list view - with buyer unique ID only"""
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    amount = serializers.DecimalField(source='product.amount', max_digits=10, decimal_places=2, read_only=True)
    amount_unit = serializers.CharField(source='product.amount_unit', read_only=True)
    quantity_unit = serializers.CharField(source='product.quantity_unit', read_only=True)
    
    # ✅ Buyer info - only unique ID, not real name
    buyer_unique_id = serializers.CharField(source='buyer.buyer_unique_id', read_only=True)
    
    # ✅ Seller info
    seller_username = serializers.CharField(source='seller.username', read_only=True)
    seller_id = serializers.IntegerField(source='seller.id', read_only=True)
    
    # ✅ Loading from-to
    loading_from = serializers.CharField(read_only=True)
    loading_to = serializers.CharField(read_only=True)
    
    status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductInterest
        fields = [
            'id', 'transaction_id', 'product_id', 'product_title',
            'amount', 'amount_unit', 'quantity_unit',
            'snapshot_amount', 'snapshot_quantity',
            'buyer_offered_amount', 'buyer_required_quantity',
            'loading_from', 'loading_to',
            'delivery_date', 'buyer_remark',
            'seller_remark', 'superadmin_remark',
            'status', 'status_display', 'is_active',
            'buyer_unique_id', 'seller_username', 'seller_id',
            'created_at', 'updated_at', 'deal_confirmed_at'
        ]
    
    def get_status_display(self, obj):
        return obj.get_status_display()


class ProductInterestDetailSerializer(serializers.ModelSerializer):
    """Serializer for detail view"""
    product_details = serializers.SerializerMethodField()
    buyer_details = serializers.SerializerMethodField()
    seller_details = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductInterest
        fields = '__all__'
    
    def get_product_details(self, obj):
        return {
            'id': obj.product.id,
            'title': obj.product.title,
            'amount': str(obj.product.amount),
            'amount_unit': obj.product.amount_unit,
            'available_quantity': str(obj.product.remaining_quantity or obj.product.original_quantity),
            'quantity_unit': obj.product.quantity_unit,
            'category': obj.product.category.category_name if obj.product.category else None,
            'loading_from': obj.product.loading_from,
            'loading_to': obj.product.loading_to,
        }
    
    def get_buyer_details(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        
        # For seller - only show unique ID
        if user and (user == obj.seller or user.role in ('seller', 'both_sellerandbuyer')):
            return {
                'unique_id': obj.buyer.buyer_unique_id,
                'offer_amount': str(obj.buyer_offered_amount),
                'required_quantity': str(obj.buyer_required_quantity),
                'loading_from': obj.loading_from,
                'loading_to': obj.loading_to,
                'delivery_date': obj.delivery_date,
                'remark': obj.buyer_remark,
            }
        
        # For admin - show all details
        if user and (user.is_admin or user.is_superuser or user.role == 'super_admin'):
            return {
                'id': obj.buyer.id,
                'unique_id': obj.buyer.buyer_unique_id,
                'username': obj.buyer.username,
                'email': obj.buyer.email,
                'mobile': obj.buyer.mobile,
                'company': obj.buyer.company_name,
            }
        
        # For others - minimal info
        return {
            'unique_id': obj.buyer.buyer_unique_id,
        }
    
    def get_seller_details(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        
        if user and (user.is_admin or user.is_superuser or user.role == 'super_admin'):
            return {
                'id': obj.seller.id,
                'username': obj.seller.username,
                'email': obj.seller.email,
                'mobile': obj.seller.mobile,
                'company': obj.seller.company_name,
            }
        return {
            'username': obj.seller.username,
        }


class InterestActionSerializer(serializers.Serializer):
    seller_remark = serializers.CharField(required=False, allow_blank=True)
    interest_id = serializers.IntegerField(required=False)


class DealConfirmSerializer(serializers.Serializer):
    admin_remark = serializers.CharField(required=False, allow_blank=True)


class ContractSerializer(serializers.ModelSerializer):
    """Serializer for contracts"""
    product_title = serializers.CharField(source='product.title', read_only=True)
    buyer_name = serializers.CharField(source='buyer.username', read_only=True)
    buyer_unique_id = serializers.CharField(source='buyer.buyer_unique_id', read_only=True)
    seller_name = serializers.CharField(source='seller.username', read_only=True)
    display_seller_id = serializers.SerializerMethodField()
    display_buyer_id = serializers.SerializerMethodField()
    
    class Meta:
        model = Contract
        fields = '__all__'
        read_only_fields = ['contract_id', 'confirmed_at', 'created_at']

    def get_display_seller_id(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        is_admin = bool(user and _is_admin_user(user))
        return get_contract_display_ids(obj, user, is_admin=is_admin)['display_seller_id']

    def get_display_buyer_id(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        is_admin = bool(user and _is_admin_user(user))
        return get_contract_display_ids(obj, user, is_admin=is_admin)['display_buyer_id']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        user = request.user if request else None
        is_admin = bool(user and _is_admin_user(user))
        party_ids = get_contract_display_ids(instance, user, is_admin=is_admin)
        data['seller'] = party_ids['seller_id']
        data['buyer'] = party_ids['buyer_id']
        data['display_seller_id'] = party_ids['display_seller_id']
        data['display_buyer_id'] = party_ids['display_buyer_id']
        if not (is_admin or (user and user.id == instance.buyer_id)):
            data['buyer_unique_id'] = None
        return data

PAN_REGEX = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$')
GST_REGEX = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9]Z[0-9A-Z]$')

ALLOWED_DOCUMENT_CONTENT_TYPES = {'image/jpeg', 'image/png', 'application/pdf'}
MAX_DOCUMENT_FILE_SIZE = 2 * 1024 * 1024


class CategorySerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.category_name', read_only=True, allow_null=True)
    children_count = serializers.SerializerMethodField()
    full_path = serializers.SerializerMethodField()
    is_root = serializers.BooleanField(read_only=True)
    is_leaf = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = CategoryMaster
        fields = ['id', 'category_name', 'parent', 'parent_name', 'level', 'path', 'is_active', 
                  'children_count', 'full_path', 'is_root', 'is_leaf', 'created_at', 'updated_at']
        read_only_fields = ['level', 'path']
    
    def get_children_count(self, obj):
        return obj.children.count()
    
    def get_full_path(self, obj):
        return obj.get_full_path()


class CategoryTreeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = CategoryMaster
        fields = ['id', 'category_name', 'level', 'path', 'is_active', 'children']
    
    def get_children(self, obj):
        children = obj.children.filter(is_active=True).order_by('category_name')
        return CategoryTreeSerializer(children, many=True).data


class SubCategorySerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(queryset=CategoryMaster.objects.all(), source='category', write_only=True)
    parent_name = serializers.CharField(source='parent.category_name', read_only=True, allow_null=True)
    full_path = serializers.SerializerMethodField()
    
    class Meta:
        model = CategoryMaster
        fields = ['id', 'category_name', 'parent', 'parent_name', 'category', 'category_id', 
                  'level', 'path', 'is_active', 'full_path', 'created_at', 'updated_at']
    
    def get_full_path(self, obj):
        return obj.get_full_path()


class ProductImageSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    image_url = serializers.SerializerMethodField()

    def get_image_url(self, obj):
        request = self.context.get('request')
        return request.build_absolute_uri(obj.image.url) if request else obj.image.url

    class Meta:
        model = ProductImage
        fields = ['id', 'product', 'product_title', 'image', 'image_url', 'is_primary', 'created_at']
        read_only_fields = ['created_at']


class ProductVideoSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    video_url = serializers.SerializerMethodField()

    def get_video_url(self, obj):
        request = self.context.get('request')
        if obj.video:
            return request.build_absolute_uri(obj.video.url) if request else obj.video.url
        return None
        
    class Meta:
        model = ProductVideo
        fields = ['id', 'product', 'product_title', 'video', 'video_url', 'title', 'is_primary', 'created_at']


class ProductSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=CategoryMaster.objects.all(),
        source='category',
        write_only=True,
        required=False,
    )
    root_category_id = serializers.PrimaryKeyRelatedField(
        queryset=CategoryMaster.objects.all(),
        source='root_category',
        write_only=True,
        required=False,
        allow_null=True,
    )
    
    category = serializers.SerializerMethodField()
    root_category = serializers.SerializerMethodField()
    category_path_data = serializers.SerializerMethodField()
    brand = serializers.SerializerMethodField()
    seller = serializers.SerializerMethodField()
    images = ProductImageSerializer(many=True, read_only=True)
    video = serializers.SerializerMethodField()
    interest_count = serializers.SerializerMethodField()
    
    # ✅ New fields for stock management
    available_quantity = serializers.SerializerMethodField()
    stock_status = serializers.SerializerMethodField()
     
    def to_representation(self, instance):
        try:
            print(f"Serializing product: {instance.id}")
            data = super().to_representation(instance)
            print(f"Serialization successful")
            return data
        except Exception as e:
            print(f"Serialization error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'id': instance.id, 'error': str(e)}
    def get_category(self, obj):
        if obj.category:
            return {'id': obj.category.id, 'name': obj.category.category_name}
        return None

    def get_root_category(self, obj):
        if obj.root_category:
            return {'id': obj.root_category.id, 'name': obj.root_category.category_name}
        return None

    def get_category_path_data(self, obj):
        if obj.category_path:
            import json
            try:
                return json.loads(obj.category_path)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    def get_seller(self, obj):
        if obj.seller:
            return {'id': obj.seller.id, 'username': obj.seller.username}
        return None

    def get_brand(self, obj):
        if obj.brand:
            return {'id': obj.brand.id, 'name': obj.brand.brand_name, 'unique_id': obj.brand.brand_unique_id}
        return None

    def get_interest_count(self, obj):
        return obj.interests.filter(
            is_active=True,
            status__in=[
                ProductInterest.STATUS_INTERESTED,
                ProductInterest.STATUS_SELLER_CONFIRMED,
            ],
        ).count()
    
    def get_available_quantity(self, obj):
        return str(obj.remaining_quantity or obj.original_quantity or '0')
    
    def get_stock_status(self, obj):
        if obj.remaining_quantity == 0:
            return 'out_of_stock'
        elif obj.remaining_quantity and obj.remaining_quantity < (obj.original_quantity or 0):
            return 'partially_available'
        return 'available'

    def get_video(self, obj):
        videos = obj.videos.all()
        if videos:
            request = self.context.get('request')
            return [
                {
                    'id': v.id,
                    'url': request.build_absolute_uri(v.video.url) if request else v.video.url,
                    'title': v.title,
                    'is_primary': v.is_primary
                }
                for v in videos
            ]
        return []

    class Meta:
        model = Product
        fields = [
            'id', 'title', 'description', 
            'category', 'category_id', 'root_category', 'root_category_id', 
            'category_path_data',
            'brand', 'seller', 'amount',  # ✅ Changed from base_amount to amount
            'amount_unit', 'original_quantity', 'remaining_quantity', 'available_quantity', 'stock_status',
            'quantity_unit', 'loading_from', 'loading_to', 'loading_location', 'remark', 
            'is_active', 'status', 'deal_status', 'created_at', 'updated_at', 'images', 
            'interest_count', 'video',
        ]
        read_only_fields = ['created_at', 'updated_at', 'root_category', 'category_path', 
                           'original_quantity', 'remaining_quantity']

    def validate(self, attrs):
        request = self.context.get('request')
        user = getattr(request, 'user', None)

        # Handle seller from form data
        if 'seller' in self.initial_data and self.initial_data.get('seller'):
            seller_val = self.initial_data.get('seller')
            if seller_val and str(seller_val).strip() not in ('', 'null'):
                try:
                    seller_id = str(seller_val).strip()
                    if seller_id.isdigit():
                        seller_id = int(seller_id)
                    attrs['seller'] = DaalUser.objects.get(pk=seller_id)
                except (DaalUser.DoesNotExist, ValueError, TypeError) as e:
                    raise serializers.ValidationError({'seller': f'Selected seller is invalid: {e}'})

        # Handle category - support sub-subcategory
        category_id = None
        if 'category_id' in self.initial_data and self.initial_data.get('category_id'):
            category_id = self.initial_data.get('category_id')
        elif 'category' in self.initial_data and self.initial_data.get('category'):
            category_id = self.initial_data.get('category')
        
        if category_id and str(category_id).strip() not in ('', 'null'):
            try:
                cat_id = str(category_id).strip()
                if cat_id.isdigit():
                    cat_id = int(cat_id)
                category_obj = CategoryMaster.objects.get(pk=cat_id)
                attrs['category'] = category_obj
                
                if category_obj:
                    root = category_obj.get_root_category()
                    attrs['root_category'] = root
                    
                    import json
                    attrs['category_path'] = json.dumps({
                        "root": root.category_name,
                        "selected": category_obj.category_name,
                        "full_path": category_obj.get_full_path()
                    })
            except (CategoryMaster.DoesNotExist, ValueError, TypeError):
                raise serializers.ValidationError({'category': 'Selected category is invalid.'})
        else:
            raise serializers.ValidationError({'category': 'Please select a category.'})

        # Handle brand (optional)
        brand_id = None
        if 'brand_id' in self.initial_data and self.initial_data.get('brand_id'):
            brand_id = self.initial_data.get('brand_id')
        elif 'brand' in self.initial_data and self.initial_data.get('brand'):
            brand_id = self.initial_data.get('brand')
        
        if brand_id and str(brand_id).strip() not in ('', 'null'):
            try:
                brand_val = str(brand_id).strip()
                if brand_val.isdigit():
                    brand_val = int(brand_val)
                attrs['brand'] = BrandMaster.objects.get(pk=brand_val)
            except (BrandMaster.DoesNotExist, ValueError, TypeError):
                pass

        # Handle quantity
        if 'quantity' in self.initial_data:
            quantity_val = self.initial_data.get('quantity')
            if quantity_val and str(quantity_val).strip():
                try:
                    quantity = float(quantity_val)
                    if quantity <= 0:
                        raise serializers.ValidationError({'quantity': 'Quantity must be greater than 0.'})
                    attrs['original_quantity'] = quantity
                    attrs['remaining_quantity'] = quantity
                except (ValueError, TypeError):
                    raise serializers.ValidationError({'quantity': 'Invalid quantity value.'})

        # Handle amount_unit
        if 'amount_unit' in self.initial_data and self.initial_data.get('amount_unit'):
            attrs['amount_unit'] = self.initial_data.get('amount_unit')

        # Handle loading from/to
        if 'loading_from' in self.initial_data:
            attrs['loading_from'] = self.initial_data.get('loading_from')
        if 'loading_to' in self.initial_data:
            attrs['loading_to'] = self.initial_data.get('loading_to')

        # Handle is_active checkbox
        if 'is_active' in self.initial_data:
            is_active_val = self.initial_data.get('is_active')
            attrs['is_active'] = is_active_val == 'on' or is_active_val is True

        # Seller assignment logic
        if user:
            if (user.is_seller or user.role in ('seller', 'both_sellerandbuyer')) and not _is_admin_user(user):
                if 'seller' in attrs and attrs.get('seller') and attrs['seller'] != user:
                    raise serializers.ValidationError({'seller': 'Sellers can only create products for themselves.'})
                attrs['seller'] = user
            elif _is_admin_user(user):
                if 'seller' not in attrs or not attrs.get('seller'):
                    raise serializers.ValidationError({'seller': 'Seller is required for admin users.'})
                if attrs.get('seller') and not (attrs['seller'].is_seller or attrs['seller'].role in ('seller', 'both_sellerandbuyer')):
                    raise serializers.ValidationError({'seller': 'Selected user does not have seller permissions.'})
            else:
                raise serializers.ValidationError({'non_field_errors': ['You do not have permission to create products.']})

        if self.instance is None and attrs.get('original_quantity') in (None, ''):
            raise serializers.ValidationError({'quantity': 'Quantity is required.'})
        
        return attrs


class UserSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()

    def get_tags(self, obj):
        return [{'id': tag.id, 'tag_name': tag.tag_name} for tag in obj.tags.all().order_by('tag_name')]

    class Meta:
        model = DaalUser
        fields = [
            'id', 'username', 'mobile', 'email', 'first_name', 'last_name',
            'role', 'pan_number', 'gst_number', 'profile_image', 'gender', 'dob',
            'pan_image', 'gst_image', 'shopact_image', 'adharcard_image',
            'tags',
            'kyc_status', 'kyc_submitted_at', 'kyc_approved_at',
            'kyc_rejected_at', 'kyc_rejection_reason', 'account_status', 'deactivated_at',
            'suspended_at', 'suspension_reason', 'is_active',
        ]


class RegistrationSerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=15)
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    role = serializers.CharField(max_length=30)
    pan_number = serializers.CharField(max_length=10, required=False, allow_blank=True, allow_null=True)
    gst_number = serializers.CharField(max_length=15, required=False, allow_blank=True, allow_null=True)
    gender = serializers.ChoiceField(choices=DaalUser.GENDER_CHOICES, required=False, allow_null=True)
    dob = serializers.DateField(required=False, allow_null=True)
    pan_image = serializers.FileField(required=False, allow_null=True)
    gst_image = serializers.FileField(required=False, allow_null=True)
    shopact_image = serializers.FileField(required=False, allow_null=True)
    adharcard_image = serializers.FileField(required=True, allow_null=False)

    def validate_mobile(self, value):
        mobile_digits = ''.join(ch for ch in str(value) if ch.isdigit())
        if len(mobile_digits) < 10:
            raise serializers.ValidationError('Enter a valid mobile number.')
        if DaalUser.objects.filter(mobile=value).exists():
            raise serializers.ValidationError('Mobile already exists.')
        return value

    def validate_email(self, value):
        if DaalUser.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email already exists.')
        return value

    def validate_role(self, value):
        try:
            from .utils import normalize_role
            return normalize_role(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))

    def validate_pan_number(self, value):
        if value in (None, ''):
            return value
        cleaned_value = str(value).strip().upper()
        if len(cleaned_value) != 10:
            raise serializers.ValidationError('PAN number must be exactly 10 characters.')
        if not PAN_REGEX.fullmatch(cleaned_value):
            raise serializers.ValidationError('Invalid PAN format. Use 5 letters + 4 digits + 1 letter (e.g., ABCDE1234F).')
        return cleaned_value

    def validate_gst_number(self, value):
        if value in (None, ''):
            return value
        cleaned_value = str(value).strip().upper()
        if len(cleaned_value) != 15:
            raise serializers.ValidationError('GST number must be exactly 15 characters.')
        if not GST_REGEX.fullmatch(cleaned_value):
            raise serializers.ValidationError('Invalid GST format. Use: 2 digits + PAN(10) + 1 digit + Z + 1 alphanumeric (e.g., 27ABCDE1234F1Z5).')
        return cleaned_value

    def validate(self, attrs):
        pan_number = attrs.get('pan_number')
        gst_number = attrs.get('gst_number')
        adharcard_image = attrs.get('adharcard_image')
        pan_image = attrs.get('pan_image')


        for field_name in ('pan_image', 'gst_image', 'shopact_image', 'adharcard_image'):
            uploaded = attrs.get(field_name)
            if not uploaded:
                continue
            content_type = str(getattr(uploaded, 'content_type', '')).lower()
            if content_type and content_type not in ALLOWED_DOCUMENT_CONTENT_TYPES:
                raise serializers.ValidationError({field_name: 'Only JPG, JPEG, PNG, or PDF files are allowed.'})
            if uploaded.size > MAX_DOCUMENT_FILE_SIZE:
                raise serializers.ValidationError({field_name: 'File size must be no more than 2MB.'})

        if not adharcard_image:
            raise serializers.ValidationError({'adharcard_image': 'Aadhaar Card document is required.'})

        if not pan_image:
            raise serializers.ValidationError({'adharcard_image': 'Aadhaar Card document is required.'})

        if pan_number and gst_number and gst_number[2:12] != pan_number:
            raise serializers.ValidationError({
                'gst_number': 'GST PAN segment does not match the provided PAN number.'
            })
        return attrs


class LoginSerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=15)
    password = serializers.CharField(max_length=128)


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(max_length=128)
    new_password = serializers.CharField(max_length=128)
    confirm_password = serializers.CharField(max_length=128)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'New password and confirm password must match.'})
        return attrs


class KYCRejectSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(max_length=500)


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DaalUser
        fields = [
            'first_name', 'last_name', 'email', 'mobile', 'profile_image',
            'pan_number', 'gst_number', 'gender', 'dob'
        ]
        extra_kwargs = {
            'profile_image': {'required': False},
            'pan_number': {'required': False},
            'gst_number': {'required': False},
            'gender': {'required': False},
            'dob': {'required': False},
            'email': {'required': False, 'validators': []},
            'mobile': {'required': False, 'validators': []},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        user = request.user if request else None
        if user and user.role == 'admin':
            pass
        else:
            allowed_fields = {'first_name', 'last_name', 'email', 'mobile', 'profile_image'}
            for field_name in list(self.fields.keys()):
                if field_name not in allowed_fields:
                    self.fields.pop(field_name)

    def validate_email(self, value):
        if value and DaalUser.objects.exclude(pk=getattr(self.instance, 'pk', None)).filter(email=value).exists():
            raise serializers.ValidationError('Email already exists.')
        return value

    def validate_mobile(self, value):
        if value and DaalUser.objects.exclude(pk=getattr(self.instance, 'pk', None)).filter(mobile=value).exists():
            raise serializers.ValidationError('Mobile already exists.')
        return value


class ProductInterestListSerializer(serializers.ModelSerializer):
    """Serializer for list view - with buyer unique ID only"""
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    amount = serializers.DecimalField(source='product.amount', max_digits=10, decimal_places=2, read_only=True)
    amount_unit = serializers.CharField(source='product.amount_unit', read_only=True)
    quantity_unit = serializers.CharField(source='product.quantity_unit', read_only=True)
    
    # ✅ Buyer info - only unique ID, not real name
    buyer_unique_id = serializers.CharField(source='buyer.buyer_unique_id', read_only=True)
    
    # ✅ Seller info
    seller_username = serializers.CharField(source='seller.username', read_only=True)
    seller_id = serializers.IntegerField(source='seller.id', read_only=True)
    
    # ✅ Loading from-to
    loading_from = serializers.CharField(read_only=True)
    loading_to = serializers.CharField(read_only=True)
    
    status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductInterest
        fields = [
            'id', 'transaction_id', 'product_id', 'product_title',
            'amount', 'amount_unit', 'quantity_unit',
            'snapshot_amount', 'snapshot_quantity',
            'buyer_offered_amount', 'buyer_required_quantity',
            'loading_from', 'loading_to',
            'delivery_date', 'buyer_remark',
            'seller_remark', 'superadmin_remark',
            'status', 'status_display', 'is_active',
            'buyer_unique_id', 'seller_username', 'seller_id',
            'created_at', 'updated_at', 'deal_confirmed_at'
        ]
    
    def get_status_display(self, obj):
        return obj.get_status_display()


class ProductInterestDetailSerializer(serializers.ModelSerializer):
    """Serializer for detail view"""
    product_details = serializers.SerializerMethodField()
    buyer_details = serializers.SerializerMethodField()
    seller_details = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductInterest
        fields = '__all__'
    
    def get_product_details(self, obj):
        return {
            'id': obj.product.id,
            'title': obj.product.title,
            'amount': str(obj.product.amount),
            'amount_unit': obj.product.amount_unit,
            'available_quantity': str(obj.product.remaining_quantity or obj.product.original_quantity),
            'quantity_unit': obj.product.quantity_unit,
            'category': obj.product.category.category_name if obj.product.category else None,
            'loading_from': obj.product.loading_from,
            'loading_to': obj.product.loading_to,
        }
    
    def get_buyer_details(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        
        # For seller - only show unique ID
        if user and (user == obj.seller or user.role in ('seller', 'both_sellerandbuyer')):
            return {
                'unique_id': obj.buyer.buyer_unique_id,
                'offer_amount': str(obj.buyer_offered_amount),
                'required_quantity': str(obj.buyer_required_quantity),
                'loading_from': obj.loading_from,
                'loading_to': obj.loading_to,
                'delivery_date': obj.delivery_date,
                'remark': obj.buyer_remark,
            }
        
        # For admin - show all details
        if user and (user.is_admin or user.is_superuser or user.role == 'super_admin'):
            return {
                'id': obj.buyer.id,
                'unique_id': obj.buyer.buyer_unique_id,
                'username': obj.buyer.username,
                'email': obj.buyer.email,
                'mobile': obj.buyer.mobile,
                'company': obj.buyer.company_name,
            }
        
        # For others - minimal info
        return {
            'unique_id': obj.buyer.buyer_unique_id,
        }
    
    def get_seller_details(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        
        if user and (user.is_admin or user.is_superuser or user.role == 'super_admin'):
            return {
                'id': obj.seller.id,
                'username': obj.seller.username,
                'email': obj.seller.email,
                'mobile': obj.seller.mobile,
                'company': obj.seller.company_name,
            }
        return {
            'username': obj.seller.username,
        }


class InterestActionSerializer(serializers.Serializer):
    seller_remark = serializers.CharField(required=False, allow_blank=True)
    interest_id = serializers.IntegerField(required=False)


class DealConfirmSerializer(serializers.Serializer):
    admin_remark = serializers.CharField(required=False, allow_blank=True)


class ContractSerializer(serializers.ModelSerializer):
    """Serializer for contracts"""
    product_title = serializers.CharField(source='product.title', read_only=True)
    buyer_name = serializers.CharField(source='buyer.username', read_only=True)
    buyer_unique_id = serializers.CharField(source='buyer.buyer_unique_id', read_only=True)
    seller_name = serializers.CharField(source='seller.username', read_only=True)
    display_seller_id = serializers.SerializerMethodField()
    display_buyer_id = serializers.SerializerMethodField()
    
    class Meta:
        model = Contract
        fields = '__all__'
        read_only_fields = ['contract_id', 'confirmed_at', 'created_at']

    def get_display_seller_id(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        is_admin = bool(user and _is_admin_user(user))
        return get_contract_display_ids(obj, user, is_admin=is_admin)['display_seller_id']

    def get_display_buyer_id(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        is_admin = bool(user and _is_admin_user(user))
        return get_contract_display_ids(obj, user, is_admin=is_admin)['display_buyer_id']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        user = request.user if request else None
        is_admin = bool(user and _is_admin_user(user))
        party_ids = get_contract_display_ids(instance, user, is_admin=is_admin)
        data['seller'] = party_ids['seller_id']
        data['buyer'] = party_ids['buyer_id']
        data['display_seller_id'] = party_ids['display_seller_id']
        data['display_buyer_id'] = party_ids['display_buyer_id']
        if not (is_admin or (user and user.id == instance.buyer_id)):
            data['buyer_unique_id'] = None
        return data
