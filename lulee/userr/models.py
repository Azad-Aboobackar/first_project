from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.timezone import now,make_aware,localtime
from datetime import date
from decimal import Decimal
# Address Model
class Address(models.Model):
    """
    Model to store address details.
    """
    user = models.ForeignKey(
        'userr.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name="addresses",
        verbose_name="User"
    )
    name=models.CharField(max_length=100,verbose_name='name',null=True)
    phone_no = models.CharField(max_length=15, null=True, blank=True, verbose_name="Phone Number")
    street_address = models.CharField(max_length=255, verbose_name="Street Address")
    city = models.CharField(max_length=100, verbose_name="City")
    state = models.CharField(max_length=100, verbose_name="State")
    pin_code = models.CharField(max_length=10, verbose_name="Pin Code")
    country = models.CharField(max_length=100, verbose_name="Country")
    is_primary = models.BooleanField(default=False) 

    def save(self, *args, **kwargs):
        if self.is_primary:
            Address.objects.filter(user=self.user, is_primary=True).update(is_primary=False)
        elif not self.pk and not Address.objects.filter(user=self.user).exists():
            self.is_primary = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.street_address}, {self.city}, {self.state}, {self.country}"


# Custom User Manager
class CustomUserManager(BaseUserManager):
    """
    Custom manager for CustomUser.
    """

    def create_user(self, email, first_name, last_name, password=None, **extra_fields):
        """
        Create and return a regular user with the given email and password.
        """
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, first_name=first_name, last_name=last_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and return a superuser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        # Set default first_name and last_name if not provided
        extra_fields.setdefault('first_name', 'Super')
        extra_fields.setdefault('last_name', 'Admin')

        if not extra_fields.get('is_staff'):
            raise ValueError('Superuser must have is_staff=True.')
        if not extra_fields.get('is_superuser'):
            raise ValueError('Superuser must have is_superuser=True.')

        # Call create_user and pass extra_fields without duplicating first_name and last_name
        return self.create_user(email, password=password, **extra_fields)


