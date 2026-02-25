from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager,
    Group,
    Permission,
)
from django.utils import timezone
# from django.contrib.auth.models import Permission as DjangoPermission
from django.core import validators
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.core import validators
import os
import random
import string
from datetime import datetime
from decimal import Decimal

def validate_file_size(value):
    max_size = 10 * 1024 * 1024  # 10MB in bytes
    if value.size > max_size:
        raise ValidationError(f'File size must be no more than 5MB. Your file is {value.size / (1024 * 1024):.2f}MB.')


def validate_video_size(value):
    max_size = 50 * 1024 * 1024  # 50MB in bytes
    if value.size > max_size:
        raise ValidationError(f'Video file size must be no more than 50MB. Your file is {value.size / (1024 * 1024):.2f}MB.')

ALLOWED_DOCUMENT_EXTENSIONS = ['jpg', 'jpeg', 'png', 'pdf']
MAX_DOCUMENT_FILE_SIZE = 5 * 1024 * 1024  # 2MB


def validate_document_file_size(value):
    if value.size > MAX_DOCUMENT_FILE_SIZE:
        raise ValidationError('File size must be no more than 2MB.')


def generate_transaction_id():
    """Generate unique transaction ID in format: INT-YYYYMMDD-XXXX"""
    today = datetime.now().strftime('%Y%m%d')
    random_part = f"{random.randint(1000, 9999)}"
    return f"INT-{today}-{random_part}"


def generate_contract_id():
    """Generate unique contract ID in format: CNT-YYYYMMDD-XXXX"""
    today = datetime.now().strftime('%Y%m%d')
    random_part = f"{random.randint(1000, 9999)}"
    return f"CNT-{today}-{random_part}"


def user_document_upload_to(instance, filename):
    user_id = instance.pk or 'temp'
    base, ext = os.path.splitext(filename or '')
    sanitized_ext = ext.lower() if ext else ''
    return f'user_documents/{user_id}/{base}{sanitized_ext}'

