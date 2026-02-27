You are a senior Django architect & backend engineer.

First, deeply scan and fully understand my entire Django project structure including:
- models.py
- views.py
- serializers.py
- urls.py
- templates
- middleware
- signals
- permissions & role logic
- authentication system
- dashboard structure
- product, offers, deals, contracts, KYC, and user modules

--------------------------------------------
🎯 OBJECTIVE:
Implement a complete PRODUCTION-GRADE role-based notification system with:

- Admin
- Super Admin
- Seller
- Buyer

--------------------------------------------
🧱 CORE REQUIREMENTS:

1. Create a centralized Notification model:
   - id
   - title
   - message
   - user (ForeignKey to User)
   - role
   - type (product, interest, deal, user, password, contract, kyc, system)
   - reference_id (product_id / offer_id / deal_id / contract_id / user_id)
   - redirect_url
   - is_read (Boolean)
   - created_at
   - updated_at

--------------------------------------------
2. CREATE AUTOMATIC NOTIFICATION TRIGGERS FOR:

A) Product Added
   - When seller adds a product:
     → Notify Admin + Super Admin
     → Message: "{seller_username} added a new product"
     → Redirect → product detail page

B) Buyer Show Interest
   - When buyer submits interest:
     → Notify Seller + Admin + Super Admin
     → Message: "{buyer_username} showed interest in {product_name}"
     → Redirect → interest detail page

C) Deal Confirmed
   - When deal is confirmed:
     → Notify Admin + Super Admin + Seller + Buyer
     → Message: "Deal confirmed between {seller} and {buyer}"
     → Redirect → deal detail page

D) New User Registered
   - When new user registers:
     → Notify Admin + Super Admin
     → Message: "New user registered: {username}"
     → Redirect → user detail page

E) Password Changed
   - When any user changes password:
     → Notify that user
     → Message: "Your password was changed successfully"
     → Redirect → profile page

F) Contract Created
   - When contract is created:
     → Notify Admin + Super Admin + Seller + Buyer
     → Message: "New contract created"
     → Redirect → contract detail page

G) KYC Pending
   - When seller uploads KYC:
     → Notify Admin + Super Admin
     → Message: "New KYC submitted by {username}"
     → Redirect → KYC verification page

--------------------------------------------
3. IMPLEMENT USING DJANGO SIGNALS:

Use:
- post_save
- m2m_changed
- custom signals

So notifications are triggered automatically without breaking existing flows.

--------------------------------------------
4. API ENDPOINTS:

Create REST APIs:

- GET  /api/notifications/
    → Return all notifications for logged-in user
    → Latest first

- POST /api/notifications/read/<id>/
    → Mark single notification read

- POST /api/notifications/read-all/
    → Mark all notifications read

- GET  /api/notifications/unread-count/
    → Return unread notification count for navbar badge

--------------------------------------------
5. DASHBOARD INTEGRATION:

Implement:

- 🔔 Notification Bell Counter (real-time fetch via AJAX / fetch / axios)
- Notification Dropdown (last 10 notifications)
- Notification Page:
    → Full list
    → Pagination
    → Filters (read / unread / type)

--------------------------------------------
6. REDIRECT FLOW:

On clicking any notification:
→ Mark it as read
→ Redirect user to correct page using redirect_url

--------------------------------------------
7. ROLE SECURITY:

Ensure:
- Admin & SuperAdmin see system-wide notifications
- Seller sees:
    - Product
    - Interest
    - Deals
    - Contracts
- Buyer sees:
    - Interest
    - Deals
    - Contracts
- User never sees others’ private notifications

--------------------------------------------
8. PERFORMANCE OPTIMIZATION:

- Use select_related & prefetch_related
- Index user + is_read
- Pagination for notification list
- Avoid N+1 queries

--------------------------------------------
9. FILE MODIFICATION STRATEGY:

Implement with:
- signals.py
- services/notification_service.py
- api/notification_views.py
- serializers.py
- urls.py
- templates/dashboard/notifications.html
- JS AJAX polling (every 15 seconds)

--------------------------------------------
10. DO NOT:

❌ Do NOT break existing flows  
❌ Do NOT modify unrelated business logic  
❌ Do NOT change permission structure  

--------------------------------------------
11. DELIVER:

Provide:
- Models
- Signals
- APIs
- Serializers
- Views
- URLs
- Template
- JS logic

With FULLY WORKING, CLEAN & OPTIMIZED CODE.

--------------------------------------------
FINAL GOAL:
A COMPLETE, SCALABLE, ROLE-BASED, REAL-TIME NOTIFICATION SYSTEM.

Now analyze the full project and implement everything.