# Custom User Model
class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model that extends AbstractBaseUser.
    """
    ROLE_CHOICES = [
        ('user', 'User'),
        ('admin', 'Admin'),
    ]
    username=models.CharField(max_length=50,blank=True,null=True)
    first_name = models.CharField(max_length=50, verbose_name="First Name")
    last_name = models.CharField(max_length=50, verbose_name="Last Name")
    email = models.EmailField(unique=True, verbose_name="Email")
    address = models.ForeignKey(
        'userr.Address',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Address"
    )
    join_date = models.DateField(auto_now_add=True, verbose_name="Join Date")
    last_login = models.DateTimeField(default=timezone.now, verbose_name="Last Login")
    phone_no = models.CharField(max_length=15, null=True, blank=True, verbose_name="Phone Number")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    is_staff = models.BooleanField(default=False, verbose_name="Is Staff")
    is_superuser = models.BooleanField(default=False, verbose_name="Is Superuser")
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='user',
        verbose_name="Role"
    )
    is_blocked = models.BooleanField(default=False, verbose_name="Is Blocked")  # Add is_blocked field

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        db_table = 'userr_customuser'

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"


# Category Model
class Category(models.Model):
    name = models.CharField(max_length=255)  # Category name
    description = models.TextField(null=True, blank=True)  # Optional description
    is_active = models.BooleanField(default=True)  # To soft delete a category
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp for creation
    updated_at = models.DateTimeField(auto_now=True)  # Timestamp for last update

    def __str__(self):
        return self.name


# Product Model
class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')  # FK to Category
    name = models.CharField(max_length=255)  # Product name
    description = models.TextField()  # Product description
    is_active = models.BooleanField(default=True)  # To soft delete a product
    is_deleted = models.BooleanField(default=False)  # For soft delete functionality
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp for creation
    updated_at = models.DateTimeField(auto_now=True)  # Timestamp for last update
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_products')  # Creator of product

    def __str__(self):
        return self.name


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')  # FK to Product
    size = models.CharField(max_length=100, null=True, blank=True)  # Size of the variant
    color = models.CharField(max_length=100, null=True, blank=True)  # Color of the variant
    name = models.CharField(max_length=255)  # Name of the variant (e.g., size, color) - This could be derived from size and color
    sku = models.CharField(max_length=255, unique=True)  # Stock Keeping Unit
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Variant price
    stock_quantity = models.IntegerField(default=0)  # Number of variant items in stock
    is_active = models.BooleanField(default=True)  # To soft delete a variant
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp for creation
    updated_at = models.DateTimeField(auto_now=True)  # Timestamp for last update

    def save(self, *args, **kwargs):
        # Auto-generate 'name' based on size and color if they are provided
        if self.size and self.color:
            self.name = f"{self.size}-{self.color}"
        super(ProductVariant, self).save(*args, **kwargs)

    def get_discounted_price(self):
        """
        Calculate the discounted price for the product variant
        based on the highest applicable category or product offer.
        """
        today = date.today()

        # Get category offers
        category_offers = Offer.objects.filter(
            offer_type='category',
            category=self.product.category,
            end_date__gte=today,
            is_listed=True 
        ).order_by('-discount')

        # Get product offers
        product_offers = Offer.objects.filter(
            offer_type='product',
            product=self.product,
            end_date__gte=today,
            is_listed=True 
        ).order_by('-discount')

        # Determine the highest discount
        category_discount = category_offers.first().discount if category_offers.exists() else 0
        product_discount = product_offers.first().discount if product_offers.exists() else 0

        highest_discount = max(category_discount, product_discount)

        # Calculate discounted price
        discounted_price = self.price * (1 - (highest_discount / Decimal('100')))
        return round(discounted_price, 2)
    

    def __str__(self):
        return f"{self.product.name} - {self.name} (SKU: {self.sku})"



# Product Image Model
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')  # Existing FK to Product
    variant = models.ForeignKey(
        ProductVariant, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='images'
    )  # FK to ProductVariant
    image_url = models.URLField(default="https://via.placeholder.com/150")  # Default image
    is_primary = models.BooleanField(default=False)  # Marks primary image
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp for creation

    def __str__(self):
        return f"Image for {self.product.name} - Variant: {self.variant.name if self.variant else 'None'}"




class CartItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)
    color = models.CharField(max_length=50, blank=True, default="")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Validate quantity
        if self.quantity > 5:
            raise ValidationError("Maximum 5 items allowed per product variant.")
        if self.quantity > self.product_variant.stock_quantity:
            raise ValidationError("Quantity exceeds available stock.")

        # Use the get_discounted_price() method to calculate the price
        price_to_use = self.product_variant.get_discounted_price()

        # Calculate total amount
        self.total_amount = price_to_use * self.quantity

        super().save(*args, **kwargs)


    def get_variant_image(self):
        primary_image = self.product_variant.images.filter(is_primary=True).first()
        return primary_image.image.url if primary_image else None

    def __str__(self):
        return f"{self.product_variant.product.name} - {self.product_variant} x {self.quantity}"




class Order(models.Model):
    STATUS_CHOICES = [

        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELED', 'Canceled'),
        ('RETURN_PENDING', 'Return pending'),
        ('RETURNED','Returned'),
        ('PAYMENT_PENDING', 'Payment Pending'),
    ]
    PAYMENT_CHOICES = [
        ('COD', 'Cash On Delivery'),
        ('RAZORPAY', 'Razorpay'),
        ('WALLET', 'Wallet'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    payment = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='COD')
    shipping_address = models.ForeignKey('Address', on_delete=models.SET_NULL, null=True, blank=True)
    order_date = models.DateField(auto_now_add=True)
    delivery_date = models.DateField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    shipping_chrg = models.FloatField(default=0)
    order_no = models.CharField(max_length=100, unique=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    razorpay_order_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_payment_status = models.CharField(max_length=20, default='PENDING')
    razorpay_signature = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"

    def save(self, *args, **kwargs):
        if not self.pk:  # For new orders
            # Get coupon discount from session if exists
            request = kwargs.pop('request', None)
            if request and request.session.get('discount_amount'):
                try:
                    # Apply discount to total
                    discount = Decimal(request.session.get('discount_amount', '0'))
                    self.total = self.total - discount
                    
                    # Clear coupon data from session
                    request.session.pop('coupon_id', None)
                    request.session.pop('discount_amount', None)
                    request.session.pop('new_total', None)
                except Exception:
                    pass

        # Handle Razorpay payment status
        if self.razorpay_payment_status != 'PAID' and self.payment == 'razorpay':
            self.status = 'PAYMENT_PENDING'

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.order_no} - {self.status}"


class OrderItem(models.Model):
    # Fields for the OrderItem model
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELED', 'Canceled'),
        ('RETURN_PENDING', 'Return Pending'),
        ('RETURNED', 'Returned'),
        ('PAYMENT_PENDING', 'Payment Pending'),
    ]
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    product_variant = models.ForeignKey('ProductVariant', on_delete=models.CASCADE)
    quantity = models.IntegerField()
    total_amount = models.FloatField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    def __str__(self):
        return f"Item: {self.product_name} - {self.quantity}"

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"


class OrderItemReturn(models.Model):
    order_item = models.OneToOneField('OrderItem', on_delete=models.CASCADE, related_name='order_item_return')
    sizing_issues = models.BooleanField(default=False)
    damaged_item = models.BooleanField(default=False)
    incorrect_order = models.BooleanField(default=False)
    delivery_delays = models.BooleanField(default=False)
    other_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.pk:  # If it's a new return request
            self.order_item.status = 'RETURN_PENDING'
            self.order_item.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Return for Order Item #{self.order_item.id} - Created on {self.created_at}"


class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product_variant = models.ForeignKey('ProductVariant', on_delete=models.CASCADE)
    added_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product_variant')

    def __str__(self):
        return f"{self.user.username}'s wishlist item: {self.product_variant}"
    


class Wallet(models.Model):
    user=models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='wallet'
    )
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.email}'s Wallet" 

    def credit(self, amount, description=""):
        """
        Add amount to the wallet balance and log a credit transaction.
        """
        if amount <= 0:
            raise ValueError("Amount must be positive for credit.")
        self.balance += amount
        self.save()
        self.transactions.create(
            transaction_type='credit',
            amount=amount,
            description=description
        )

    def debit(self, amount, description=""):
        """
        Deduct amount from the wallet balance and log a debit transaction.
        """
        if amount <= 0:
            raise ValueError("Amount must be positive for debit.")
        if self.balance < amount:
            raise ValueError("Insufficient balance for this transaction.")
        self.balance -= amount
        self.save()
        self.transactions.create(
            transaction_type='debit',
            amount=amount,
            description=description
        )


class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    )

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type.capitalize()} - ₹{self.amount}"
    



class Coupon(models.Model):
    code = models.CharField(max_length=20, unique=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    valid_from = models.DateField()
    valid_until = models.DateField()
    is_active = models.BooleanField(default=True)
    is_listed=models.BooleanField(default=True)

    def __str__(self):
        return self.code
    
    def save(self, *args, **kwargs):
        # Deactivate coupon if the valid_until date is in the past
        if self.valid_until < now().date():
            self.is_active = False
        super().save(*args, **kwargs)

    def is_valid(self):
        today = now().date()  # Get the current date only
        return self.is_active and self.valid_from <= today <= self.valid_until


# -------------------------------------------------------------------------------------

class Offer(models.Model):
    TYPE_CHOICES = [
        ('category', 'Category'),
        ('product', 'Product'),  # Changed to apply to product
    ]

    name = models.CharField(max_length=255)
    discount = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.TextField()
    offer_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    end_date = models.DateField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)  # Linked to Product instead of ProductVariant
    is_listed=models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def is_valid(self):
        """Check if the offer is still valid."""
        from django.utils import timezone

        return self.end_date >= timezone.now().date()
    


class Banner(models.Model):
    POSITION_CHOICES = [
        (1, 'Banner 1 (Top)'),
        (2, 'Banner 2 (Middle)'),
        (3, 'Banner 3 (Bottom)')
    ]
    
    title = models.CharField(max_length=200)
    image_url = models.URLField(max_length=500)
    link = models.URLField(max_length=200, default='#')
    position = models.IntegerField(choices=POSITION_CHOICES, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['position']

    def __str__(self):
        return f"{self.title} - Position {self.position}"