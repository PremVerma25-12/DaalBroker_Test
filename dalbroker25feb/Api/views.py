from django.contrib.auth import authenticate, logout as django_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.apps import apps
from django.db import transaction
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.db.models import Q
import logging
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action, api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import PermissionDenied
from brokers_app.models import *
from .permission import *
from .serializers import *
from .utils import *
from .utils import _is_admin_user, _is_seller_user, _is_buyer_user
from brokers_app.utils import (
    has_permission,
    can_user_perform_action,
    get_user_status,
    normalize_user_status,
    get_contract_display_ids,
)
from django.db.models import Q, Count, Sum, F, DecimalField, Avg
from django.db.models.functions import Coalesce
from decimal import Decimal
from brokers_app.views import (
    product_create_ajax as web_product_create_ajax,
    product_get_ajax as web_product_get_ajax,
    product_update_ajax as web_product_update_ajax,
    product_delete_ajax as web_product_delete_ajax,
    product_toggle_ajax as web_product_toggle_ajax,
    product_update_stock_ajax as web_product_update_stock_ajax,
    offers_list_ajax as web_offers_list_ajax,
    branch_create_ajax as web_branch_create_ajax,
    branch_update_ajax as web_branch_update_ajax,
    branch_toggle_status_ajax as web_branch_toggle_status_ajax,
    branch_delete_ajax as web_branch_delete_ajax,
    brand_create_ajax as web_brand_create_ajax,
    brand_get_ajax as web_brand_get_ajax,
    brand_update_ajax as web_brand_update_ajax,
    brand_delete_ajax as web_brand_delete_ajax,
    user_create_ajax as web_user_create_ajax,
    get_user_data as web_get_user_data,
    user_update_ajax as web_user_update_ajax,
    user_update_status_ajax as web_user_update_status_ajax,
    user_delete_ajax as web_user_delete_ajax,
)

DEFAULT_PAGE_SIZE = 10
logger = logging.getLogger(__name__)
USER_STATUS_ACTIVE = 'active'
USER_STATUS_DEACTIVATED = 'deactivated'
USER_STATUS_SUSPENDED = 'suspended'
PENDING_INTEREST_STATUSES = (
    ProductInterest.STATUS_INTERESTED,
    ProductInterest.STATUS_SELLER_CONFIRMED,
)


def _effective_user_status(user):
    return normalize_user_status(get_user_status(user))


def _create_user_from_registration_data(validated_data):
    plain_password = generate_registration_password(validated_data['first_name'], validated_data['mobile'])
    normalized_role = validated_data['role']

    user = DaalUser(
        username=validated_data['mobile'],
        mobile=validated_data['mobile'],
        email=validated_data['email'],
        first_name=validated_data['first_name'],
        last_name=validated_data.get('last_name', ''),
        role=normalized_role,
        pan_number=validated_data.get('pan_number'),
        gst_number=validated_data.get('gst_number'),
        gender=validated_data.get('gender'),
        dob=validated_data.get('dob'),
        kyc_status='pending',
        kyc_submitted_at=timezone.now(),
        kyc_rejection_reason='',
        status='active',
        account_status='active',
        is_active=True,
        char_password=plain_password,
    )
    user.set_password(plain_password)
    apply_role_flags(user, normalized_role)
    user.save()

    # Save document uploads after primary key is created so upload path uses user ID.
    user.pan_image = validated_data.get('pan_image')
    user.gst_image = validated_data.get('gst_image')
    user.shopact_image = validated_data.get('shopact_image')
    user.adharcard_image = validated_data.get('adharcard_image')
    user.save(update_fields=[
        'pan_image', 'gst_image', 'shopact_image', 'adharcard_image'
    ])
    return user, plain_password


def _build_pagination_window(page_obj):
    total_pages = page_obj.paginator.num_pages
    current_page = page_obj.number

    important_pages = {
        1, 2, 3,
        total_pages - 1, total_pages,
        current_page - 1, current_page, current_page + 1,
    }
    page_numbers = sorted({page for page in important_pages if 1 <= page <= total_pages})

    window = []
    last_page = None
    for page in page_numbers:
        if last_page is not None and page - last_page > 1:
            window.append(None)
        window.append(page)
        last_page = page
    return window


def _paginate_queryset(request, queryset, page_param='page', page_size=DEFAULT_PAGE_SIZE):
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(request.GET.get(page_param))

    query_params = request.GET.copy()
    if page_param in query_params:
        query_params.pop(page_param)

    return page_obj, {
        'page_param': page_param,
        'querystring': query_params.urlencode(),
        'window': _build_pagination_window(page_obj),
    }


def _parse_bool(value):
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def _action_guard_response(user):
    allowed, reason = can_user_perform_action(user)
    if allowed:
        return None
    return Response({'success': False, 'message': reason}, status=status.HTTP_403_FORBIDDEN)


def _normalize_tag_ids(raw_tag_ids):
    if raw_tag_ids is None:
        return []
    if isinstance(raw_tag_ids, (str, int)):
        raw_tag_ids = [raw_tag_ids]
    normalized = []
    for value in raw_tag_ids:
        text = str(value).strip()
        if not text:
            continue
        if not text.isdigit():
            raise serializers.ValidationError({'tag_ids': 'Tag IDs must be numeric.'})
        normalized.append(int(text))
    # preserve order, remove duplicates
    seen = set()
    unique = []
    for tag_id in normalized:
        if tag_id in seen:
            continue
        seen.add(tag_id)
        unique.append(tag_id)
    return unique


def _extract_tag_ids(request):
    if hasattr(request.data, 'getlist'):
        tag_ids = request.data.getlist('tag_ids')
    else:
        tag_ids = request.data.get('tag_ids', [])
    return _normalize_tag_ids(tag_ids)


class TokenViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        mobile = request.data.get('mobile') or request.data.get('username')
        password = request.data.get('password')
        if not mobile or not password:
            return Response({'detail': 'mobile/username and password are required'}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, mobile=mobile, password=password) or authenticate(request, username=mobile, password=password)
        if user is None:
            return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        current_status = _effective_user_status(user)
        if current_status == USER_STATUS_SUSPENDED:
            if should_send_suspension_email(user.id):
                send_account_suspended_email_async(user.email, getattr(user, 'suspension_reason', ''))
            return Response({'detail': 'Your account has been suspended. Check your email.'}, status=status.HTTP_403_FORBIDDEN)
        if current_status == USER_STATUS_DEACTIVATED:
            return Response({'detail': 'Your account has been deactivated. Please contact admin.'}, status=status.HTTP_403_FORBIDDEN)

        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'username': user.username,
                'role': user.role,
                'kyc_status': user.kyc_status,
                'status': current_status,
                'account_status': current_status,
            },
        })

    @action(detail=False, methods=['get'], url_path='all-with-details')
    def all_with_details(self, request):
        """Get all categories with full details for display - with proper indentation"""
        categories = CategoryMaster.objects.filter(is_active=True).order_by('level', 'category_name')
        data = []
        for cat in categories:
                data.append({
                    'id': cat.id,
                    'name': cat.category_name,
                    'level': cat.level,
                    'parent_id': cat.parent_id if cat.parent else None,
                    'parent_name': cat.parent.category_name if cat.parent else None,
                    'full_path': cat.get_full_path(),
                    'is_active': cat.is_active,
                    'created_at': cat.created_at,
                    'updated_at': cat.updated_at,
                    'children_count': cat.children.count(),
                    'display_name': '— ' * cat.level + cat.category_name  # Indented name for dropdowns
                })
        return Response(data)