# =========================
# Custom User Manager
# =========================
class DaalUserManager(BaseUserManager):
    def create_user(self, username=None, mobile=None, password=None, **extra_fields):
        if not username and not mobile:
            raise ValueError("Username or mobile number is required")
        
        if username:
            username = username.lower()
        
        user = self.model(username=username, mobile=mobile, **extra_fields)
        user.set_password(password)
        user.is_active = True
        user.save(using=self._db)
        return user

    def create_superuser(self, username=None, mobile=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_admin", True)
        extra_fields.setdefault("role", "super_admin")


        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(username, mobile, password, **extra_fields)


# =========================
# Custom User Model
# =========================

class TagMaster(models.Model):
    tag_name = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['tag_name']
        verbose_name = "Tag Master"
        verbose_name_plural = "Tag Master"

    def __str__(self):
        return self.tag_name

class DaalUser(AbstractBaseUser, PermissionsMixin):

    # 🔐 Login field
    username = models.CharField(max_length=100, unique=True)
    profile_image = models.ImageField(upload_to='profile/', blank=True, null=True)

    # 👤 Basic Profile
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    mobile = models.CharField(max_length=15, unique=True, blank=False, null=False, default='')

    # 🧑‍💼 Broker / User type
    is_buyer = models.BooleanField(default=False)
    is_seller = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_transporter = models.BooleanField(default=False)
    is_both_sellerandbuyer = models.BooleanField(default=False)
    
    # 📋 User role with predefined choices
    ROLE_CHOICES = [
        ('super_admin', 'Super Admin'),
        ('admin', 'Admin'),
        ('buyer', 'Buyer'),
        ('seller', 'Seller'),
        ('transporter', 'Transporter'),
        ('both_sellerandbuyer', 'Both Seller and Buyer'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='admin')
    # KYC Status choices
    KYC_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    # User Status choices
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('deactive', 'Deactive'),
        ('suspended', 'Suspended'),
    ]
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    
    # 📄 Legal identification fields
    pan_number = models.CharField(max_length=10, blank=True, null=True)
    gst_number = models.CharField(max_length=15, blank=True, null=True)

    # 🔑 Django required flags
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # ⚠️ SECURITY WARNING: Storing plain text passwords is a serious security vulnerability!
    char_password = models.CharField(max_length=128, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    date_joined = models.DateTimeField(default=timezone.now)
    dob = models.DateField(blank=True, null=True, help_text="Date of birth in YYYY-MM-DD format")
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    # pan_image = models.ImageField(upload_to='pan_images/', blank=True, null=True, validators=[validate_file_size])
    # gst_image = models.ImageField(upload_to='gst_images/', blank=True, null=True, validators=[validate_file_size])
    kyc_status = models.CharField(max_length=20, choices=KYC_STATUS_CHOICES, default='pending')
    company_name = models.CharField(max_length=200, blank=True, null=True)
    brand = models.CharField(max_length=200, blank=True, null=True)
    kyc_submitted_at = models.DateTimeField(blank=True, null=True)
    kyc_approved_at = models.DateTimeField(blank=True, null=True)
    kyc_rejected_at = models.DateTimeField(blank=True, null=True)
    kyc_rejection_reason = models.TextField(blank=True, null=True)
    account_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', db_index=True)
    deactivated_at = models.DateTimeField(blank=True, null=True)
    suspended_at = models.DateTimeField(blank=True, null=True)
    suspension_reason = models.TextField(blank=True, null=True)
    tags = models.ManyToManyField(TagMaster, related_name='users', blank=True)

    buyer_unique_id = models.CharField(
        max_length=20, 
        unique=True, 
        blank=True, 
        null=True, 
        help_text="Unique identifier for buyers to show to sellers"
    )
    pan_image = models.FileField(
        upload_to=user_document_upload_to,
        blank=True,
        null=True,
        help_text="Upload PAN card image",
        validators=[
            validators.FileExtensionValidator(allowed_extensions=ALLOWED_DOCUMENT_EXTENSIONS),
            validate_document_file_size,
        ],
    )
    gst_image = models.FileField(
        upload_to=user_document_upload_to,
        blank=True,
        null=True,
        help_text="Upload GST certificate image",
        validators=[
            validators.FileExtensionValidator(allowed_extensions=ALLOWED_DOCUMENT_EXTENSIONS),
            validate_document_file_size,
        ],
    )
    shopact_image = models.FileField(
        upload_to=user_document_upload_to,
        blank=True,
        null=True,
        help_text="Upload Shop Act document",
        validators=[
            validators.FileExtensionValidator(allowed_extensions=ALLOWED_DOCUMENT_EXTENSIONS),
            validate_document_file_size,
        ],
    )
    adharcard_image = models.FileField(
        upload_to=user_document_upload_to,
        blank=True,
        null=True,
        help_text="Upload Aadhaar card document",
        validators=[
            validators.FileExtensionValidator(allowed_extensions=ALLOWED_DOCUMENT_EXTENSIONS),
            validate_document_file_size,
        ],
    )

    # ✅ Fix reverse accessor conflict
    groups = models.ManyToManyField(
        Group,
        related_name="daaluser_set",
        blank=True,
        help_text="Groups this user belongs to",
    )

    user_permissions = models.ManyToManyField(
        Permission,
        related_name="daaluser_permissions_set",
        blank=True,
        help_text="Specific permissions for this user",
    )

    objects = DaalUserManager()

    USERNAME_FIELD = "mobile"
    REQUIRED_FIELDS = ["username", "email", "first_name"]

    class Meta:
        verbose_name = "DAAL User"
        verbose_name_plural = "DAAL Users"
        indexes = [
            models.Index(fields=['buyer_unique_id']),
        ]

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        if not self.buyer_unique_id and (self.is_buyer or self.role in ('buyer', 'both_sellerandbuyer')):
            today = datetime.now().strftime('%Y%m%d')
            random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            self.buyer_unique_id = f"BUY-{today}-{random_part}"
        super().save(*args, **kwargs)


# Permission System Models

# Define available modules in the system
MODULE_CHOICES = [
    ('user_management', 'User Management'),
    ('branch_management', 'Branch Management'),
    ('category_management', 'Category Management'),
    ('subcategory_management', 'Subcategory Management'),
    ('brand_management', 'Brand Management'),
    ('product_management', 'Product Management'),
    ('product_image_management', 'Product Image Management'),
]

# Define available actions
ACTION_CHOICES = [
    ('create', 'Create'),
    ('read', 'Read'),
    ('update', 'Update'),
    ('delete', 'Delete'),
]


class RolePermission(models.Model):
    """Model to define permissions for each role on different modules"""
    role = models.CharField(max_length=20, choices=DaalUser.ROLE_CHOICES)
    module = models.CharField(max_length=50, choices=MODULE_CHOICES)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    is_allowed = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('role', 'module', 'action')
        verbose_name = "Role Permission"
        verbose_name_plural = "Role Permissions"
        ordering = ['role', 'module', 'action']

    def __str__(self):
        return f"{self.role} - {self.module} - {self.action} ({'Allowed' if self.is_allowed else 'Denied'})"


# Category Master Model
class CategoryMaster(models.Model):
    category_name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    level = models.PositiveIntegerField(default=0)
    path = models.CharField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Category Master"
        verbose_name_plural = "Category Masters"
        ordering = ['path', 'category_name']
        indexes = [
            models.Index(fields=['parent']),
            models.Index(fields=['level']),
            models.Index(fields=['path']),
        ]
    

    def __str__(self):
        return self.category_name
    
    def save(self, *args, **kwargs):
        if self.parent:
            self.level = self.parent.level + 1
            self.path = f"{self.parent.path}{self.id}/" if self.id else f"{self.parent.path}"
        else:
            self.level = 0
            self.path = f"{self.id}/" if self.id else "/"
        
        super().save(*args, **kwargs)
        
        if self.parent and not self.path.endswith(f"{self.id}/"):
            self.path = f"{self.parent.path}{self.id}/"
            super().save(update_fields=['path'])
    
    def get_root_category(self):
        if self.parent:
            return self.parent.get_root_category()
        return self
    
    def get_ancestors(self):
        ancestors = []
        current = self.parent
        while current:
            ancestors.append(current)
            current = current.parent
        return list(reversed(ancestors))
    
    def get_descendants(self):
        descendants = []
        for child in self.children.all():
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants
    
    def get_full_path(self):
        if self.parent:
            return f"{self.parent.get_full_path()} > {self.category_name}"
        return self.category_name
    
    def is_root(self):
        return self.parent is None
    
    def is_leaf(self):
        return not self.children.exists()


subCategoryMaster = CategoryMaster


class BrandMaster(models.Model):
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_INACTIVE, 'Inactive'),
    ]

    brand_unique_id = models.CharField(max_length=20, unique=True, blank=True)
    brand_name = models.CharField(max_length=120, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    created_by = models.ForeignKey(DaalUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_brands')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Brand Master'
        verbose_name_plural = 'Brand Masters'

    def __str__(self):
        return f"{self.brand_unique_id or 'BR???'} - {self.brand_name}"

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating and not self.brand_unique_id:
            self.brand_unique_id = f"BR{self.pk:03d}"
            super().save(update_fields=['brand_unique_id', 'updated_at'])



# Product Model
class Product(models.Model):
    DEAL_STATUS_AVAILABLE = 'available'
    DEAL_STATUS_PARTIALLY_SOLD = 'partially_sold'
    DEAL_STATUS_SELLER_CONFIRMED = 'seller_confirmed'
    DEAL_STATUS_DEAL_CONFIRMED = 'deal_confirmed'
    DEAL_STATUS_OUT_OF_STOCK = 'out_of_stock'
    DEAL_STATUS_SOLD = 'sold'
    DEAL_STATUS_CHOICES = [
        (DEAL_STATUS_AVAILABLE, 'Available'),
        (DEAL_STATUS_PARTIALLY_SOLD, 'Partially Sold'),
        (DEAL_STATUS_SELLER_CONFIRMED, 'Seller Confirmed'),
        (DEAL_STATUS_DEAL_CONFIRMED, 'Deal Confirmed'),
        (DEAL_STATUS_OUT_OF_STOCK, 'Out of Stock'),
        (DEAL_STATUS_SOLD, 'Sold'),
    ]

    STATUS_AVAILABLE = 'available'
    STATUS_SOLD_PENDING_CONFIRMATION = 'sold_pending_confirmation'
    STATUS_SOLD = 'sold'
    STATUS_OUT_OF_STOCK = 'out_of_stock'
    STATUS_CHOICES = [
        (STATUS_AVAILABLE, 'Available'),
        (STATUS_SOLD_PENDING_CONFIRMATION, 'Sold Pending Confirmation'),
        (STATUS_SOLD, 'Sold'),
        (STATUS_OUT_OF_STOCK, 'Out of Stock'),
    ]
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(CategoryMaster, on_delete=models.CASCADE, related_name='products')
    root_category = models.ForeignKey(CategoryMaster, on_delete=models.CASCADE, related_name='root_products', null=True, blank=True)
    category_path = models.TextField(blank=True, null=True)
    brand = models.ForeignKey(BrandMaster, on_delete=models.SET_NULL, related_name='products', null=True, blank=True)
    seller = models.ForeignKey(DaalUser, on_delete=models.CASCADE, related_name='products')
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )
    amount_unit = models.CharField(max_length=10, choices=[('kg', 'KG'), ('ton', 'TON'), ('qtl', 'QUINTAL')], default='kg')
    
    # ✅ Stock management fields
    original_quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, 
                                           help_text='Original quantity when product was created')
    remaining_quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                            help_text='Remaining quantity available for sale')
    quantity_unit = models.CharField(max_length=10, choices=[('kg', 'KG'), ('ton', 'TON'), ('qtl', 'QUINTAL')], 
                                    default='kg', null=True, blank=True)
    
    # ✅ Loading from-to fields
    loading_from = models.CharField(max_length=200, blank=True, null=True, help_text="Loading from location")
    loading_to = models.CharField(max_length=200, blank=True, null=True, help_text="Loading to location")
    remark = models.TextField(blank=True, null=True)
    loading_location = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    deal_status = models.CharField(max_length=30, choices=DEAL_STATUS_CHOICES, default=DEAL_STATUS_AVAILABLE, db_index=True)
    status = models.CharField(max_length=40, choices=STATUS_CHOICES, default=STATUS_AVAILABLE, db_index=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.seller.username}"

    def clean(self):
        if not self.title:
            raise ValidationError({'title': 'Title required'})
        if self.amount <= 0:
            raise ValidationError({'amount': 'Amount must be > 0'})
        if self.original_quantity and self.original_quantity <= 0:
            raise ValidationError({'original_quantity': 'Quantity must be > 0'})

    def save(self, *args, **kwargs):
        # Set initial quantities when creating product
        if not self.pk:
            if self.original_quantity is None and self.remaining_quantity is not None:
                self.original_quantity = self.remaining_quantity
            elif self.remaining_quantity is None and self.original_quantity is not None:
                self.remaining_quantity = self.original_quantity
        
        if self.category:
            root = self.category.get_root_category()
            self.root_category = root
            import json
            self.category_path = json.dumps({
                "root": root.category_name,
                "selected": self.category.category_name,
                "full_path": self.category.get_full_path()
            })
        super().save(*args, **kwargs)

    def update_stock_after_deal(self, sold_quantity):
        """Update remaining quantity after a deal is confirmed"""
        current_remaining = self.remaining_quantity
        if current_remaining is None:
            current_remaining = self.original_quantity or Decimal('0')

        current_remaining -= Decimal(str(sold_quantity))

        if current_remaining <= 0:
            self.remaining_quantity = Decimal('0')
            self.deal_status = self.DEAL_STATUS_OUT_OF_STOCK
            self.status = self.STATUS_OUT_OF_STOCK
            self.is_active = False
        else:
            self.remaining_quantity = current_remaining
            self.deal_status = self.DEAL_STATUS_PARTIALLY_SOLD
            self.status = self.STATUS_AVAILABLE

        self.save(update_fields=['remaining_quantity', 'deal_status', 'status', 'is_active', 'updated_at'])

    def add_stock(self, added_quantity):
        """Increase available stock (does not replace existing remaining quantity)."""
        qty = Decimal(str(added_quantity))
        if qty <= 0:
            raise ValidationError({'quantity': 'Added quantity must be greater than 0.'})

        current_remaining = self.remaining_quantity if self.remaining_quantity is not None else (self.original_quantity or Decimal('0'))
        current_original = self.original_quantity if self.original_quantity is not None else current_remaining

        self.remaining_quantity = current_remaining + qty
        self.original_quantity = current_original + qty

        if self.remaining_quantity <= 0:
            self.remaining_quantity = Decimal('0')
            self.deal_status = self.DEAL_STATUS_OUT_OF_STOCK
            self.status = self.STATUS_OUT_OF_STOCK
            self.is_active = False
        else:
            self.deal_status = (
                self.DEAL_STATUS_AVAILABLE
                if self.remaining_quantity == self.original_quantity
                else self.DEAL_STATUS_PARTIALLY_SOLD
            )
            self.status = self.STATUS_AVAILABLE
            self.is_active = True

        self.save(update_fields=['original_quantity', 'remaining_quantity', 'deal_status', 'status', 'is_active', 'updated_at'])


