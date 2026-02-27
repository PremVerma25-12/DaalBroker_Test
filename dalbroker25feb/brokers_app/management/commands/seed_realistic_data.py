import base64
import random
import string
from datetime import date, timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from brokers_app.models import (
    BrandMaster,
    BranchMaster,
    CategoryMaster,
    DaalUser,
    Product,
    TagMaster,
)


FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Krishna", "Ishaan", "Arjun", "Rohan", "Kunal", "Siddharth", "Yash",
    "Ananya", "Aditi", "Priya", "Sneha", "Pooja", "Kavya", "Riya", "Neha", "Ira", "Meera",
]
LAST_NAMES = [
    "Sharma", "Patel", "Gupta", "Jain", "Agarwal", "Singh", "Verma", "Yadav", "Mishra", "Khanna",
]
COMPANY_SUFFIXES = [
    "Traders", "Agro Foods", "Enterprises", "Commodities", "Supply Co", "Exports", "Wholesales",
]

TAG_NAMES = [
    "Premium", "Organic", "Bulk", "Fast Delivery", "Verified", "Export Quality", "Retail Pack",
    "Farm Fresh", "Top Seller", "Trusted", "A Grade", "B Grade", "Negotiable", "Seasonal", "Warehouse Stock",
]

BRAND_NAMES = [
    "Tata Sampann", "Fortune", "Aashirvaad", "Patanjali", "24 Mantra Organic", "India Gate",
    "Daawat", "Natureland Organics", "Organic Tattva", "Dhara", "Bail Kolhu", "Everest", "Catch", "MDH", "Pansari",
]

CATEGORY_TREE = {
    "Grains": ["Wheat", "Rice", "Maize"],
    "Pulses": ["Toor Dal", "Moong Dal", "Chana Dal"],
    "Spices": ["Turmeric", "Coriander", "Red Chilli"],
    "Oilseeds": ["Soybean", "Mustard", "Groundnut"],
    "Dry Fruits": ["Almond", "Cashew", "Raisin"],
}

BRANCH_DATA = [
    ("Maharashtra", "Mumbai", "Vashi", "Vashi APMC Yard"),
    ("Maharashtra", "Pune", "Market Yard", "Pune Main Market"),
    ("Gujarat", "Ahmedabad", "Naroda", "Naroda Grain Hub"),
    ("Gujarat", "Surat", "Kadodara", "Kadodara Agro Point"),
    ("Rajasthan", "Jaipur", "Sanganer", "Sanganer Mandi"),
    ("Rajasthan", "Kota", "Anantpura", "Kota Trade Center"),
    ("Delhi", "New Delhi", "Narela", "Narela Grain Terminal"),
    ("Uttar Pradesh", "Kanpur", "Nawabganj", "Kanpur Agro Yard"),
    ("Madhya Pradesh", "Indore", "Laxmibai Nagar", "Indore Mandi"),
    ("Karnataka", "Bengaluru", "Yeshwanthpur", "YPR Agro Market"),
    ("Telangana", "Hyderabad", "Balanagar", "Hyderabad Commodity Hub"),
    ("Punjab", "Ludhiana", "Gill Road", "Ludhiana Grain Point"),
]

STATE_CODES = ["27", "24", "08", "07", "09", "23", "29", "36", "03"]

ONE_BY_ONE_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO2XwHkAAAAASUVORK5CYII="
)


def _random_pan():
    letters = "".join(random.choices(string.ascii_uppercase, k=5))
    digits = "".join(random.choices(string.digits, k=4))
    tail = random.choice(string.ascii_uppercase)
    return f"{letters}{digits}{tail}"


def _random_gst(pan):
    state_code = random.choice(STATE_CODES)
    entity_code = random.choice(string.digits)
    checksum = random.choice(string.ascii_uppercase + string.digits)
    return f"{state_code}{pan}{entity_code}Z{checksum}"


def _random_date(start_year=1980, end_year=2003):
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    return start + timedelta(days=random.randint(0, (end - start).days))