@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def register_api(request):
    serializer = RegistrationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        with transaction.atomic():
            user, plain_password = _create_user_from_registration_data(serializer.validated_data)
            transaction.on_commit(
                lambda: send_welcome_credentials_email_async(user.email, user.username, plain_password)
            )
    except Exception as exc:
        logger.exception('Registration failed for mobile=%s email=%s', request.data.get('mobile'), request.data.get('email'))
        return Response({
            'status': 'error',
            'message': 'Registration failed. Please try again.',
            'detail': str(exc),
        }, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        'status': 'success',
        'message': 'Registration successful. Credentials sent to email.',
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_api(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    mobile = serializer.validated_data['mobile']
    password = serializer.validated_data['password']
    user = authenticate(request, mobile=mobile, password=password) or authenticate(request, username=mobile, password=password)
    if user is None:
        return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    current_status = _effective_user_status(user)
    if current_status == USER_STATUS_SUSPENDED:
        if should_send_suspension_email(user.id):
            send_account_suspended_email_async(user.email, getattr(user, 'suspension_reason', ''))
        return Response({'detail': 'Your account has been suspended. Check your email.'}, status=status.HTTP_403_FORBIDDEN)
    if current_status == USER_STATUS_DEACTIVATED:
        return Response({'detail': 'Your account has been deactivated. Please contact admin.'}, status=status.HTTP_403_FORBIDDEN)

    refresh = RefreshToken.for_user(user)
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': {
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'kyc_status': user.kyc_status,
            'status': current_status,
            'account_status': current_status,
        },
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_api(request):
    """
    Mobile logout endpoint.
    Session logout always happens; refresh blacklisting is attempted only if
    token blacklist app is installed and refresh token is provided.
    """
    refresh_token = (request.data.get('refresh') or '').strip()
    token_blacklisted = False

    if refresh_token and apps.is_installed('rest_framework_simplejwt.token_blacklist'):
        try:
            RefreshToken(refresh_token).blacklist()
            token_blacklisted = True
        except Exception:
            token_blacklisted = False

    django_logout(request)
    return Response({
        'success': True,
        'message': 'Logged out successfully.',
        'token_blacklisted': token_blacklisted,
        'note': 'Please clear local access/refresh tokens on mobile client.',
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password_api(request):
    serializer = ForgotPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data['email']

    user = DaalUser.objects.filter(email=email).first()
    if user:
        try:
            with transaction.atomic():
                new_password = generate_secure_password(8)
                user.set_password(new_password)
                user.char_password = new_password
                user.save(update_fields=['password', 'char_password'])
                if not send_forgot_password_email(email, new_password):
                    raise RuntimeError('Forgot-password email delivery failed.')
        except Exception:
            logger.exception('Forgot-password flow failed for email=%s', email)
            return Response(
                {'message': 'Unable to send reset password email right now. Please try again shortly.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    return Response({'message': 'If account exists, password has been sent.'}, status=status.HTTP_200_OK)


# ✅ User Management APIs - Sirf Admin
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminRole])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def add_user_api(request):
    serializer = RegistrationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    tag_ids = _extract_tag_ids(request)
    if len(tag_ids) < 1 or len(tag_ids) > 15:
        return Response(
            {'message': 'Please select at least 1 and maximum 15 tags.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    tags = list(TagMaster.objects.filter(id__in=tag_ids))
    if len(tags) != len(tag_ids):
        return Response({'message': 'One or more selected tags are invalid.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        with transaction.atomic():
            user, plain_password = _create_user_from_registration_data(serializer.validated_data)
            user.tags.set(tags)
            transaction.on_commit(
                lambda: send_welcome_credentials_email_async(user.email, user.username, plain_password)
            )
    except Exception as exc:
        logger.exception('Add user failed for mobile=%s email=%s by user=%s', request.data.get('mobile'), request.data.get('email'), request.user.id)
        return Response({
            'status': 'error',
            'message': 'User creation failed. Please try again.',
            'detail': str(exc),
        }, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        'status': 'success',
        'message': 'User created successfully. Credentials sent to email.',
        'user_id': user.id,
    }, status=status.HTTP_201_CREATED)


# ✅ Tag Management APIs - Admin aur Seller dono
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSellerOrAdminRole])
def admin_tag_create_api(request):
    tag_name = (request.data.get('tag_name') or '').strip()
    if len(tag_name) < 2 or len(tag_name) > 50:
        return Response({'message': 'Tag name must be between 2 and 50 characters.'}, status=status.HTTP_400_BAD_REQUEST)
    if TagMaster.objects.filter(tag_name__iexact=tag_name).exists():
        return Response({'message': 'Tag name already exists.'}, status=status.HTTP_400_BAD_REQUEST)

    tag = TagMaster.objects.create(tag_name=tag_name)
    return Response({
        'success': True,
        'message': 'Tag created successfully.',
        'tag': {
            'id': tag.id,
            'tag_name': tag.tag_name,
            'created_at': tag.created_at.strftime('%d/%m/%Y %H:%M'),
            'updated_at': tag.updated_at.strftime('%d/%m/%Y %H:%M'),
            'assigned_users_count': 0,
        }
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSellerOrAdminRole])
def admin_tag_list_api(request):
    search = (request.GET.get('search') or '').strip()
    queryset = TagMaster.objects.all().order_by('tag_name')
    if search:
        queryset = queryset.filter(tag_name__icontains=search)

    page_obj, _ = _paginate_queryset(request, queryset, page_size=10)
    results = []
    for tag in page_obj.object_list:
        results.append({
            'id': tag.id,
            'tag_name': tag.tag_name,
            'created_at': tag.created_at.strftime('%d/%m/%Y %H:%M'),
            'updated_at': tag.updated_at.strftime('%d/%m/%Y %H:%M'),
            'assigned_users_count': tag.users.count(),
        })

    return Response({
        'success': True,
        'results': results,
        'pagination': {
            'page': page_obj.number,
            'num_pages': page_obj.paginator.num_pages,
            'count': page_obj.paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        }
    }, status=status.HTTP_200_OK)


@api_view(['PUT'])
@permission_classes([IsAuthenticated, IsSellerOrAdminRole])
def admin_tag_update_api(request, tag_id):
    tag = TagMaster.objects.filter(id=tag_id).first()
    if not tag:
        return Response({'message': 'Tag not found.'}, status=status.HTTP_404_NOT_FOUND)

    tag_name = (request.data.get('tag_name') or '').strip()
    if len(tag_name) < 2 or len(tag_name) > 50:
        return Response({'message': 'Tag name must be between 2 and 50 characters.'}, status=status.HTTP_400_BAD_REQUEST)
    if TagMaster.objects.filter(tag_name__iexact=tag_name).exclude(id=tag.id).exists():
        return Response({'message': 'Tag name already exists.'}, status=status.HTTP_400_BAD_REQUEST)

    tag.tag_name = tag_name
    tag.save(update_fields=['tag_name', 'updated_at'])
    return Response({
        'success': True,
        'message': 'Tag updated successfully.',
        'tag': {
            'id': tag.id,
            'tag_name': tag.tag_name,
            'created_at': tag.created_at.strftime('%d/%m/%Y %H:%M'),
            'updated_at': tag.updated_at.strftime('%d/%m/%Y %H:%M'),
            'assigned_users_count': tag.users.count(),
        }
    }, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsSellerOrAdminRole])
def admin_tag_delete_api(request, tag_id):
    tag = TagMaster.objects.filter(id=tag_id).first()
    if not tag:
        return Response({'message': 'Tag not found.'}, status=status.HTTP_404_NOT_FOUND)

    assigned_count = tag.users.count()
    force_delete = str(request.GET.get('force') or '').strip().lower() in {'1', 'true', 'yes'}
    if assigned_count > 0 and not force_delete:
        return Response({
            'success': False,
            'message': f'Tag is assigned to {assigned_count} user(s). Confirm deletion to continue.',
            'assigned_users_count': assigned_count,
            'requires_confirmation': True,
        }, status=status.HTTP_409_CONFLICT)

    if assigned_count > 0:
        tag.users.clear()
    tag.delete()
    return Response({'success': True, 'message': 'Tag deleted successfully.'}, status=status.HTTP_200_OK)


# ✅ KYC APIs - Sirf Admin
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminRole])
def kyc_list_api(request):
    queryset = DaalUser.objects.exclude(role='admin').order_by('-date_joined')
    page_obj, pagination = _paginate_queryset(request, queryset)
    data = [{
        'id': u.id,
        'name': f'{u.first_name or ""} {u.last_name or ""}'.strip() or u.username,
        'mobile': u.mobile,
        'email': u.email,
        'role': u.role,
        'pan_number': u.pan_number,
        'gst_number': u.gst_number,
        'kyc_status': u.kyc_status,
        'kyc_submitted_at': u.kyc_submitted_at,
        'kyc_approved_at': u.kyc_approved_at,
        'kyc_rejected_at': u.kyc_rejected_at,
        'kyc_rejection_reason': u.kyc_rejection_reason or '',
        'account_status': u.account_status,
    } for u in page_obj.object_list]
    return Response({
        'results': data,
        'pagination': {
            'page': page_obj.number,
            'num_pages': page_obj.paginator.num_pages,
            'count': page_obj.paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'window': pagination['window'],
        }
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mobile_kyc_list_api(request):
    """
    Mobile KYC listing endpoint.
    Kept separate from /api/kyc/ because that path is currently used for HTML page.
    """
    if not _is_admin_user(request.user):
        return Response({'success': False, 'message': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    queryset = DaalUser.objects.exclude(role='admin').order_by('-date_joined')

    search = (request.GET.get('search') or '').strip()
    if search:
        queryset = queryset.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(username__icontains=search)
            | Q(email__icontains=search)
            | Q(mobile__icontains=search)
        )

    role = (request.GET.get('role') or '').strip()
    if role:
        queryset = queryset.filter(role=role)

    kyc_status = (request.GET.get('kyc_status') or '').strip()
    if kyc_status:
        queryset = queryset.filter(kyc_status=kyc_status)

    page_obj, pagination = _paginate_queryset(request, queryset)
    results = [{
        'id': u.id,
        'name': f'{u.first_name or ""} {u.last_name or ""}'.strip() or u.username,
        'username': u.username,
        'mobile': u.mobile,
        'email': u.email,
        'role': u.role,
        'kyc_status': u.kyc_status,
        'pan_number': u.pan_number,
        'gst_number': u.gst_number,
        'kyc_submitted_at': u.kyc_submitted_at,
        'kyc_approved_at': u.kyc_approved_at,
        'kyc_rejected_at': u.kyc_rejected_at,
        'kyc_rejection_reason': u.kyc_rejection_reason or '',
        'account_status': u.account_status,
    } for u in page_obj.object_list]

    return Response({
        'success': True,
        'results': results,
        'pagination': {
            'page': page_obj.number,
            'num_pages': page_obj.paginator.num_pages,
            'count': page_obj.paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'window': pagination['window'],
        }
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mobile_brand_list_api(request):
    """
    Mobile brand listing endpoint (JSON).
    Web /brands/ page remains unchanged.
    """
    role = (getattr(request.user, 'role', '') or '').strip().lower()
    can_read = (
        _is_admin_user(request.user)
        or role in {'buyer', 'super_admin'}
        or has_permission(request.user, 'brand_management', 'read')
    )
    if not can_read:
        return Response({'success': False, 'message': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    queryset = BrandMaster.objects.select_related('created_by').order_by('-created_at')
    search = (request.GET.get('search') or '').strip()
    if search:
        queryset = queryset.filter(brand_name__icontains=search)

    status_filter = (request.GET.get('status') or '').strip().lower()
    if status_filter in {BrandMaster.STATUS_ACTIVE, BrandMaster.STATUS_INACTIVE}:
        queryset = queryset.filter(status=status_filter)

    page_obj, pagination = _paginate_queryset(request, queryset)
    results = [{
        'id': brand.id,
        'brand_unique_id': brand.brand_unique_id,
        'brand_name': brand.brand_name,
        'status': brand.status,
        'created_by': brand.created_by.username if brand.created_by else '-',
        'created_at': brand.created_at.strftime('%d/%m/%y'),
        'updated_at': brand.updated_at.strftime('%d/%m/%y'),
    } for brand in page_obj.object_list]

    return Response({
        'success': True,
        'results': results,
        'pagination': {
            'page': page_obj.number,
            'num_pages': page_obj.paginator.num_pages,
            'count': page_obj.paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'window': pagination['window'],
        }
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminRole])
def kyc_approve_api(request, user_id):
    with transaction.atomic():
        user = DaalUser.objects.select_for_update().filter(id=user_id).first()
        if not user:
            return Response({'message': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        user.kyc_status = 'approved'
        user.kyc_submitted_at = user.kyc_submitted_at or timezone.now()
        user.kyc_approved_at = timezone.now()
        user.kyc_rejected_at = None
        user.kyc_rejection_reason = ''
        user.save(update_fields=['kyc_status', 'kyc_submitted_at', 'kyc_approved_at', 'kyc_rejected_at', 'kyc_rejection_reason'])
    send_kyc_status_email_async(user.email, 'approved')
    return Response({'message': 'KYC approved successfully.'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminRole])
def kyc_reject_api(request, user_id):
    serializer = KYCRejectSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    with transaction.atomic():
        user = DaalUser.objects.select_for_update().filter(id=user_id).first()
        if not user:
            return Response({'message': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        reason = serializer.validated_data['rejection_reason']
        user.kyc_status = 'rejected'
        user.kyc_submitted_at = user.kyc_submitted_at or timezone.now()
        user.kyc_approved_at = None
        user.kyc_rejected_at = timezone.now()
        user.kyc_rejection_reason = reason
        user.save(update_fields=['kyc_status', 'kyc_submitted_at', 'kyc_approved_at', 'kyc_rejected_at', 'kyc_rejection_reason'])
    send_kyc_status_email_async(user.email, 'rejected', reason)
    return Response({'message': 'KYC rejected successfully.'}, status=status.HTTP_200_OK)


# ✅ User Profile APIs - Sab logged in users
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_profile_image_api(request):
    image_file = request.FILES.get('profile_image')
    if not image_file:
        return Response({'success': False, 'message': 'Profile image is required.'}, status=status.HTTP_400_BAD_REQUEST)
    if not str(getattr(image_file, 'content_type', '')).startswith('image/'):
        return Response({'success': False, 'message': 'Only image files are allowed.'}, status=status.HTTP_400_BAD_REQUEST)

    user = request.user
    user.profile_image = image_file
    user.save(update_fields=['profile_image'])

    return Response({
        'success': True,
        'message': 'Profile image updated successfully.',
        'profile_image_url': user.profile_image.url if user.profile_image else '',
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def session_token_api(request):
    """
    Issue JWT tokens for authenticated session users.
    Used by template pages so frontend guards can bootstrap tokens safely.
    """
    current_status = _effective_user_status(request.user)
    refresh = RefreshToken.for_user(request.user)
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': {
            'id': request.user.id,
            'username': request.user.username,
            'role': request.user.role,
            'kyc_status': request.user.kyc_status,
            'status': current_status,
            'account_status': current_status,
        },
    }, status=status.HTTP_200_OK)


# ✅ Filter APIs - Sab logged in users (data filtered by role)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def product_filter_api(request):
    user = request.user
    queryset = Product.objects.select_related('category', 'seller').prefetch_related('interests').order_by('-created_at')

    if _is_admin_user(user):
        base_q = Q()
    elif _is_seller_user(user):
        base_q = Q(seller=user)
    elif _is_buyer_user(user):
        base_q = Q(is_active=True)
    else:
        return Response({'results': [], 'pagination': {'count': 0, 'num_pages': 0, 'page': 1}}, status=status.HTTP_200_OK)

    filters_q = Q()

    title = (request.GET.get('title') or '').strip()
    if title:
        filters_q &= Q(title__icontains=title)

    min_price = (request.GET.get('min_price') or '').strip()
    if min_price:
        try:
            filters_q &= Q(amount__gte=min_price)
        except Exception:
            pass

    max_price = (request.GET.get('max_price') or '').strip()
    if max_price:
        try:
            filters_q &= Q(amount__lte=max_price)
        except Exception:
            pass

    if request.GET.get('is_active', '').strip() != '':
        filters_q &= Q(is_active=_parse_bool(request.GET.get('is_active')))

    product_status = (request.GET.get('status') or '').strip()
    if product_status:
        filters_q &= Q(status=product_status)

    from_date = (request.GET.get('from_date') or '').strip()
    if from_date:
        filters_q &= Q(created_at__date__gte=from_date)

    to_date = (request.GET.get('to_date') or '').strip()
    if to_date:
        filters_q &= Q(created_at__date__lte=to_date)

    category_id = (request.GET.get('category_id') or '').strip()
    if category_id:
        filters_q &= Q(category_id=category_id)

    subcategory_id = (request.GET.get('subcategory_id') or '').strip()
    if subcategory_id:
        filters_q &= (Q(category_id=subcategory_id) | Q(category__parent_id=subcategory_id))

    seller_id = (request.GET.get('seller_id') or '').strip()
    if seller_id:
        filters_q &= Q(seller_id=seller_id)

    seller_mobile = (request.GET.get('seller_mobile') or '').strip()
    if seller_mobile:
        filters_q &= Q(seller__mobile__icontains=seller_mobile)

    seller_email = (request.GET.get('seller_email') or '').strip()
    if seller_email:
        filters_q &= Q(seller__email__icontains=seller_email)

    if request.GET.get('interested', '').strip() != '':
        if _parse_bool(request.GET.get('interested')):
            filters_q &= Q(interests__is_active=True, interests__status__in=PENDING_INTEREST_STATUSES)

    if request.GET.get('approved', '').strip() != '':
        if _parse_bool(request.GET.get('approved')):
            filters_q &= (
                Q(status=Product.STATUS_SOLD_PENDING_CONFIRMATION)
                | Q(status=Product.STATUS_SOLD)
                | Q(interests__status='seller_confirmed')
                | Q(interests__status='deal_confirmed')
            )

    search = (request.GET.get('search') or '').strip()
    if search:
        filters_q &= (
            Q(title__icontains=search)
            | Q(category__category_name__icontains=search)
            | Q(seller__first_name__icontains=search)
            | Q(seller__last_name__icontains=search)
            | Q(seller__username__icontains=search)
        )

    filtered_qs = queryset.filter(base_q & filters_q).distinct()
    page_obj, _ = _paginate_queryset(request, filtered_qs, page_size=10)

    results = []
    for product in page_obj.object_list:
        seller_name = f"{product.seller.first_name or ''} {product.seller.last_name or ''}".strip() or product.seller.username
        results.append({
            'id': product.id,
            'title': product.title,
            'amount': str(product.amount),
            'is_active': product.is_active,
            'deal_status': product.deal_status,
            'status': product.status,
            'created_at': product.created_at.isoformat(),
            'category': {
                'id': product.category_id,
                'name': product.category.category_name if product.category else None,
            },
            'seller': {
                'id': product.seller_id,
                'name': seller_name,
                'mobile': product.seller.mobile,
                'email': product.seller.email,
            },
            'interested_buyers_count': sum(
                1 for i in product.interests.all()
                if i.is_active and i.status in PENDING_INTEREST_STATUSES
            ),
            'approved_buyer_id': None,
        })

    return Response({
        'results': results,
        'pagination': {
            'count': page_obj.paginator.count,
            'num_pages': page_obj.paginator.num_pages,
            'page': page_obj.number,
            'page_size': 10,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
            'previous_page': page_obj.previous_page_number() if page_obj.has_previous() else None,
        },
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def universal_filter_api(request):
    entity = (request.GET.get('entity') or 'product').strip().lower()
    user = request.user
    params = {k: (v or '').strip() for k, v in request.GET.items() if k != 'entity'}

    admin_only_entities = {'user', 'category', 'subcategory', 'branch'}
    if entity in admin_only_entities and not _is_admin_user(user):
        return Response({'detail': 'Only admin can access this entity filter.'}, status=status.HTTP_403_FORBIDDEN)

    def bool_param(name):
        value = params.get(name, '')
        if value == '':
            return None
        return _parse_bool(value)

    if entity == 'product':
        queryset = Product.objects.select_related('category', 'seller').prefetch_related('interests').order_by('-created_at')

        base_q = Q()
        if _is_admin_user(user):
            base_q &= Q()
        elif _is_seller_user(user):
            base_q &= Q(seller=user)
        elif _is_buyer_user(user):
            base_q &= Q(is_active=True)
        else:
            return Response({'results': [], 'pagination': {'count': 0, 'num_pages': 0, 'page': 1}}, status=status.HTTP_200_OK)

        q = Q()
        search = params.get('search', '')
        if search:
            q &= (
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(category__category_name__icontains=search)
                | Q(seller__username__icontains=search)
                | Q(seller__first_name__icontains=search)
                | Q(seller__last_name__icontains=search)
            )

        for key, lookup in {
            'id': 'id',
            'title': 'title__icontains',
            'category_id': 'category_id',
            'subcategory_id': 'category__parent_id',
            'seller_id': 'seller_id',
            'seller_mobile': 'seller__mobile__icontains',
            'seller_email': 'seller__email__icontains',
            'status': 'status',
            'loading_location': 'loading_location__icontains',
        }.items():
            value = params.get(key, '')
            if value:
                q &= Q(**{lookup: value})

        if params.get('min_price'):
            q &= Q(amount__gte=params['min_price'])
        if params.get('max_price'):
            q &= Q(amount__lte=params['max_price'])

        is_active_value = bool_param('is_active')
        if is_active_value is not None:
            q &= Q(is_active=is_active_value)

        is_approved_value = bool_param('is_approved')
        if is_approved_value is not None:
            q &= Q(is_approved=is_approved_value)

        if params.get('from_date'):
            q &= Q(created_at__date__gte=params['from_date'])
        if params.get('to_date'):
            q &= Q(created_at__date__lte=params['to_date'])

        interested_value = bool_param('interested')
        if interested_value:
            q &= Q(interests__is_active=True, interests__status__in=PENDING_INTEREST_STATUSES)

        approved_value = bool_param('approved')
        if approved_value:
            q &= (
                Q(status=Product.STATUS_SOLD_PENDING_CONFIRMATION)
                | Q(status=Product.STATUS_SOLD)
                | Q(interests__status=ProductInterest.STATUS_SELLER_CONFIRMED)
                | Q(interests__status=ProductInterest.STATUS_DEAL_CONFIRMED)
            )

        filtered_qs = queryset.filter(base_q & q).distinct()
        page_obj, _ = _paginate_queryset(request, filtered_qs, page_size=10)
        results = [{
            'id': p.id,
            'title': p.title,
            'amount': str(p.amount),
            'is_active': p.is_active,
            'deal_status': p.deal_status,
            'status': p.status,
            'is_approved': p.is_approved,
            'created_at': p.created_at.isoformat(),
            'category': {'id': p.category_id, 'name': p.category.category_name if p.category else None},
            'seller': {
                'id': p.seller_id,
                'name': (f'{p.seller.first_name or ""} {p.seller.last_name or ""}'.strip() or p.seller.username),
                'mobile': p.seller.mobile,
                'email': p.seller.email,
            },
            'interested_buyers_count': sum(
                1 for i in p.interests.all()
                if i.is_active and i.status in PENDING_INTEREST_STATUSES
            ),
            'approved_buyer_id': None,
        } for p in page_obj.object_list]

    elif entity == 'user':
        queryset = DaalUser.objects.order_by('-date_joined')
        q = Q()
        search = params.get('search', '')
        if search:
            q &= (
                Q(username__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
                | Q(mobile__icontains=search)
            )
        for key, lookup in {
            'id': 'id',
            'username': 'username__icontains',
            'mobile': 'mobile__icontains',
            'email': 'email__icontains',
            'first_name': 'first_name__icontains',
            'last_name': 'last_name__icontains',
            'role': 'role',
            'kyc_status': 'kyc_status',
        }.items():
            value = params.get(key, '')
            if value:
                q &= Q(**{lookup: value})
        is_active_value = bool_param('is_active')
        if is_active_value is not None:
            q &= Q(is_active=is_active_value)
        if params.get('from_date'):
            q &= Q(date_joined__date__gte=params['from_date'])
        if params.get('to_date'):
            q &= Q(date_joined__date__lte=params['to_date'])
        page_obj, _ = _paginate_queryset(request, queryset.filter(q).distinct(), page_size=10)
        results = [{
            'id': u.id,
            'username': u.username,
            'mobile': u.mobile,
            'email': u.email,
            'first_name': u.first_name,
            'last_name': u.last_name,
            'role': u.role,
            'kyc_status': u.kyc_status,
            'is_active': u.is_active,
            'date_joined': u.date_joined.isoformat(),
        } for u in page_obj.object_list]

    elif entity == 'category':
        queryset = CategoryMaster.objects.order_by('-created_at')
        q = Q()
        if params.get('id'):
            q &= Q(id=params['id'])
        if params.get('category_name'):
            q &= Q(category_name__icontains=params['category_name'])
        if params.get('search'):
            q &= Q(category_name__icontains=params['search'])
        if params.get('from_date'):
            q &= Q(created_at__date__gte=params['from_date'])
        if params.get('to_date'):
            q &= Q(created_at__date__lte=params['to_date'])
        page_obj, _ = _paginate_queryset(request, queryset.filter(q).distinct(), page_size=10)
        results = [{
            'id': c.id,
            'category_name': c.category_name,
            'created_at': c.created_at.isoformat(),
            'updated_at': c.updated_at.isoformat(),
        } for c in page_obj.object_list]

    elif entity == 'subcategory':
        queryset = subCategoryMaster.objects.select_related('parent').filter(parent__isnull=False).order_by('-created_at')
        q = Q()
        if params.get('id'):
            q &= Q(id=params['id'])
        if params.get('subcategory_name'):
            q &= Q(category_name__icontains=params['subcategory_name'])
        if params.get('category_id'):
            q &= Q(parent_id=params['category_id'])
        if params.get('search'):
            q &= (
                Q(category_name__icontains=params['search'])
                | Q(parent__category_name__icontains=params['search'])
            )
        if params.get('from_date'):
            q &= Q(created_at__date__gte=params['from_date'])
        if params.get('to_date'):
            q &= Q(created_at__date__lte=params['to_date'])
        page_obj, _ = _paginate_queryset(request, queryset.filter(q).distinct(), page_size=10)
        results = [{
            'id': s.id,
            'subcategory_name': s.category_name,
            'category': {'id': s.parent_id, 'name': s.parent.category_name if s.parent else None},
            'created_at': s.created_at.isoformat(),
            'updated_at': s.updated_at.isoformat(),
        } for s in page_obj.object_list]

    else:
        return Response({'detail': 'Invalid entity. Use: product, user, category, subcategory.'}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        'entity': entity,
        'results': results,
        'pagination': {
            'count': page_obj.paginator.count,
            'num_pages': page_obj.paginator.num_pages,
            'page': page_obj.number,
            'page_size': 10,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
            'previous_page': page_obj.previous_page_number() if page_obj.has_previous() else None,
        },
    }, status=status.HTTP_200_OK)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = CategoryMaster.objects.all().order_by('-created_at')
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsSellerOrAdminRole]  # ✅ Admin + Seller
    module_name = 'category_management'

    def get_queryset(self):
        queryset = CategoryMaster.objects.all()
        
        # Filter by level
        level = self.request.query_params.get('level')
        if level:
            queryset = queryset.filter(level=level)
        
        # Filter by parent
        parent = self.request.query_params.get('parent')
        if parent:
            if parent == 'null' or parent == '0':
                queryset = queryset.filter(parent__isnull=True)
            else:
                queryset = queryset.filter(parent_id=parent)
        
        # Filter for subcategories (children of a parent)
        parent_id = self.request.query_params.get('parent_id')
        if parent_id:
            if parent_id == 'null' or parent_id == '0':
                queryset = queryset.filter(parent__isnull=True)
            else:
                queryset = queryset.filter(parent_id=parent_id)
        
        # Only active
        active_only = self.request.query_params.get('active_only')
        if active_only and active_only.lower() == 'true':
            queryset = queryset.filter(is_active=True)
        
        return queryset

    @staticmethod
    def _normalize_parent_payload(data):
        """
        Accept both `parent` and legacy `parent_id` keys from frontend.
        """
        mutable = data.copy()

        parent_val = mutable.get('parent')
        parent_id_val = mutable.get('parent_id')
        resolved_parent = parent_val if parent_val not in (None, '') else parent_id_val

        if resolved_parent in (None, '', 'null', 'None'):
            mutable['parent'] = None
        else:
            mutable['parent'] = resolved_parent

        # Avoid serializer "unexpected field" errors for legacy key.
        if 'parent_id' in mutable:
            try:
                mutable.pop('parent_id')
            except Exception:
                pass

        return mutable

    def create(self, request, *args, **kwargs):
        data = self._normalize_parent_payload(request.data)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = self._normalize_parent_payload(request.data)
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='hierarchy')
    def category_hierarchy(self, request):
        """Get full category hierarchy as nested structure"""
        root_categories = CategoryMaster.objects.filter(
            parent__isnull=True, 
            is_active=True
        ).order_by('category_name')
        
        def build_tree(categories):
            tree = []
            for cat in categories:
                children = cat.children.filter(is_active=True).order_by('category_name')
                tree.append({
                    'id': cat.id,
                    'name': cat.category_name,
                    'level': cat.level,
                    'path': cat.path,
                    'full_path': cat.get_full_path(),
                    'children': build_tree(children) if children.exists() else []
                })
            return tree
        
        return Response(build_tree(root_categories))

    @action(detail=False, methods=['get'], url_path='levels')
    def categories_by_level(self, request):
        """Get categories grouped by level"""
        max_level = request.query_params.get('max_level')
        categories = CategoryMaster.objects.filter(is_active=True).order_by('level', 'category_name')
        
        if max_level:
            categories = categories.filter(level__lte=max_level)
        
        result = {}
        for cat in categories:
            level = cat.level
            if level not in result:
                result[level] = []
            result[level].append({
                'id': cat.id,
                'name': cat.category_name,
                'parent_id': cat.parent_id if cat.parent else None,
                'full_path': cat.get_full_path()
            })
        
        return Response(result)

    def perform_create(self, serializer):
        blocked = _action_guard_response(self.request.user)
        if blocked:
            raise serializers.ValidationError({'detail': blocked.data['message']})
        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        blocked = _action_guard_response(user)
        if blocked:
            raise PermissionDenied(blocked.data['message'])
        if _is_admin_user(user) or _is_seller_user(user):
            serializer.save()
        else:
            raise PermissionDenied('You do not have permission to update categories.')

    def perform_destroy(self, instance):
        user = self.request.user
        blocked = _action_guard_response(user)
        if blocked:
            raise PermissionDenied(blocked.data['message'])
        if _is_admin_user(user) or _is_seller_user(user):
            instance.delete()
        else:
            raise PermissionDenied('You do not have permission to delete categories.')


class ProductViewSetLegacy(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        try:
            queryset = Product.objects.select_related(
                'category', 'root_category', 'brand', 'seller'
            ).prefetch_related(
                'images', 'videos', 'interests'
            ).order_by('-created_at')
            
            # Filter based on user role
            if self._is_admin(user):
                return queryset
            elif self._is_seller(user):
                return queryset.filter(seller=user)
            elif self._is_buyer(user):
                return queryset.filter(is_active=True)
            else:
                return queryset.none()
        except Exception as e:
            print(f"Error in get_queryset: {e}")
            return Product.objects.none()
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def create(self, request, *args, **kwargs):
        """Override create to handle multipart form data and seller assignment properly"""
        user = request.user
        
        # ✅ Check if user has permission to create products (Admin or Seller)
        if not (self._is_admin(user) or self._is_seller(user)):
            return Response(
                {'detail': 'You do not have permission to create products.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Debug: Print all received data
        print("="*50)
        print("CREATE PRODUCT - Received data:")
        print("POST data:", request.POST.dict())
        print("FILES data:", request.FILES.keys())
        print("="*50)
        
        # Create a mutable copy of the data
        data = request.POST.copy()
        
        # Handle seller for admin users
        if self._is_admin(user):
            # Check for seller_id in various possible field names
            seller_id = (
                data.get('seller_id') or 
                data.get('seller') or 
                request.data.get('seller_id') or 
                request.data.get('seller')
            )
            
            if not seller_id:
                return Response(
                    {'seller': ['Seller is required for admin users.']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Clean the seller_id (remove any whitespace)
            if isinstance(seller_id, str):
                seller_id = seller_id.strip()
            
            # Verify seller exists and has seller role
            try:
                seller_text = str(seller_id).strip()
                if seller_text.isdigit():
                    seller_user = DaalUser.objects.get(id=int(seller_text))
                else:
                    seller_user = DaalUser.objects.get(username=seller_text)
                
                if not (seller_user.is_seller or seller_user.role in ('seller', 'both_sellerandbuyer')):
                    return Response(
                        {'seller': ['Selected user does not have seller permissions.']},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Add seller to data
                data['seller'] = seller_user.id
                
            except DaalUser.DoesNotExist:
                return Response(
                    {'seller': ['Selected seller does not exist.']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except ValueError:
                return Response(
                    {'seller': ['Invalid seller ID format.']},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            # For sellers, set seller to current user
            data['seller'] = user.id
        
        # Handle category_id
        category_id = data.get('category_id') or data.get('category')
        
        if not category_id or category_id in ('', 'null'):
            return Response(
                {'category_id': ['Please select a category.']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            category_text = str(category_id).strip()
            if category_text.isdigit():
                # Verify category exists
                category = CategoryMaster.objects.get(id=int(category_text))
                data['category_id'] = category.id
            else:
                return Response(
                    {'category_id': ['Invalid category ID format.']},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except CategoryMaster.DoesNotExist:
            return Response(
                {'category_id': ['Selected category does not exist.']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Handle brand_id (optional)
        brand_id = data.get('brand_id') or data.get('brand')
        if brand_id and brand_id not in ('', 'null'):
            try:
                brand_text = str(brand_id).strip()
                if brand_text.isdigit():
                    brand = BrandMaster.objects.get(id=int(brand_text))
                    data['brand_id'] = brand.id
            except (BrandMaster.DoesNotExist, ValueError):
                # Don't error for brand as it's optional
                pass
        
        # Handle quantity fields
        quantity = data.get('quantity')
        if quantity and quantity.strip():
            try:
                qty_value = float(quantity)
                if qty_value <= 0:
                    return Response(
                        {'quantity': ['Quantity must be greater than 0.']},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                data['original_quantity'] = qty_value
                data['remaining_quantity'] = qty_value
            except ValueError:
                return Response(
                    {'quantity': ['Invalid quantity value.']},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            if 'quantity' in data:
                data.pop('quantity')
        
        # Handle amount_unit
        if 'amount_unit' not in data or not data.get('amount_unit'):
            data['amount_unit'] = 'kg'
        
        # Handle quantity_unit
        if 'quantity_unit' not in data or not data.get('quantity_unit'):
            data['quantity_unit'] = 'kg'
        
        # Handle amount
        amount = data.get('amount')
        if not amount:
            return Response(
                {'amount': ['Amount is required.']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            float(amount)
        except ValueError:
            return Response(
                {'amount': ['Invalid amount value.']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Handle loading_location
        if 'loading_location' not in data or not data.get('loading_location'):
            return Response(
                {'loading_location': ['Loading location is required.']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Handle title
        if 'title' not in data or not data.get('title'):
            return Response(
                {'title': ['Product title is required.']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Handle is_active checkbox
        if 'is_active' in data:
            data['is_active'] = data.get('is_active') == 'on'
        
        # Create serializer with the processed data
        serializer = self.get_serializer(data=data)
        
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            
            # Handle image upload if present
            if 'image' in request.FILES and request.FILES['image']:
                image_file = request.FILES['image']
                ProductImage.objects.create(
                    product=serializer.instance,
                    image=image_file,
                    is_primary=True
                )
            
            # Handle video upload if present
            if 'video' in request.FILES and request.FILES['video']:
                video_file = request.FILES['video']
                ProductVideo.objects.create(
                    product=serializer.instance,
                    video=video_file,
                    is_primary=True
                )
            
            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data, 
                status=status.HTTP_201_CREATED, 
                headers=headers
            )
            
        except serializers.ValidationError as e:
            print("Validation error:", e.detail)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
    
    def perform_create(self, serializer):
        # This is called after validation in create method
        serializer.save()
    
    def update(self, request, *args, **kwargs):
        """Override update to check permissions"""
        product = self.get_object()
        user = request.user
        
        # ✅ Check if user can update this product
        if not (self._is_admin(user) or (self._is_seller(user) and product.seller == user)):
            return Response(
                {'detail': 'You do not have permission to update this product.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Override delete to check permissions"""
        product = self.get_object()
        user = request.user
        
        # ✅ Check if user can delete this product
        if not (self._is_admin(user) or (self._is_seller(user) and product.seller == user)):
            return Response(
                {'detail': 'You do not have permission to delete this product.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'], url_path='toggle')
    def toggle_visibility(self, request, pk=None):
        """Toggle product active status"""
        product = self.get_object()
        user = request.user
        is_active = request.data.get('is_active', not product.is_active)
        
        # ✅ Check permissions
        if not (self._is_admin(user) or (self._is_seller(user) and product.seller == user)):
            return Response(
                {'success': False, 'message': 'Permission denied.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        product.is_active = is_active
        product.save()
        
        serializer = self.get_serializer(product)
        return Response({
            'success': True,
            'message': f'Product {"activated" if is_active else "deactivated"} successfully.',
            'product': serializer.data
        })
    
    @action(detail=True, methods=['get'], url_path='interests')
    def get_interests(self, request, pk=None):
        """Get all interests for a product"""
        product = self.get_object()
        user = request.user
        
        # ✅ Check permissions - Admin ya seller of this product
        if not (self._is_admin(user) or user == product.seller):
            return Response(
                {'success': False, 'message': 'Permission denied. You are not the seller of this product.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get interests - for seller, show only interested and seller_confirmed status
        interests = product.interests.filter(
            status__in=['interested', 'seller_confirmed']
        ).order_by('-created_at')
        
        # Custom data for seller - hide buyer personal info
        data = []
        for interest in interests:
            data.append({
                'id': interest.id,
                'transaction_id': interest.transaction_id,
                'buyer_id': interest.buyer.buyer_unique_id or f"BUYER-{interest.buyer.id:04d}",
                'buyer_name': f"Buyer {interest.buyer.id}",  # Hide real name
                'buyer_offered_amount': str(interest.buyer_offered_amount or ''),
                'required_quantity': str(interest.buyer_required_quantity),
                'delivery_date': interest.delivery_date.strftime('%Y-%m-%d') if interest.delivery_date else None,
                'message': interest.buyer_remark or '',
                'status': interest.status,
                'created_at': interest.created_at.isoformat(),
            })
        
        return Response({
            'success': True,
            'interests': data,
            'product_status': product.status,
            'deal_status': product.deal_status
        })
    
    @action(detail=True, methods=['post'], url_path='approve')
    def approve_interest(self, request, pk=None):
        """Seller approves a buyer's interest"""
        product = self.get_object()
        user = request.user
        interest_id = request.data.get('interest_id')
        seller_remark = request.data.get('seller_remark', '')
        
        # ✅ Check permissions
        if not (self._is_admin(user) or user == product.seller):
            return Response(
                {'success': False, 'message': 'Permission denied.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            interest = ProductInterest.objects.get(id=interest_id, product=product)
            
            # Check if interest is in correct state
            if interest.status != ProductInterest.STATUS_INTERESTED:
                return Response(
                    {'success': False, 'message': f'Cannot approve interest with status {interest.status}.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic():
                interest.status = ProductInterest.STATUS_SELLER_CONFIRMED
                interest.seller_remark = seller_remark
                interest.save()
                
                product.deal_status = Product.DEAL_STATUS_SELLER_CONFIRMED
                product.save()
            
            serializer = self.get_serializer(product)
            return Response({
                'success': True,
                'message': 'Interest approved successfully. Waiting for admin confirmation.',
                'product': serializer.data
            })
            
        except ProductInterest.DoesNotExist:
            return Response(
                {'success': False, 'message': 'Interest not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'], url_path='reject')
    def reject_interest(self, request, pk=None):
        """Seller rejects a buyer's interest"""
        product = self.get_object()
        user = request.user
        interest_id = request.data.get('interest_id')
        seller_remark = request.data.get('seller_remark', '')
        
        # ✅ Check permissions
        if not (self._is_admin(user) or user == product.seller):
            return Response(
                {'success': False, 'message': 'Permission denied.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            interest = ProductInterest.objects.get(id=interest_id, product=product)
            
            # Check if interest is in correct state
            if interest.status != ProductInterest.STATUS_INTERESTED:
                return Response(
                    {'success': False, 'message': f'Cannot reject interest with status {interest.status}.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic():
                interest.status = ProductInterest.STATUS_REJECTED
                interest.seller_remark = seller_remark
                interest.is_active = False
                interest.save()
            
            serializer = self.get_serializer(product)
            return Response({
                'success': True,
                'message': 'Interest rejected successfully.',
                'product': serializer.data
            })
            
        except ProductInterest.DoesNotExist:
            return Response(
                {'success': False, 'message': 'Interest not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'], url_path='confirm-deal')
    def confirm_deal(self, request, pk=None):
        """Super admin confirms the deal"""
        product = self.get_object()
        user = request.user
        
        # ✅ Check permissions - only admin/superuser
        if not self._is_admin(user):
            return Response(
                {'success': False, 'message': 'Permission denied. Only admin can confirm deals.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        with transaction.atomic():
            # Update product
            product.deal_status = Product.DEAL_STATUS_DEAL_CONFIRMED
            product.status = Product.STATUS_SOLD_PENDING_CONFIRMATION
            product.save(update_fields=['deal_status', 'status', 'updated_at'])
            
            # Update the confirmed interest
            confirmed_interest = product.interests.filter(
                status=ProductInterest.STATUS_SELLER_CONFIRMED
            ).first()
            
            if confirmed_interest:
                confirmed_interest.status = ProductInterest.STATUS_DEAL_CONFIRMED
                confirmed_interest.deal_confirmed_at = timezone.now()
                confirmed_interest.save()
                
                # Update product stock
                product.update_stock_after_deal(confirmed_interest.buyer_required_quantity)
                
                # Reject all other interests
                product.interests.exclude(id=confirmed_interest.id).update(
                    status=ProductInterest.STATUS_REJECTED,
                    is_active=False
                )
        
        serializer = self.get_serializer(product)
        return Response({
            'success': True,
            'message': 'Deal confirmed successfully.',
            'product': serializer.data
        })
    
    @action(detail=True, methods=['post'], url_path='toggle-interest')
    def toggle_interest(self, request, pk=None):
        """Buyer shows or updates interest in a product"""
        product = self.get_object()
        user = request.user
        
        # ✅ Check if user is a buyer
        if not self._is_buyer(user):
            return Response(
                {'success': False, 'message': 'Only buyers can show interest.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if product is available
        if product.status != Product.STATUS_AVAILABLE or product.deal_status != Product.DEAL_STATUS_AVAILABLE:
            return Response(
                {'success': False, 'message': 'This product is no longer available.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate required fields
        offered_amount = request.data.get('buyer_offered_amount')
        required_quantity = request.data.get('buyer_required_quantity', 1)
        delivery_date = request.data.get('delivery_date')
        
        if not offered_amount:
            return Response(
                {'success': False, 'message': 'Offered amount is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not delivery_date:
            return Response(
                {'success': False, 'message': 'Delivery date is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            offered_amount = Decimal(str(offered_amount))
            required_quantity = Decimal(str(required_quantity))
        except Exception:
            return Response(
                {'success': False, 'message': 'Invalid amount or quantity.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if offered_amount <= 0 or required_quantity <= 0:
            return Response(
                {'success': False, 'message': 'Amount and quantity must be greater than 0.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        available_qty = product.remaining_quantity if product.remaining_quantity is not None else product.original_quantity
        if available_qty is None or available_qty <= 0:
            return Response(
                {'success': False, 'message': 'This product is out of stock.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if required_quantity > available_qty:
            return Response(
                {'success': False, 'message': f'Only {available_qty} {product.quantity_unit} available.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Always create a fresh interest so buyer can place multiple offers on same product.
        interest = ProductInterest.objects.create(
            product=product,
            buyer=user,
            seller=product.seller,
            status=ProductInterest.STATUS_INTERESTED,
            buyer_offered_amount=offered_amount,
            buyer_required_quantity=required_quantity,
            buyer_remark=request.data.get('buyer_remark', ''),
            delivery_date=delivery_date,
            is_active=True
        )
        
        serializer = self.get_serializer(product)
        return Response({
            'success': True,
            'message': 'Interest submitted successfully.',
            'product': serializer.data
        })
    
    # ===================== HELPER METHODS =====================
    
    @staticmethod
    def _is_admin(user):
        """Check if user is admin"""
        return bool(
            user.is_authenticated and (
                user.is_superuser or
                user.is_staff or
                user.is_admin or
                user.role in ('super_admin', 'admin')
            )
        )
    
    @staticmethod
    def _is_seller(user):
        """Check if user is seller"""
        return bool(
            user.is_authenticated and (
                user.is_seller or
                user.role in ('seller', 'both_sellerandbuyer')
            )
        )
    
    @staticmethod
    def _is_buyer(user):
        """Check if user is buyer"""
        return bool(
            user.is_authenticated and (
                user.is_buyer or
                user.role in ('buyer', 'both_sellerandbuyer')
            )
        )

# class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    
    def retrieve(self, request, *args, **kwargs):
        try:
            print(f"=== Retrieve Product ===")
            print(f"User: {request.user.id}, Role: {request.user.role}")
            print(f"Product ID: {kwargs.get('pk')}")
            
            instance = self.get_object()
            print(f"Product found: {instance.id} - {instance.title}")
            
            serializer = self.get_serializer(instance)
            print(f"Serialization successful")
            
            return Response(serializer.data)
        except Exception as e:
            print(f"ERROR in retrieve: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e), 'detail': 'Internal server error'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get_queryset(self):
        try:
            user = self.request.user
            print(f"get_queryset for user: {user.id}")
            
            queryset = Product.objects.select_related(
                'category', 'root_category', 'brand', 'seller'
            ).prefetch_related(
                'images', 'videos', 'interests'
            ).order_by('-created_at')
            
            if self._is_admin(user):
                print("Admin: returning all products")
                return queryset
            elif self._is_seller(user):
                print(f"Seller: returning products for seller {user.id}")
                return queryset.filter(seller=user)
            elif self._is_buyer(user):
                print("Buyer: returning active products")
                return queryset.filter(is_active=True)
            else:
                print("Other: returning none")
                return queryset.none()
        except Exception as e:
            print(f"ERROR in get_queryset: {str(e)}")
            import traceback
            traceback.print_exc()
            return Product.objects.none()

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer  # Ye wala problematic hai
    permission_classes = [IsAuthenticated]
    
    def retrieve(self, request, *args, **kwargs):
        try:
            print("="*50)
            print("PRODUCT RETRIEVE CALLED")
            print(f"Product ID: {kwargs.get('pk')}")
            
            # Pehle product fetch karo
            product = self.get_object()
            print(f"Product found: {product.id} - {product.title}")
            
            # Ab serializer lagao
            serializer = self.get_serializer(product)
            print("Serializer successful")
            
            return Response(serializer.data)
            
        except Exception as e:
            print(f"ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e), 'detail': 'Internal server error'}, 
                status=500
            )

@login_required
def intrast_page(request):
    """Render contracts/deals page."""
    user = request.user

    contracts_qs = Contract.objects.select_related('product', 'buyer', 'seller').order_by('-confirmed_at', '-id')

    if _is_admin_user(user):
        pass
    elif _is_seller_user(user):
        contracts_qs = contracts_qs.filter(seller=user)
    elif _is_buyer_user(user):
        contracts_qs = contracts_qs.filter(buyer=user)
    else:
        contracts_qs = contracts_qs.none()

    search = (request.GET.get('search') or '').strip()
    if search:
        contracts_qs = contracts_qs.filter(
            Q(contract_id__icontains=search) |
            Q(product__title__icontains=search)
        )

    status_filter = (request.GET.get('status') or '').strip()
    if status_filter:
        contracts_qs = contracts_qs.filter(status=status_filter)

    if _is_admin_user(user):
        seller = (request.GET.get('seller') or '').strip()
        if seller.isdigit():
            contracts_qs = contracts_qs.filter(seller_id=int(seller))

        buyer = (request.GET.get('buyer') or '').strip()
        if buyer.isdigit():
            contracts_qs = contracts_qs.filter(buyer_id=int(buyer))

    page_obj, pagination = _paginate_queryset(request, contracts_qs, page_size=15)
    is_admin_viewer = _is_admin_user(user)

    for contract in page_obj.object_list:
        party_ids = get_contract_display_ids(contract, user, is_admin=is_admin_viewer)
        contract.display_seller_id = party_ids['display_seller_id']
        contract.display_buyer_id = party_ids['display_buyer_id']

    total_contracts = contracts_qs.count()
    active_contracts = contracts_qs.filter(status=Contract.STATUS_ACTIVE).count()
    completed_contracts = contracts_qs.filter(status=Contract.STATUS_COMPLETED).count()
    total_value = contracts_qs.aggregate(total=Coalesce(Sum('deal_amount'), Decimal('0.00')))['total']

    sellers = []
    buyers = []
    if _is_admin_user(user):
        sellers = DaalUser.objects.filter(
            Q(is_seller=True) | Q(role__in=['seller', 'both_sellerandbuyer'])
        ).order_by('username')
        buyers = DaalUser.objects.filter(
            Q(is_buyer=True) | Q(role__in=['buyer', 'both_sellerandbuyer'])
        ).order_by('username')

    highlighted_contract = None
    highlighted_contract_id = (request.GET.get('contract_id') or '').strip()
    if highlighted_contract_id.isdigit():
        highlighted_contract = contracts_qs.filter(id=int(highlighted_contract_id)).first()
        if highlighted_contract:
            party_ids = get_contract_display_ids(highlighted_contract, user, is_admin=is_admin_viewer)
            highlighted_contract.display_seller_id = party_ids['display_seller_id']
            highlighted_contract.display_buyer_id = party_ids['display_buyer_id']

    context = {
        'contracts': page_obj.object_list,
        'page_obj': page_obj,
        'pagination': pagination,
        'total_contracts': total_contracts,
        'active_contracts': active_contracts,
        'completed_contracts': completed_contracts,
        'total_value': total_value,
        'sellers': sellers,
        'buyers': buyers,
        'highlighted_contract': highlighted_contract,
        'is_admin_user': _is_admin_user(user),
        'is_admin_or_super_admin': bool(
            user.is_superuser or getattr(user, 'is_admin', False) or getattr(user, 'role', '') in ('super_admin', 'admin')
        ),
        'is_seller_user': _is_seller_user(user),
        'is_buyer_user': _is_buyer_user(user),
        'filters': {
            'search': search,
            'status': status_filter,
            'seller': request.GET.get('seller', ''),
            'buyer': request.GET.get('buyer', ''),
        }
    }

    return render(request, 'intrest.html', context)


class ProductImageViewSet(viewsets.ModelViewSet):
    serializer_class = ProductImageSerializer
    permission_classes = [IsAuthenticated, IsSellerOrAdminRole]  # ✅ Admin + Seller
    module_name = 'product_image_management'

    def get_queryset(self):
        queryset = ProductImage.objects.select_related('product', 'product__seller').order_by('-created_at')
        user = self.request.user
        if _is_admin_user(user):
            return queryset
        if _is_seller_user(user):
            return queryset.filter(product__seller=user)
        return ProductImage.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        blocked = _action_guard_response(user)
        if blocked:
            raise serializers.ValidationError({'detail': blocked.data['message']})
        product = serializer.validated_data['product']
        
        # ✅ Check permissions
        if _is_admin_user(user):
            pass  # Admin can upload to any product
        elif _is_seller_user(user) and product.seller_id == user.id:
            pass  # Seller can upload to own products
        else:
            raise serializers.ValidationError({'product': 'You can upload images only for your own products.'})

        is_primary = serializer.validated_data.get('is_primary', False)
        if is_primary:
            ProductImage.objects.filter(product=product).update(is_primary=False)
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        blocked = _action_guard_response(user)
        if blocked:
            raise serializers.ValidationError({'detail': blocked.data['message']})
        
        # ✅ Check permissions
        if _is_admin_user(user):
            instance.delete()
        elif _is_seller_user(user) and instance.product.seller_id == user.id:
            instance.delete()
        else:
            raise serializers.ValidationError({'detail': 'You can only delete images from your own products.'})


class UserViewSet(viewsets.ModelViewSet):
    queryset = DaalUser.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]  # ✅ Sirf admin
    module_name = 'user_management'

    def get_queryset(self):
        return DaalUser.objects.all().order_by('-date_joined')

    def perform_update(self, serializer):
        user = self.request.user
        sensitive_fields = {
            'kyc_status', 'kyc_submitted_at', 'kyc_approved_at', 'kyc_rejected_at',
            'kyc_rejection_reason', 'account_status', 'deactivated_at',
            'suspended_at', 'suspension_reason',
        }
        if not _is_admin_user(user):
            if any(field in serializer.validated_data for field in sensitive_fields):
                raise serializers.ValidationError({'detail': 'Only admin can modify KYC/account status fields.'})
        serializer.save()


def registration_page(request):
    return render(request, 'registration.html')


def forgotpassword_page(request):
    return render(request, 'forgotpassword.html')


@login_required
def kyc_dashboard_page(request):
    if not _is_admin_user(request.user):
        messages.error(request, 'Only admin can access User KYC dashboard.')
        return redirect('dashboard')

    search = (request.GET.get('search') or '').strip()
    role = (request.GET.get('role') or 'all').strip()
    kyc_status = (request.GET.get('kyc_status') or 'all').strip()

    queryset = DaalUser.objects.exclude(role='admin').order_by('-date_joined')

    if search:
        queryset = queryset.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(username__icontains=search)
            | Q(mobile__icontains=search)
        )

    valid_roles = {choice[0] for choice in DaalUser.ROLE_CHOICES if choice[0] != 'admin'}
    if role in valid_roles:
        queryset = queryset.filter(role=role)
    else:
        role = 'all'

    valid_kyc_statuses = {choice[0] for choice in DaalUser.KYC_STATUS_CHOICES}
    if kyc_status in valid_kyc_statuses:
        queryset = queryset.filter(kyc_status=kyc_status)
    else:
        kyc_status = 'all'

    page_obj, pagination = _paginate_queryset(request, queryset)
    return render(request, 'kyc.html', {
        'kyc_users': page_obj.object_list,
        'page_obj': page_obj,
        'pagination': pagination,
        'roles': [(k, v) for (k, v) in DaalUser.ROLE_CHOICES if k != 'admin'],
        'kyc_status_choices': DaalUser.KYC_STATUS_CHOICES,
        'filters': {
            'search': search,
            'role': role,
            'kyc_status': kyc_status,
        },
    })


class ProductVideoViewSet(viewsets.ModelViewSet):
    serializer_class = ProductVideoSerializer
    permission_classes = [IsAuthenticated, IsSellerOrAdminRole]  # ✅ Admin + Seller
    module_name = 'product_image_management'

    def get_queryset(self):
        queryset = ProductVideo.objects.select_related('product', 'product__seller').order_by('-created_at')
        user = self.request.user
        if _is_admin_user(user):
            return queryset
        if _is_seller_user(user):
            return queryset.filter(product__seller=user)
        return ProductVideo.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        blocked = _action_guard_response(user)
        if blocked:
            raise serializers.ValidationError({'detail': blocked.data['message']})
        product = serializer.validated_data['product']
        if not product.is_active:
            raise serializers.ValidationError({'product': 'Cannot upload video to inactive product.'})
        
        # ✅ Check permissions
        if _is_admin_user(user):
            pass  # Admin can upload to any product
        elif _is_seller_user(user) and product.seller_id == user.id:
            pass  # Seller can upload to own products
        else:
            raise serializers.ValidationError({'product': 'You can upload videos only for your own products.'})

        is_primary = serializer.validated_data.get('is_primary', False)
        if is_primary:
            ProductVideo.objects.filter(product=product).update(is_primary=False)
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        blocked = _action_guard_response(user)
        if blocked:
            raise serializers.ValidationError({'detail': blocked.data['message']})
        
        # ✅ Check permissions
        if _is_admin_user(user):
            instance.delete()
        elif _is_seller_user(user) and instance.product.seller_id == user.id:
            instance.delete()
        else:
            raise serializers.ValidationError({'detail': 'You can only delete videos from your own products.'})


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def profile_update_api(request):
    user = request.user
    if request.method == 'GET':
        serializer = ProfileUpdateSerializer(user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    elif request.method == 'PATCH':
        serializer = ProfileUpdateSerializer(user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            try:
                serializer.save()
                return Response({'message': 'Profile updated successfully.', 'data': serializer.data}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'message': f'Failed to update profile: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_api(request):
    serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = request.user
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']

        if not user.check_password(old_password):
            return Response({'old_password': ['Old password is incorrect.']}, status=status.HTTP_400_BAD_REQUEST)

        # Validate new password strength
        if len(new_password) < 8:
            return Response({'new_password': ['Password must be at least 8 characters long.']}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.char_password = new_password
        user.save(update_fields=['password', 'char_password'])
        send_password_changed_email(user.email)
        return Response({'message': 'Password changed successfully.'}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@login_required
def product_video_list_page(request):
    user = request.user
    if not (_is_admin_user(user) or _is_seller_user(user)):
        messages.error(request, 'Only admin or seller can access Product Video management.')
        return redirect('dashboard')

    products = Product.objects.filter(is_active=True).order_by('-created_at')
    videos = ProductVideo.objects.select_related('product').order_by('-created_at')
    
    if _is_seller_user(user) and not _is_admin_user(user):
        products = products.filter(seller=user)
        videos = videos.filter(product__seller=user)

    return render(request, 'product_video_list.html', {
        'products': products,
        'videos': videos,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_dashboard_api(request):
    """
    API endpoint for admin dashboard data
    Returns KPIs, charts data, branch performance, recent activities, and contracts
    """
    user = request.user
    if not _is_admin_user(user):
        return Response({'message': 'Access denied. Admin privileges required.'}, status=status.HTTP_403_FORBIDDEN)

    # Dynamic data computation
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    # User counts
    active_sellers = DaalUser.objects.filter(
        is_active=True,
        role__in=['seller', 'both_sellerandbuyer']
    ).count()

    active_buyers = DaalUser.objects.filter(
        is_active=True,
        role__in=['buyer', 'both_sellerandbuyer']
    ).count()

    active_transporters = DaalUser.objects.filter(
        is_active=True,
        role='transporter'
    ).count()

    active_admins = DaalUser.objects.filter(
        is_active=True
    ).filter(
        Q(is_admin=True) | Q(is_staff=True) | Q(is_superuser=True) | Q(role='admin')
    ).distinct().count()

    branches_count = BranchMaster.objects.filter(is_active=True).count()
    listed_skus = Product.objects.filter(is_active=True).values('category_id').distinct().count()

    # Contract and deal counts
    active_contracts = ProductInterest.objects.filter(
        status=ProductInterest.STATUS_SELLER_CONFIRMED,
        is_active=True,
    ).count()

    finalized_deals_mtd = ProductInterest.objects.filter(
        status=ProductInterest.STATUS_DEAL_CONFIRMED,
        updated_at__gte=month_start,
    ).count()

    deals_in_negotiation = ProductInterest.objects.filter(
        status=ProductInterest.STATUS_INTERESTED,
        is_active=True,
    ).count()

    pending_dispatches = Product.objects.filter(
        status=Product.STATUS_SOLD_PENDING_CONFIRMATION
    ).count()

    # Financial calculations
    sold_mtd_total = ProductInterest.objects.filter(
        status=ProductInterest.STATUS_DEAL_CONFIRMED,
        updated_at__gte=month_start,
    ).aggregate(total=Sum('buyer_offered_amount')).get('total') or Decimal('0')

    brokerage_rate = 4.0
    brokerage_earned_mtd = sold_mtd_total * Decimal(brokerage_rate / 100)

    # Dummy values for unimplemented features
    open_complaints = 12
    on_time_delivery_percent = 94
    avg_transit_days = 4.2
    payments_overdue = 8
    at_risk_amount = 1250000
    capacity_utilized = 78

    # Charts data
    gtv_deals_data = []
    for i in range(6, -1, -1):
        month_date = (now - timezone.timedelta(days=30*i)).replace(day=1)
        next_month = (month_date + timezone.timedelta(days=32)).replace(day=1)
        month_gtv = ProductInterest.objects.filter(
            status=ProductInterest.STATUS_DEAL_CONFIRMED,
            updated_at__gte=month_date,
            updated_at__lt=next_month
        ).aggregate(total=Sum('buyer_offered_amount')).get('total') or Decimal('0')
        month_deals = ProductInterest.objects.filter(
            status=ProductInterest.STATUS_DEAL_CONFIRMED,
            updated_at__gte=month_date,
            updated_at__lt=next_month
        ).count()
        month_name = month_date.strftime('%b')
        gtv_deals_data.append({
            'month': month_name,
            'gtv': float(month_gtv),
            'deals': month_deals
        })

    pipeline_data = ProductInterest.objects.values('status').annotate(count=Count('id')).order_by('status')
    pipeline_dict = {item['status']: item['count'] for item in pipeline_data}
    pipeline_stages = ['interested', 'seller_confirmed', 'buyer_confirmed', 'deal_confirmed']
    pipeline_values = [pipeline_dict.get(status, 0) for status in pipeline_stages]

    commodity_data = Product.objects.filter(is_active=True).values('category__category_name').annotate(
        volume=Count('id')
    ).order_by('-volume')[:5]
    commodity_labels = [item['category__category_name'] for item in commodity_data]
    commodity_volumes = [item['volume'] for item in commodity_data]

    top_buyers_data = ProductInterest.objects.filter(
        status=ProductInterest.STATUS_DEAL_CONFIRMED,
        updated_at__gte=year_start,
        buyer__is_active=True
    ).values('buyer__first_name', 'buyer__last_name').annotate(
        gtv=Coalesce(Sum('buyer_offered_amount'), Decimal(0), output_field=DecimalField())
    ).order_by('-gtv')[:5]
    top_buyers_labels = [f"{item['buyer__first_name']} {item['buyer__last_name']}" for item in top_buyers_data]
    top_buyers_gtv = [float(item['gtv']) for item in top_buyers_data]

    transporter_sla_labels = ['TransCo Logistics', 'FastMove Carriers', 'RoadRunner Transport', 'Speedy Deliveries']
    transporter_sla_otd = [96, 92, 88, 85]

    payments_labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4']
    payments_received = [4500000, 5200000, 4800000, 6100000]
    payments_outstanding = [2800000, 2100000, 3200000, 1800000]

    user_distribution_labels = ['Sellers', 'Buyers', 'Transporters', 'Admins']
    user_distribution_counts = [active_sellers, active_buyers, active_transporters, active_admins]

    # Branch performance (dummy)
    branch_performance = [
        {
            'name': 'Nagpur',
            'admin': 'R. Kulkarni',
            'sellers': 38,
            'buyers': 52,
            'contracts': 146,
            'gtv_mtd': 2240000,
            'otd_percent': 91,
            'open_issues': 9,
            'status': 'active'
        },
        {
            'name': 'Katni',
            'admin': 'P. Singh',
            'sellers': 31,
            'buyers': 41,
            'contracts': 103,
            'gtv_mtd': 1810000,
            'otd_percent': 87,
            'open_issues': 13,
            'status': 'active'
        },
        {
            'name': 'Indore',
            'admin': 'A. Jain',
            'sellers': 19,
            'buyers': 28,
            'contracts': 58,
            'gtv_mtd': 970000,
            'otd_percent': 93,
            'open_issues': 4,
            'status': 'active'
        },
        {
            'name': 'Raipur',
            'admin': 'S. Verma',
            'sellers': 22,
            'buyers': 33,
            'contracts': 44,
            'gtv_mtd': 720000,
            'otd_percent': 79,
            'open_issues': 11,
            'status': 'watchlist'
        }
    ]

    # Recent activities
    recent_interests = ProductInterest.objects.select_related(
        'product', 'buyer', 'seller'
    ).filter(
        buyer__is_active=True,
        seller__is_active=True
    ).order_by('-updated_at')[:6]
    recent_activities = []
    for interest in recent_interests:
        if interest.status == ProductInterest.STATUS_DEAL_CONFIRMED:
            activity_type = 'trade'
            icon = 'shopping-cart'
            title = 'Deal Finalized'
            desc = f"#{interest.id} • {interest.product.title[:20]}... • Buyer: {interest.buyer.first_name} {interest.buyer.last_name} • Seller: {interest.seller.first_name} {interest.seller.last_name}"
        elif interest.status == ProductInterest.STATUS_SELLER_CONFIRMED:
            activity_type = 'contract'
            icon = 'file-signature'
            title = 'Contract Signed'
            desc = f"#{interest.id} • {interest.product.title[:20]}... • Brokerage: ₹{(interest.buyer_offered_amount or 0) * Decimal(0.04):,.0f}"
        else:
            activity_type = 'trade'
            icon = 'balance-scale'
            title = 'Negotiation Updated'
            desc = f"#{interest.id} • {interest.product.title[:20]}... • Offer: ₹{(interest.buyer_offered_amount or 0):,.0f}/qtl"
        recent_activities.append({
            'type': activity_type,
            'icon': icon,
            'title': title,
            'description': desc,
            'time': interest.updated_at.strftime('%H:%M %d/%m')
        })

    # Recent contracts
    recent_contracts_qs = ProductInterest.objects.select_related(
        'product__category', 'buyer', 'seller'
    ).filter(
        status=ProductInterest.STATUS_DEAL_CONFIRMED,
        buyer__is_active=True,
        seller__is_active=True
    ).order_by('-updated_at')[:5]
    recent_contracts = []
    for interest in recent_contracts_qs:
        recent_contracts.append({
            'id': f'#CNT-{interest.id}',
            'seller': f"{interest.seller.first_name} {interest.seller.last_name}",
            'buyer': f"{interest.buyer.first_name} {interest.buyer.last_name}",
            'commodity': interest.product.category.category_name,
            'quantity': '80 Qtl',
            'rate': f"₹{(interest.buyer_offered_amount or 0):,.0f}/qtl",
            'value': f"₹{(interest.buyer_offered_amount or 0):,.0f}",
            'brokerage': f"₹{(interest.buyer_offered_amount or 0) * Decimal(0.04):,.0f}",
            'payment_status': 'Fully Paid',
            'delivery_status': 'Delivered',
            'transporter': 'TransCo Logistics',
            'branch': 'Nagpur'
        })

    data = {
        'kpis': {
            'active_contracts': active_contracts,
            'gtv_mtd': float(sold_mtd_total),
            'brokerage_earned_mtd': float(brokerage_earned_mtd),
            'brokerage_rate': brokerage_rate,
            'pending_dispatches': pending_dispatches,
            'active_sellers': active_sellers,
            'listed_skus': listed_skus,
            'active_buyers': active_buyers,
            'final_deals_mtd': finalized_deals_mtd,
            'open_complaints': open_complaints,
            'otd_percent': on_time_delivery_percent,
            'avg_transit_days': avg_transit_days,
            'payments_overdue': payments_overdue,
            'at_risk_amount': at_risk_amount,
            'active_transporters': active_transporters,
            'capacity_utilized': capacity_utilized,
            'branches': branches_count,
            'admins_active': active_admins,
            'deals_in_negotiation': deals_in_negotiation,
            'avg_ttc_days': 3.8
        },
        'charts': {
            'gtv_deals': {
                'labels': [item['month'] for item in gtv_deals_data],
                'gtv_values': [item['gtv'] for item in gtv_deals_data],
                'deals_values': [item['deals'] for item in gtv_deals_data]
            },
            'pipeline_by_stage': {
                'labels': ['Negotiation', 'Contract Signed', 'Buyer Confirmed', 'Deal Confirmed'],
                'values': pipeline_values
            },
            'commodity_mix': {
                'labels': commodity_labels,
                'volumes': commodity_volumes
            },
            'top_buyers': {
                'labels': top_buyers_labels,
                'gtv_values': top_buyers_gtv
            },
            'transporter_sla': {
                'labels': transporter_sla_labels,
                'otd_percentages': transporter_sla_otd
            },
            'payments_receivables': {
                'labels': payments_labels,
                'received': payments_received,
                'outstanding': payments_outstanding
            },
            'user_distribution': {
                'labels': user_distribution_labels,
                'counts': user_distribution_counts
            }
        },
        'branch_performance': branch_performance,
        'recent_activities': recent_activities,
        'recent_contracts': recent_contracts
    }

    return Response(data, status=status.HTTP_200_OK)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def buyer_dashboard_api(request):
    """Dynamic buyer dashboard data"""
    user = request.user
    
    if not _is_buyer_user(user):
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Get user's interests/contracts
    user_interests = ProductInterest.objects.filter(buyer=user)
    user_contracts = Contract.objects.filter(buyer=user)
    user_products = ProductInterest.objects.filter(buyer=user).select_related('product')
    
    # Calculate KPIs
    total_spent = user_contracts.filter(
        status='active'
    ).aggregate(total=Sum('deal_amount'))['total'] or 0
    
    spent_mtd = user_contracts.filter(
        status='active',
        confirmed_at__gte=month_start
    ).aggregate(total=Sum('deal_amount'))['total'] or 0
    
    # Get last month's spent for comparison
    last_month_start = (month_start - timezone.timedelta(days=1)).replace(day=1)
    spent_last_month = user_contracts.filter(
        status='active',
        confirmed_at__gte=last_month_start,
        confirmed_at__lt=month_start
    ).aggregate(total=Sum('deal_amount'))['total'] or 0
    
    if spent_last_month > 0:
        spent_delta = ((spent_mtd - spent_last_month) / spent_last_month) * 100
        spent_delta_str = f"{'+' if spent_delta >= 0 else ''}{spent_delta:.1f}% vs last month"
    else:
        spent_delta_str = "New this month"
    
    # Active orders (interests that are not rejected)
    active_orders = user_interests.filter(
        status__in=['interested', 'seller_confirmed']
    ).count()
    
    open_rfq = user_interests.filter(status='interested').count()
    
    # Contracts
    active_contracts = user_contracts.filter(status='active').count()
    signed_mtd = user_contracts.filter(
        confirmed_at__gte=month_start
    ).count()
    
    # In transit (from contracts)
    in_transit = user_contracts.filter(
        status='active',
        loading_to__isnull=False
    ).count()
    
    # Payment pending (simplified - you can enhance with actual payment model)
    payment_pending = user_contracts.filter(status='active').count() // 2
    pending_amount = user_contracts.filter(
        status='active'
    ).aggregate(total=Sum('deal_amount'))['total'] or 0
    pending_amount = pending_amount * 0.3  # Assume 30% pending
    
    # Issues (dummy for now - implement actual complaint model)
    issues = 0
    open_tickets = 0
    
    # Top supplier
    top_supplier_data = user_contracts.values('seller__username').annotate(
        total=Sum('deal_amount')
    ).order_by('-total').first()
    
    if top_supplier_data:
        top_supplier = top_supplier_data['seller__username']
        total_all = user_contracts.aggregate(total=Sum('deal_amount'))['total'] or 1
        top_share = (top_supplier_data['total'] / total_all) * 100
        top_share_str = f"{top_share:.1f}% of spend"
    else:
        top_supplier = "—"
        top_share_str = "—"
    
    # Avg purchase price
    avg_price = user_contracts.aggregate(avg=Avg('deal_amount'))['avg'] or 0
    
    # Get last month's avg price
    last_month_contracts = user_contracts.filter(
        confirmed_at__gte=last_month_start,
        confirmed_at__lt=month_start
    )
    last_month_avg = last_month_contracts.aggregate(avg=Avg('deal_amount'))['avg'] or 0
    
    if last_month_avg > 0:
        price_delta = ((avg_price - last_month_avg) / last_month_avg) * 100
        price_delta_str = f"{'+' if price_delta >= 0 else ''}{price_delta:.1f}%"
    else:
        price_delta_str = "—"
    
    # Prepare response data
    data = {
        'deal_products': [],
        'kpis': {
            'spent': f"₹{spent_mtd:,.2f}",
            'spent_delta': spent_delta_str,
            'active_orders': active_orders,
            'open_rfq': open_rfq,
            'active_contracts': active_contracts,
            'signed_mtd': signed_mtd,
            'in_transit': in_transit,
            'avg_eta': '2.1 days',  # Dummy - implement actual tracking
            'pay_pending': payment_pending,
            'pending_amount': f"₹{pending_amount:,.2f}",
            'issues': issues,
            'open_tickets': open_tickets,
            'top_supplier': top_supplier,
            'top_supplier_share': top_share_str,
            'avg_price': f"₹{avg_price:,.2f}/qtl",
            'avg_price_delta': price_delta_str,
        },
        'charts': {
            'trend': {
                '7D': generate_trend_data(user_contracts, days=7),
                '1M': generate_trend_data(user_contracts, days=30),
                '3M': generate_trend_data(user_contracts, days=90),
                '1Y': generate_trend_data(user_contracts, days=365),
            },
            'suppliers': get_supplier_spend_data(user_contracts),
            'commodity_mix': get_commodity_mix_data(user_contracts),
            'order_status': get_order_status_data(user_interests),
            'transport': get_transport_status_data(user_contracts),
        },
        'recent_rfqs': get_recent_rfqs(user_interests),
        'recent_orders': get_recent_orders(user_contracts),
        'transport_tracking': get_transport_tracking(user_contracts),
    }
    
    return Response(data)


def generate_trend_data(contracts, days):
    """Generate trend data for charts"""
    end_date = timezone.now()
    start_date = end_date - timezone.timedelta(days=days)
    
    if days <= 7:
        # Daily grouping
        from django.db.models.functions import TruncDay
        data = contracts.filter(
            confirmed_at__gte=start_date
        ).annotate(
            period=TruncDay('confirmed_at')
        ).values('period').annotate(
            spend=Sum('deal_amount'),
            orders=Count('id')
        ).order_by('period')
        
        labels = []
        spend = []
        orders = []
        
        for item in data:
            if item['period']:
                labels.append(item['period'].strftime('%a'))
                spend.append(float(item['spend'] or 0) / 100000)  # Convert to lakhs
                orders.append(item['orders'])
        
        return {'labels': labels, 'spend': spend, 'orders': orders}
    
    elif days <= 30:
        # Weekly grouping
        from django.db.models.functions import TruncWeek
        data = contracts.filter(
            confirmed_at__gte=start_date
        ).annotate(
            period=TruncWeek('confirmed_at')
        ).values('period').annotate(
            spend=Sum('deal_amount'),
            orders=Count('id')
        ).order_by('period')

        labels = []
        spend = []
        orders = []
        for item in data:
            if item['period']:
                labels.append(item['period'].strftime('Wk %W'))
                spend.append(float(item['spend'] or 0) / 100000)
                orders.append(item['orders'])
        return {'labels': labels, 'spend': spend, 'orders': orders}
    else:
        # Monthly grouping
        from django.db.models.functions import TruncMonth
        data = contracts.filter(
            confirmed_at__gte=start_date
        ).annotate(
            period=TruncMonth('confirmed_at')
        ).values('period').annotate(
            spend=Sum('deal_amount'),
            orders=Count('id')
        ).order_by('period')
        
        labels = []
        spend = []
        orders = []
        
        for item in data:
            if item['period']:
                labels.append(item['period'].strftime('%b'))
                spend.append(float(item['spend'] or 0) / 100000)
                orders.append(item['orders'])
        
        return {'labels': labels, 'spend': spend, 'orders': orders}


def get_supplier_spend_data(contracts):
    """Get supplier spend distribution"""
    data = contracts.values('seller__username').annotate(
        total=Sum('deal_amount')
    ).order_by('-total')[:5]
    
    return {
        'labels': [item['seller__username'] for item in data],
        'spend': [float(item['total'] or 0) / 100000 for item in data]
    }


def get_commodity_mix_data(contracts):
    """Get commodity mix by volume"""
    from django.db.models import Sum
    
    data = contracts.values('product__category__category_name').annotate(
        volume=Sum('deal_quantity')
    ).order_by('-volume')[:5]
    
    return {
        'labels': [item['product__category__category_name'] or 'Other' for item in data],
        'volume': [float(item['volume'] or 0) for item in data]
    }


def get_order_status_data(interests):
    """Get order status distribution"""
    status_counts = {
        'interested': interests.filter(status='interested').count(),
        'seller_confirmed': interests.filter(status='seller_confirmed').count(),
        'deal_confirmed': interests.filter(status='deal_confirmed').count(),
        'rejected': interests.filter(status='rejected').count(),
    }
    
    return {
        'labels': ['Interested', 'Seller Accepted', 'Deal Confirmed', 'Rejected'],
        'counts': [
            status_counts['interested'],
            status_counts['seller_confirmed'],
            status_counts['deal_confirmed'],
            status_counts['rejected'],
        ]
    }


def get_transport_status_data(contracts):
    """Get transport status distribution"""
    # Dummy data - implement actual transport model
    return {
        'labels': ['Pickup Due', 'In Transit', 'Delivered', 'Delayed'],
        'counts': [2, 5, 14, 1]
    }


def get_recent_rfqs(interests):
    """Get recent RFQs/negotiations"""
    recent = interests.select_related(
        'product', 'seller'
    ).order_by('-updated_at')[:5]
    
    data = []
    for interest in recent:
        status_map = {
            'interested': 'Negotiation',
            'seller_confirmed': 'Deal Locked',
            'deal_confirmed': 'Confirmed',
            'rejected': 'Rejected',
        }
        
        status_class_map = {
            'interested': 'info',
            'seller_confirmed': 'purp',
            'deal_confirmed': 'ok',
            'rejected': 'bad',
        }
        
        data.append({
            'id': interest.transaction_id or f"RFQ-{interest.id}",
            'product': interest.product.title,
            'quantity': f"{interest.buyer_required_quantity} {interest.product.quantity_unit or 'Qtl'}",
            'price': float(interest.buyer_offered_amount or 0),
            'seller': interest.seller.username,
            'status': status_map.get(interest.status, 'Unknown'),
            'status_class': status_class_map.get(interest.status, 'info'),
            'updated': interest.updated_at.strftime('%d %b, %H:%M'),
        })
    
    return data


def get_recent_orders(contracts):
    """Get recent orders/contracts"""
    recent = contracts.select_related(
        'product', 'seller'
    ).order_by('-confirmed_at')[:5]
    
    data = []
    for contract in recent:
        # Dummy payment and transport status - implement actual models
        data.append({
            'id': contract.contract_id,
            'seller': contract.seller.username,
            'commodity': contract.product.title,
            'quantity': f"{contract.deal_quantity} {contract.quantity_unit}",
            'value': float(contract.deal_amount),
            'payment_status': 'Paid' if contract.status == 'active' else 'Pending',
            'payment_class': 'ok' if contract.status == 'active' else 'bad',
            'transport_status': 'In Transit' if contract.loading_to else 'Delivered',
            'transport_class': 'info' if contract.loading_to else 'ok',
            'eta': '—',
        })
    
    return data


def get_transport_tracking(contracts):
    """Get transport tracking data"""
    # Dummy data - implement actual transport model
    return [
        {
            'lr': 'LR-11208',
            'contract': '#CNT-7812',
            'transporter': 'TransCo Logistics',
            'route': 'Nagpur → Pune',
            'status': 'In Transit',
            'status_class': 'info',
            'last_scan': 'Feb 03, 11:20',
            'eta': 'Feb 05',
        },
        {
            'lr': 'LR-11177',
            'contract': '#ORD-5388',
            'transporter': 'FastMove Carriers',
            'route': 'Katni → Indore',
            'status': 'In Transit',
            'status_class': 'info',
            'last_scan': 'Feb 03, 09:05',
            'eta': 'Feb 04',
        },
        {
            'lr': 'LR-11151',
            'contract': '#ORD-5407',
            'transporter': 'RoadRunner Transport',
            'route': 'Indore → Bhopal',
            'status': 'Pickup Due',
            'status_class': 'warn',
            'last_scan': 'Feb 02, 18:40',
            'eta': 'Feb 06',
        },
    ]

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test_product_api(request, product_id):
    try:
        user = request.user
        print(f"User: {user.id}, Role: {user.role}")
        
        product = Product.objects.filter(id=product_id).first()
        if not product:
            return Response({'error': 'Product not found'}, status=404)
            
        # Simple response
        return Response({
            'id': product.id,
            'title': product.title,
            'amount': str(product.amount)
        })
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response({'error': str(e)}, status=500)



def _contracts_qs_for_mobile(user):
    qs = Contract.objects.select_related('product', 'buyer', 'seller').order_by('-confirmed_at', '-id')
    if _is_admin_user(user):
        return qs
    if _is_seller_user(user):
        return qs.filter(seller=user)
    if _is_buyer_user(user):
        return qs.filter(buyer=user)
    return qs.none()


def _apply_mobile_contract_filters(request, queryset):
    status_filter = (request.GET.get('status') or '').strip().lower()
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    seller = (request.GET.get('seller') or '').strip()
    if seller.isdigit():
        queryset = queryset.filter(seller_id=int(seller))

    buyer = (request.GET.get('buyer') or '').strip()
    if buyer.isdigit():
        queryset = queryset.filter(buyer_id=int(buyer))

    search = (request.GET.get('search') or '').strip()
    if search:
        queryset = queryset.filter(
            Q(contract_id__icontains=search) |
            Q(product__title__icontains=search)
        )

    return queryset


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mobile_contract_list_api(request):
    contracts_qs = _apply_mobile_contract_filters(request, _contracts_qs_for_mobile(request.user))
    page_obj, pagination = _paginate_queryset(request, contracts_qs, page_size=15)
    serializer = ContractSerializer(page_obj.object_list, many=True, context={'request': request})
    return Response({
        'success': True,
        'results': serializer.data,
        'pagination': {
            'page': page_obj.number,
            'num_pages': page_obj.paginator.num_pages,
            'count': page_obj.paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'window': pagination['window'],
        },
    }, status=status.HTTP_200_OK)


@api_view(['GET', 'PATCH', 'PUT'])
@permission_classes([IsAuthenticated])
def mobile_contract_detail_api(request, contract_id):
    contract = Contract.objects.select_related('product', 'buyer', 'seller').filter(id=contract_id).first()
    if not contract:
        return Response({'success': False, 'message': 'Contract not found.'}, status=status.HTTP_404_NOT_FOUND)

    is_admin = _is_admin_user(request.user)

    # View permission: admin/super-admin can view any, others only own contract.
    can_view = is_admin or contract.seller_id == request.user.id or contract.buyer_id == request.user.id
    if not can_view:
        return Response({'success': False, 'message': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        serializer = ContractSerializer(contract, context={'request': request})
        return Response({'success': True, 'data': serializer.data}, status=status.HTTP_200_OK)

    # Edit permission: only admin/super-admin.
    if not is_admin:
        return Response(
            {'success': False, 'message': 'Permission denied. Only admin can edit contract.'},
            status=status.HTTP_403_FORBIDDEN
        )

    allowed_statuses = {choice[0] for choice in Contract.STATUS_CHOICES}
    update_fields = []

    if 'status' in request.data:
        next_status = str(request.data.get('status') or '').strip().lower()
        if not next_status or next_status not in allowed_statuses:
            return Response({'success': False, 'message': 'Invalid contract status.'}, status=status.HTTP_400_BAD_REQUEST)
        contract.status = next_status
        update_fields.append('status')

    if 'admin_remark' in request.data:
        contract.admin_remark = request.data.get('admin_remark') or ''
        update_fields.append('admin_remark')

    if not update_fields:
        return Response({
            'success': False,
            'message': 'No valid fields provided. Allowed fields: status, admin_remark.',
        }, status=status.HTTP_400_BAD_REQUEST)

    contract.save(update_fields=update_fields + ['updated_at'])
    serializer = ContractSerializer(contract, context={'request': request})
    return Response({
        'success': True,
        'message': 'Contract updated successfully.',
        'data': serializer.data,
    }, status=status.HTTP_200_OK)


def _force_ajax_request(request):
    """
    Reuse existing web JSON handlers by forcing AJAX header on underlying
    Django request so they always return JsonResponse (not redirects).
    """
    raw_request = request._request
    raw_request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'
    return raw_request


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mobile_offer_create_api(request):
    return web_product_create_ajax(_force_ajax_request(request))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mobile_offer_get_api(request, product_id):
    return web_product_get_ajax(_force_ajax_request(request), product_id)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mobile_offer_update_api(request, product_id):
    return web_product_update_ajax(_force_ajax_request(request), product_id)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mobile_offer_delete_api(request, product_id):
    return web_product_delete_ajax(_force_ajax_request(request), product_id)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mobile_offer_toggle_api(request, product_id):
    return web_product_toggle_ajax(_force_ajax_request(request), product_id)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mobile_offer_update_stock_api(request, product_id):
    return web_product_update_stock_ajax(_force_ajax_request(request), product_id)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mobile_offers_list_api(request):
    return web_offers_list_ajax(_force_ajax_request(request))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mobile_branch_create_api(request):
    return web_branch_create_ajax(_force_ajax_request(request))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mobile_branch_update_api(request, branch_id):
    return web_branch_update_ajax(_force_ajax_request(request), branch_id)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mobile_branch_toggle_api(request, branch_id):
    return web_branch_toggle_status_ajax(_force_ajax_request(request), branch_id)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mobile_branch_delete_api(request, branch_id):
    return web_branch_delete_ajax(_force_ajax_request(request), branch_id)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mobile_brand_create_api(request):
    return web_brand_create_ajax(_force_ajax_request(request))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mobile_brand_get_api(request, brand_id):
    return web_brand_get_ajax(_force_ajax_request(request), brand_id)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mobile_brand_update_api(request, brand_id):
    return web_brand_update_ajax(_force_ajax_request(request), brand_id)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mobile_brand_delete_api(request, brand_id):
    return web_brand_delete_ajax(_force_ajax_request(request), brand_id)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mobile_user_create_api(request):
    return web_user_create_ajax(_force_ajax_request(request))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mobile_user_get_api(request, user_id):
    return web_get_user_data(_force_ajax_request(request), user_id)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mobile_user_update_api(request, user_id):
    return web_user_update_ajax(_force_ajax_request(request), user_id)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mobile_user_update_status_api(request, user_id):
    return web_user_update_status_ajax(_force_ajax_request(request), user_id)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mobile_user_delete_api(request, user_id):
    return web_user_delete_ajax(_force_ajax_request(request), user_id)