# Product Image Model
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_images/')
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Product Image"
        verbose_name_plural = "Product Images"
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['product'],
                condition=Q(is_primary=True),
                name='unique_primary_image_per_product',
            ),
        ]
    
    def __str__(self):
        return f"Image for {self.product.title}"

    def clean(self):
        if self.is_primary and ProductImage.objects.filter(product=self.product, is_primary=True).exclude(id=self.id).exists():
            raise ValidationError({'is_primary': 'Only one primary image is allowed per product.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class ProductVideo(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='videos')
    video = models.FileField(upload_to='product_videos/', validators=[validators.FileExtensionValidator(allowed_extensions=['mp4', 'mov', 'avi', 'webm']), validate_video_size])
    title = models.CharField(max_length=200, blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Product Video"
        verbose_name_plural = "Product Videos"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Video for {self.product.title}" if not self.title else f"{self.title} - {self.product.title}"

    def clean(self):
        if self.is_primary and ProductVideo.objects.filter(product=self.product, is_primary=True).exclude(id=self.id).exists():
            raise ValidationError({'is_primary': 'Only one primary video is allowed per product.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class ProductInterest(models.Model):
    STATUS_INTERESTED = 'interested'
    STATUS_SELLER_CONFIRMED = 'seller_confirmed'
    STATUS_DEAL_CONFIRMED = 'deal_confirmed'
    STATUS_REJECTED = 'rejected'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_INTERESTED, 'Interested'),
        (STATUS_SELLER_CONFIRMED, 'Seller Confirmed'),
        (STATUS_DEAL_CONFIRMED, 'Deal Confirmed'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_CANCELLED, 'Cancelled')
    ]
    transaction_id = models.CharField(max_length=20, unique=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='interests')
    buyer = models.ForeignKey(DaalUser, on_delete=models.CASCADE, related_name='product_interests')
    seller = models.ForeignKey(DaalUser, on_delete=models.CASCADE, related_name='received_product_interests')
    # ✅ Snapshot of product at time of interest
    snapshot_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    snapshot_quantity = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # ✅ Buyer's offer details
    buyer_offered_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    buyer_required_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    
    # ✅ Loading from-to for this specific interest
    loading_from = models.CharField(max_length=200, blank=True, null=True)
    loading_to = models.CharField(max_length=200, blank=True, null=True)
    
    buyer_remark = models.TextField(blank=True, null=True)
    seller_remark = models.TextField(blank=True, null=True)
    superadmin_remark = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_INTERESTED, db_index=True)
    delivery_date = models.DateField(null=True, blank=True, db_index=True)
    deal_confirmed_at = models.DateTimeField(null=True, blank=True)
    negotiation_history = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'status']),
            models.Index(fields=['seller', 'status']),
            models.Index(fields=['buyer', 'status']),
            models.Index(fields=['transaction_id']),
        ]
        verbose_name = "Product Interest"
        verbose_name_plural = "Product Interests"

    def __str__(self):
        buyer_display = self.buyer.buyer_unique_id if self.buyer.buyer_unique_id else self.buyer.username
        return f'Interest: {self.transaction_id} / {self.product.title} / {buyer_display} / {self.status}'

    def clean(self):
        if self.product_id and self.seller_id and self.product.seller_id != self.seller_id:
            raise ValidationError({'seller': 'Seller must match product owner.'})
        if self.product_id and self.buyer_id == self.product.seller_id:
            raise ValidationError({'buyer': 'Seller cannot show interest in own product.'})
        if self.buyer_offered_amount is not None and self.buyer_offered_amount <= 0:
            raise ValidationError({'buyer_offered_amount': 'Offered amount must be greater than 0.'})
        if self.buyer_required_quantity is not None and self.buyer_required_quantity <= 0:
            raise ValidationError({'buyer_required_quantity': 'Required quantity must be greater than 0.'})

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = generate_transaction_id()

        if not self.pk and self.product:
            self.snapshot_amount = self.product.amount
            self.snapshot_quantity = self.product.remaining_quantity or self.product.original_quantity

        if self.pk:
            try:
                old = ProductInterest.objects.get(pk=self.pk)
                if old.status != self.status:
                    history_entry = {
                        'action': f'status_changed_to_{self.status}',
                        'from_status': old.status,
                        'to_status': self.status,
                        'timestamp': timezone.now().isoformat()
                    }
                    if not self.negotiation_history:
                        self.negotiation_history = []
                    history_list = list(self.negotiation_history)
                    history_list.append(history_entry)
                    self.negotiation_history = history_list
            except ProductInterest.DoesNotExist:
                pass

        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def buyer_display_id(self):
        return self.buyer.buyer_unique_id or f"BUY-{self.buyer.id:06d}"


