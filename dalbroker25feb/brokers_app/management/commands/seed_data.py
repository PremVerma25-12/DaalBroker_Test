from django.core.management.base import BaseCommand
from faker import Faker
from brokers_app.models import CategoryMaster, BrandMaster, TagMaster, BranchMaster, DaalUser, Product
from django.utils import timezone
from decimal import Decimal
import random

class Command(BaseCommand):
    help = 'Generate fake data for testing'

    def handle(self, *args, **options):
        fake = Faker()

        # Generate masters
        self.stdout.write('Generating categories...')
        categories = []
        category_names = ['Pulses', 'Grains', 'Spices', 'Oils', 'Fruits', 'Vegetables', 'Dairy', 'Meat', 'Seafood', 'Beverages']
        for name in category_names:
            cat = CategoryMaster.objects.create(category_name=name, is_active=True)
            categories.append(cat)

        self.stdout.write('Generating brands...')
        brands = []
        for _ in range(20):
            brand = BrandMaster.objects.create(brand_name=fake.company(), status='active')
            brands.append(brand)

        self.stdout.write('Generating tags...')
        tags = []
        tag_names = ['Organic', 'Fresh', 'Premium', 'Bulk', 'Retail', 'Wholesale', 'Exotic', 'Local', 'Imported', 'Seasonal']
        for name in tag_names:
            tag = TagMaster.objects.create(tag_name=name)
            tags.append(tag)

        self.stdout.write('Generating branches...')
        branches = []
        branch_names = ['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Kolkata', 'Hyderabad', 'Pune', 'Ahmedabad', 'Jaipur', 'Lucknow']
        for name in branch_names:
            branch = BranchMaster.objects.create(location_name=name, state=fake.state(), city=fake.city(), area=fake.city(), is_active=True)
            branches.append(branch)

        # Generate users
        self.stdout.write('Generating users...')
        users = []
        roles = ['admin', 'seller', 'buyer']
        for i in range(20):
            username = fake.user_name()
            email = fake.email()
            role = random.choice(roles)
            company_name = fake.company()
            branch = random.choice(branches)
            user = DaalUser.objects.create(
                username=username,
                email=email,
                role=role,
                company_name=company_name,
                branch=branch.location_name,  # Assuming branch is CharField
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                phone=fake.phone_number(),
                address=fake.address(),
                city=fake.city(),
                state=fake.state(),
                pincode=fake.zipcode(),
                gst_number=fake.bothify(text='??#########?'),
                pan_number=fake.bothify(text='?????####?'),
                aadhar_number=fake.bothify(text='#### #### ####'),
                bank_name=fake.company(),
                account_number=fake.bothify(text='############'),
                ifsc_code=fake.bothify(text='????0#######'),
                is_active=True,
                is_staff=(role == 'admin'),
                is_superuser=(role == 'admin' and random.choice([True, False])),
                date_joined=timezone.now(),
            )
            users.append(user)

        # Generate products
        self.stdout.write('Generating products...')
        for _ in range(50):  # More products
            seller = random.choice([u for u in users if u.role == 'seller'])
            category = random.choice(categories)
            brand = random.choice(brands)
            tags_list = random.sample(tags, random.randint(1, 3))
            title = fake.sentence(nb_words=3)
            description = fake.text()
            loading_from = fake.date_this_year()
            loading_to = fake.date_this_year()
            if loading_to < loading_from:
                loading_to = loading_from
            loading_location = f'{fake.city()}, {fake.state()} -> {fake.city()}, {fake.state()}'
            remark = fake.sentence()
            amount = Decimal(str(random.uniform(100, 10000)))
            amount_unit = random.choice(['kg', 'ton', 'qtl'])
            is_active = random.choice([True, False])

            product = Product.objects.create(
                seller=seller,
                title=title,
                description=description,
                category=category,
                brand=brand,
                loading_from=loading_from,
                loading_to=loading_to,
                loading_location=loading_location,
                remark=remark,
                amount=amount,
                amount_unit=amount_unit,
                quantity_unit=random.choice(['kg', 'ton', 'qtl']),
                original_quantity=amount,
                remaining_quantity=amount,
                available_quantity=amount,
                is_active=is_active,
                created_at=timezone.now(),
                updated_at=timezone.now(),
            )
            product.tags.set(tags_list)

        self.stdout.write(self.style.SUCCESS('Successfully generated fake data'))