class Command(BaseCommand):
    help = "Seed realistic demo data: users, tags, categories, brands, branches, and products."

    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=20, help="Number of users to create")
        parser.add_argument("--products", type=int, default=35, help="Number of products to create")

    def handle(self, *args, **options):
        user_count = max(1, int(options["users"]))
        product_count = max(1, int(options["products"]))
        batch = timezone.now().strftime("%Y%m%d%H%M%S")

        created_counts = {
            "tags": 0,
            "categories": 0,
            "brands": 0,
            "branches": 0,
            "users": 0,
            "products": 0,
        }

        self.stdout.write(self.style.WARNING(f"Seeding realistic demo data (batch: {batch}) ..."))

        with transaction.atomic():
            tags = self._create_tags(created_counts)
            leaves, category_created = self._create_categories()
            created_counts["categories"] += category_created
            brands, brand_created = self._create_brands(created_counts)
            created_counts["brands"] += brand_created
            branches = self._create_branches(created_counts)
            users = self._create_users(user_count, batch, tags, brands, created_counts)
            products = self._create_products(product_count, users, leaves, brands, branches, created_counts)

        self.stdout.write(self.style.SUCCESS("Seed completed successfully."))
        self.stdout.write(f"Tags: {created_counts['tags']}")
        self.stdout.write(f"Categories: {created_counts['categories']}")
        self.stdout.write(f"Brands: {created_counts['brands']}")
        self.stdout.write(f"Branches: {created_counts['branches']}")
        self.stdout.write(f"Users: {created_counts['users']}")
        self.stdout.write(f"Products: {created_counts['products']}")
        self.stdout.write(f"Created user IDs: {[u.id for u in users]}")
        self.stdout.write(f"Created product IDs: {[p.id for p in products[:10]]} ... total {len(products)}")

    def _create_tags(self, created_counts):
        tags = []
        for tag_name in TAG_NAMES:
            tag, created = TagMaster.objects.get_or_create(tag_name=tag_name)
            tags.append(tag)
            if created:
                created_counts["tags"] += 1
        return tags

    def _create_categories(self):
        leaves = []
        created_total = 0
        for root_name, children in CATEGORY_TREE.items():
            root = (
                CategoryMaster.objects.filter(category_name=root_name, parent__isnull=True)
                .order_by("id")
                .first()
            )
            if not root:
                root = CategoryMaster.objects.create(
                    category_name=root_name,
                    parent=None,
                    is_active=True,
                )
                created_total += 1
            if not root.is_active:
                root.is_active = True
                root.save(update_fields=["is_active", "updated_at"])
            for child_name in children:
                child = (
                    CategoryMaster.objects.filter(category_name=child_name, parent=root)
                    .order_by("id")
                    .first()
                )
                if not child:
                    child = CategoryMaster.objects.create(
                        category_name=child_name,
                        parent=root,
                        is_active=True,
                    )
                    created_total += 1
                if not child.is_active:
                    child.is_active = True
                    child.save(update_fields=["is_active", "updated_at"])
                leaves.append(child)
        return leaves, created_total

    def _create_brands(self, created_counts):
        creator = (
            DaalUser.objects.filter(
                is_active=True,
                role__in=["admin", "super_admin"],
            )
            .order_by("id")
            .first()
        )
        brands = []
        created_total = 0
        for brand_name in BRAND_NAMES:
            brand, created = BrandMaster.objects.get_or_create(
                brand_name=brand_name,
                defaults={
                    "status": BrandMaster.STATUS_ACTIVE,
                    "created_by": creator,
                },
            )
            if created:
                created_total += 1
            elif brand.status != BrandMaster.STATUS_ACTIVE:
                brand.status = BrandMaster.STATUS_ACTIVE
                brand.save(update_fields=["status", "updated_at"])
            brands.append(brand)
        return brands, created_total

    def _create_branches(self, created_counts):
        branches = []
        for state, city, area, location_name in BRANCH_DATA:
            branch, created = BranchMaster.objects.get_or_create(
                state=state,
                city=city,
                area=area,
                defaults={
                    "location_name": location_name,
                    "is_active": True,
                },
            )
            if created:
                created_counts["branches"] += 1
            elif not branch.is_active:
                branch.is_active = True
                branch.save(update_fields=["is_active", "updated_at"])
            branches.append(branch)
        return branches

    def _create_users(self, user_count, batch, tags, brands, created_counts):
        roles = (
            ["seller"] * 6
            + ["buyer"] * 6
            + ["both_sellerandbuyer"] * 4
            + ["transporter"] * 2
            + ["admin"] * 2
        )
        if user_count > len(roles):
            roles += [random.choice(["buyer", "seller", "both_sellerandbuyer"]) for _ in range(user_count - len(roles))]
        random.shuffle(roles)
        roles = roles[:user_count]

        created_users = []
        used_mobiles = set()
        used_emails = set()
        for idx in range(user_count):
            role = roles[idx]
            first_name = random.choice(FIRST_NAMES)
            last_name = random.choice(LAST_NAMES)
            company_name = f"{last_name} {random.choice(COMPANY_SUFFIXES)}"
            password = f"Demo@{random.randint(1000, 9999)}"

            mobile = self._unique_mobile(used_mobiles)
            email = self._unique_email(first_name, last_name, idx, batch, used_emails)

            pan_number = _random_pan()
            gst_number = _random_gst(pan_number)
            kyc_submitted_at = timezone.now() - timedelta(days=random.randint(45, 320))
            kyc_approved_at = kyc_submitted_at + timedelta(days=random.randint(1, 10))

            user = DaalUser.objects.create_user(
                username=mobile,
                mobile=mobile,
                password=password,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
            user.char_password = password
            user.role = role
            user.company_name = company_name
            user.brand = random.choice(brands).brand_name if brands else "Generic Agro Brand"
            user.pan_number = pan_number
            user.gst_number = gst_number
            user.gender = random.choice(["male", "female", "other"])
            user.dob = _random_date()
            user.status = "active"
            user.account_status = "active"
            user.is_active = True
            user.kyc_status = "approved"
            user.kyc_submitted_at = kyc_submitted_at
            user.kyc_approved_at = kyc_approved_at
            user.kyc_rejected_at = None
            user.kyc_rejection_reason = ""
            user.deactivated_at = None
            user.suspended_at = None
            user.suspension_reason = ""

            user.is_buyer = False
            user.is_seller = False
            user.is_admin = False
            user.is_staff = False
            user.is_transporter = False
            user.is_both_sellerandbuyer = False
            if role == "admin":
                user.is_admin = True
                user.is_staff = True
            elif role == "seller":
                user.is_seller = True
            elif role == "buyer":
                user.is_buyer = True
            elif role == "transporter":
                user.is_transporter = True
            elif role == "both_sellerandbuyer":
                user.is_both_sellerandbuyer = True
                user.is_buyer = True
                user.is_seller = True

            user.pan_image.save(f"pan_{mobile}.png", ContentFile(ONE_BY_ONE_PNG), save=False)
            user.gst_image.save(f"gst_{mobile}.png", ContentFile(ONE_BY_ONE_PNG), save=False)
            user.shopact_image.save(f"shopact_{mobile}.png", ContentFile(ONE_BY_ONE_PNG), save=False)
            user.adharcard_image.save(f"adhar_{mobile}.png", ContentFile(ONE_BY_ONE_PNG), save=False)
            user.save()

            tag_count = random.randint(2, min(5, len(tags)))
            user.tags.set(random.sample(tags, tag_count))

            created_counts["users"] += 1
            created_users.append(user)

        return created_users

    def _create_products(self, product_count, users, categories, brands, branches, created_counts):
        sellers = [u for u in users if u.is_seller or u.is_both_sellerandbuyer or u.role in ["seller", "both_sellerandbuyer"]]
        if not sellers:
            sellers = list(
                DaalUser.objects.filter(
                    is_active=True,
                    role__in=["seller", "both_sellerandbuyer"],
                )[:5]
            )
        if not sellers:
            return []

        products = []
        quality = ["A Grade", "Premium", "FAQ", "Export Quality", "Machine Cleaned"]
        for _ in range(product_count):
            seller = random.choice(sellers)
            category = random.choice(categories)
            brand = random.choice(brands) if brands else None
            branch_from = random.choice(branches)
            branch_to = random.choice(branches)
            qty = Decimal(str(random.randint(25, 600)))
            amount = Decimal(str(random.randint(25, 240)))
            amount_unit = random.choice(["kg", "qtl", "ton"])
            title = f"{category.category_name} {random.choice(quality)}"
            loading_from_date = timezone.now().date() + timedelta(days=random.randint(1, 25))
            loading_to_date = loading_from_date + timedelta(days=random.randint(1, 10))

            product = Product.objects.create(
                title=title,
                description=(
                    f"{category.category_name} sourced from verified mandi network. "
                    "Clean stock, moisture-controlled, immediate dispatch available."
                ),
                category=category,
                brand=brand,
                seller=seller,
                amount=amount,
                amount_unit=amount_unit,
                original_quantity=qty,
                remaining_quantity=qty,
                quantity_unit=amount_unit,
                loading_from=loading_from_date,
                loading_to=loading_to_date,
                loading_location=f"{branch_from.area}, {branch_from.city} -> {branch_to.area}, {branch_to.city}",
                remark="Payment terms: 50% advance, balance against dispatch documents.",
                is_active=True,
                is_approved=True,
            )
            products.append(product)
            created_counts["products"] += 1

        return products

    def _unique_mobile(self, used_mobiles):
        while True:
            mobile = str(random.randint(6000000000, 9999999999))
            if mobile in used_mobiles:
                continue
            if DaalUser.objects.filter(mobile=mobile).exists():
                continue
            used_mobiles.add(mobile)
            return mobile

    def _unique_email(self, first_name, last_name, idx, batch, used_emails):
        domains = ["agronet.in", "mandimail.com", "tradehub.in", "supplymart.in"]
        while True:
            base = f"{first_name.lower()}.{last_name.lower()}{idx}{random.randint(10,99)}.{batch[-4:]}"
            email = f"{base}@{random.choice(domains)}"
            if email in used_emails:
                continue
            if DaalUser.objects.filter(email=email).exists():
                continue
            used_emails.add(email)
            return email