class Contract(models.Model):
    """Model for confirmed deals/contracts"""
    contract_id = models.CharField(max_length=20, unique=True, blank=True)
    interest = models.OneToOneField(ProductInterest, on_delete=models.CASCADE, related_name='contract')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='contracts')
    buyer = models.ForeignKey(DaalUser, on_delete=models.CASCADE, related_name='buyer_contracts')
    seller = models.ForeignKey(DaalUser, on_delete=models.CASCADE, related_name='seller_contracts')
    
    # ✅ Snapshot of deal at confirmation time
    deal_amount = models.DecimalField(max_digits=12, decimal_places=2)
    deal_quantity = models.DecimalField(max_digits=12, decimal_places=2)
    amount_unit = models.CharField(max_length=10)
    quantity_unit = models.CharField(max_length=10)
    
    # ✅ Loading details
    loading_from = models.CharField(max_length=200)
    loading_to = models.CharField(max_length=200)
    
    # ✅ Remarks
    buyer_remark = models.TextField(blank=True, null=True)
    seller_remark = models.TextField(blank=True, null=True)
    admin_remark = models.TextField(blank=True, null=True)
    
    # ✅ Timestamps
    confirmed_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # ✅ Status (for admin CRUD)
    STATUS_ACTIVE = 'active'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    
    class Meta:
        ordering = ['-confirmed_at']
        verbose_name = "Contract"
        verbose_name_plural = "Contracts"
    
    def __str__(self):
        return f"Contract: {self.contract_id} - {self.product.title}"
    
    def save(self, *args, **kwargs):
        if not self.contract_id:
            self.contract_id = generate_contract_id()
        super().save(*args, **kwargs)
        

#16 feb
class BranchMaster(models.Model):
    location_name = models.CharField(max_length=150)
    state = models.CharField(max_length=120)
    city = models.CharField(max_length=120)
    area = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Branch Master"
        verbose_name_plural = "Branch Masters"
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['state', 'city', 'area'], name='unique_branch_state_city_area'),
        ]
        indexes = [
            models.Index(fields=['state']),
            models.Index(fields=['city']),
            models.Index(fields=['area']),
        ]

    def __str__(self):
        return f"{self.location_name} - {self.state}, {self.city}, {self.area}"

    def clean(self):
        if not (self.location_name or '').strip():
            raise ValidationError({'location_name': 'Location name is required.'})
        if not (self.state or '').strip():
            raise ValidationError({'state': 'State is required.'})
        if not (self.city or '').strip():
            raise ValidationError({'city': 'City is required.'})
        if not (self.area or '').strip():
            raise ValidationError({'area': 'Area is required.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


