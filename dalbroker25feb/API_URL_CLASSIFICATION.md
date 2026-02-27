# API URL Classification

Generated for this project on 2026-02-27.

## Summary

- Mobile-ready API routes (JWT/DRF): 75
- Web/session AJAX routes (primarily `@login_required` + CSRF): 31
- Web page routes (HTML templates): 27

## 1) Mobile-ready APIs (for mobile app)

These are suitable for mobile integration with token auth (`Authorization: Bearer <token>`), based on current DRF/API wiring.

### Core auth/user/admin APIs

- `/api/`
- `/api/<drf_format_suffix:format>`
- `/api/adduser/`
- `/api/admin/dashboard/`
- `/api/admin/tag/create/`
- `/api/admin/tag/list/`
- `/api/admin/tag/<int:tag_id>/update/`
- `/api/admin/tag/<int:tag_id>/delete/`
- `/api/auth/register/`
- `/api/auth/login/`
- `/api/auth/logout/`
- `/api/auth/forgot-password/`
- `/api/auth/change-password/`
- `/api/auth/session-token/`
- `/api/buyer/dashboard/`
- `/api/branch/create/`
- `/api/branch/update/<int:branch_id>/`
- `/api/branch/toggle/<int:branch_id>/`
- `/api/branch/delete/<int:branch_id>/`
- `/api/brands/`
- `/api/brands/create/`
- `/api/brands/<int:brand_id>/`
- `/api/brands/<int:brand_id>/update/`
- `/api/brands/<int:brand_id>/delete/`
- `/api/filter/`
- `/api/kyc/<int:user_id>/approve/`
- `/api/kyc/<int:user_id>/reject/`
- `/api/kyc/list/`
- `/api/mobile/contracts/`
- `/api/mobile/contracts/<int:contract_id>/`
- `/api/offers/create/`
- `/api/offers/<int:product_id>/`
- `/api/offers/<int:product_id>/update/`
- `/api/offers/<int:product_id>/delete/`
- `/api/offers/<int:product_id>/toggle/`
- `/api/offers/<int:product_id>/update-stock/`
- `/api/offers/list/`
- `/api/products/filter/`
- `/api/profile/update/`
- `/api/test-product/<int:product_id>/`
- `/api/user/`
- `/api/user/profile-image/`
- `/api/users/create/`
- `/api/users/<int:user_id>/`
- `/api/users/<int:user_id>/update/`
- `/api/users/<int:user_id>/status/`
- `/api/users/<int:user_id>/delete/`

### DRF router routes

- `/api/^token/$`
- `/api/^token\.(?P<format>[a-z0-9]+)/?$`
- `/api/^token/all-with-details/$`
- `/api/^token/all-with-details\.(?P<format>[a-z0-9]+)/?$`

- `/api/^users/$`
- `/api/^users\.(?P<format>[a-z0-9]+)/?$`
- `/api/^users/(?P<pk>[^/.]+)/$`
- `/api/^users/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$`

- `/api/^categories/$`
- `/api/^categories\.(?P<format>[a-z0-9]+)/?$`
- `/api/^categories/levels/$`
- `/api/^categories/levels\.(?P<format>[a-z0-9]+)/?$`
- `/api/^categories/hierarchy/$`
- `/api/^categories/hierarchy\.(?P<format>[a-z0-9]+)/?$`
- `/api/^categories/(?P<pk>[^/.]+)/$`
- `/api/^categories/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$`

- `/api/^products/$`
- `/api/^products\.(?P<format>[a-z0-9]+)/?$`
- `/api/^products/(?P<pk>[^/.]+)/$`
- `/api/^products/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$`

- `/api/^product-images/$`
- `/api/^product-images\.(?P<format>[a-z0-9]+)/?$`
- `/api/^product-images/(?P<pk>[^/.]+)/$`
- `/api/^product-images/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$`

- `/api/^product-videos/$`
- `/api/^product-videos\.(?P<format>[a-z0-9]+)/?$`
- `/api/^product-videos/(?P<pk>[^/.]+)/$`
- `/api/^product-videos/(?P<pk>[^/.]+)\.(?P<format>[a-z0-9]+)/?$`

## 2) Web/session AJAX APIs (not ideal for mobile JWT-first usage)

These come from `brokers_app` routes and are mainly designed for browser session + CSRF flows.

- `/api/categories/create/`
- `/api/categories/<int:category_id>/`
- `/api/categories/<int:category_id>/update/`
- `/api/categories/<int:category_id>/delete/`
- `/api/categories/tree/`
- `/api/categories/<int:parent_id>/children/`
- `/api/categories/<int:category_id>/path/`
- `/api/categories/search/`

- `/api/contracts/list/`
- `/api/contracts/<int:contract_id>/`
- `/api/contracts/<int:contract_id>/update/`
- `/api/contracts/export/`

- `/api/location/states/`
- `/api/location/cities/`
- `/api/location/areas/`

- `/api/permissions/matrix/`
- `/api/permissions/update/`

- `/api/product-images/create/`
- `/api/product-images/<int:image_id>/`
- `/api/product-images/<int:image_id>/delete/`

- `/api/products/<int:product_id>/show-interest/`
- `/api/products/<int:product_id>/toggle-interest/`
- `/api/products/<int:product_id>/interests/`
- `/api/products/<int:product_id>/approve/`
- `/api/products/<int:product_id>/reject/`
- `/api/products/<int:product_id>/confirm-deal/`
- `/api/products/<int:product_id>/buyer-confirm/`

- `/api/subcategories/create/`
- `/api/subcategories/<int:subcategory_id>/`
- `/api/subcategories/<int:subcategory_id>/update/`
- `/api/subcategories/<int:subcategory_id>/delete/`

## 3) Web page routes (HTML/template views)

These are browser pages, not mobile APIs.

- `/`
- `/login/`
- `/logout/`
- `/dashboard/`
- `/dashboard/buyer/`
- `/dashboard/seller/`
- `/dashboard/transporter/`
- `/dashboard/both_sellerandbuyer/`
- `/dashboard/branch-master/`
- `/users/`
- `/users/create/`
- `/users/<int:user_id>/edit/`
- `/users/<int:user_id>/delete/`
- `/tags/`
- `/categories/`
- `/subcategories/`
- `/brands/`
- `/offers/`
- `/offers/add/`
- `/product-images/`
- `/permissions/`
- `/contracts/`
- `/api/register/`
- `/api/forgotpassword/`
- `/api/kyc/`
- `/api/intrast/`
- `/api/product-video-list/`

## 4) Contract APIs for mobile (current)

Use only these for mobile contract module:

- `GET /api/mobile/contracts/`
- `GET /api/mobile/contracts/<contract_id>/`
- `PATCH /api/mobile/contracts/<contract_id>/`
- `PUT /api/mobile/contracts/<contract_id>/`

### Permission behavior

- Login required for all contract endpoints.
- Admin/Super-admin:
  - Can list/view all contracts.
  - Can edit contract.
- Buyer/Seller:
  - Can list/view only own contracts.
  - Cannot edit contract.
