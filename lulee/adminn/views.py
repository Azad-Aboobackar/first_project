from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from userr.models import Category,Product,ProductImage,ProductVariant,Order,OrderItem, Coupon,Offer,Wallet,OrderItemReturn,Banner
from cloudinary.uploader import upload
import cloudinary.uploader
from decimal import Decimal 
from django.db.models import Prefetch
from django.views.decorators.cache import never_cache
from django.contrib.auth import get_user_model
from django.db import transaction, connection
from django.core.paginator import Paginator
CustomUser = get_user_model()


# Create your views here.
# Admin Login Page
@never_cache
def admin_login(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        
        user = authenticate(request, email=email, password=password)
        
        if user is not None and user.is_superuser:
            login(request, user)
            return redirect('admin_dashboard')
        else:
            messages.error(request, "Invalid credentials or unauthorized access. Superuser access only.")
    
    return render(request, 'admin/admin_login.html') 

# Admin Dashboard
@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        return redirect('admin_login')
    return render(request, 'admin/dashboard.html')

# User Management
@login_required
def user_management(request):
    if not request.user.is_staff:
        return redirect('admin_login')

    # Exclude superusers from the user list
    user_list = CustomUser.objects.filter(is_superuser=False).order_by('-id')
    
    # Set items per page
    items_per_page = 5
    paginator = Paginator(user_list, items_per_page)
    
    # Get page number from URL parameters
    page = request.GET.get('page', 1)
    
    try:
        users = paginator.page(page)
    except PageNotAnInteger:
        users = paginator.page(1)
    except EmptyPage:
        users = paginator.page(paginator.num_pages)

    # Calculate the visible page numbers
    current_page = users.number
    total_pages = paginator.num_pages

    # Create a range of page numbers to display
    start_range = max(current_page - 2, 1)
    end_range = min(current_page + 2, total_pages)

    if start_range > 2:
        start_range = max(1, start_range)
    if end_range < total_pages - 1:
        end_range = min(total_pages, end_range)

    page_range = range(start_range, end_range + 1)

    context = {
        'users': users,
        'total_users': user_list.count(),
        'page_range': page_range,
        'current_page': current_page,
        'total_pages': total_pages,
    }
    
    return render(request, 'admin/manage_users.html', context)

# Admin Logout
@login_required
def admin_logout(request):
    logout(request)
    return redirect('admin_login')

# Toggle User Status
def toggle_user_status(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    user.is_active = not user.is_active
    user.save()

    if user.is_active:
        messages.success(request, f'{user.email} is now active.')
    else:
        messages.success(request, f'{user.email} is now blocked.')

    return redirect('user_management')

# Edit User
def edit_user(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.phone_no = request.POST.get('phone_no', user.phone_no)

        user.save()

        messages.success(request, f'{user.email} details updated successfully.')
        return redirect('user_management')

    return render(request, 'admin/edit_user.html', {'user': user})


def category_list(request):
    categories = Category.objects.all()
    return render(request, 'admin/category.html', {'categories': categories})

def create_category(request):
    if request.method == 'POST':
        name = request.POST['name']
        description = request.POST['description']

        # Check if a category with the same name already exists
        if Category.objects.filter(name__iexact=name).exists():
            messages.error(request, "A category with this name already exists.")
            return redirect('category_management')

        # Create the category if it doesn't exist
        Category.objects.create(name=name, description=description, is_active=True)
        messages.success(request, "Category created successfully.")
        return redirect('category_management')
    
    return redirect('category_management')


def edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        category.name = request.POST['name']
        category.description = request.POST['description']
        category.save()
        messages.success(request, "Category updated successfully.")
        return redirect('category_management')
    return render(request, 'admin/edit_category.html', {'category': category})


def delete_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    category.delete()
    messages.success(request, "Category deleted successfully.")
    return redirect('category_management')


def toggle_category_status(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    category.is_active = not category.is_active
    category.save()
    messages.success(request, "Category status updated successfully.")
    return redirect('category_management')





from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Prefetch

def product_management(request):
    # Get all products with prefetched relationships
    product_list = Product.objects.prefetch_related(
        Prefetch('variants')
    ).select_related('category').order_by('-id')
    
    # Set items per page
    items_per_page = 5
    paginator = Paginator(product_list, items_per_page)
    
    # Get page number from URL parameters
    page = request.GET.get('page')
    if not page:
        page = 1
    
    try:
        # Convert page to integer and get the page
        page = int(page)
        products = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        # If page is not an integer or out of range, deliver first page
        products = paginator.page(1)
    
    # Calculate the visible page numbers
    max_pages = paginator.num_pages
    current_page = products.number
    
    # Create a list of page numbers to display
    page_numbers = []
    if max_pages <= 5:
        page_numbers = [num for num in range(1, max_pages + 1)]
    else:
        if current_page <= 3:
            page_numbers = [num for num in range(1, 6)]
        elif current_page >= max_pages - 2:
            page_numbers = [num for num in range(max_pages - 4, max_pages + 1)]
        else:
            page_numbers = [num for num in range(current_page - 2, current_page + 3)]

    context = {
        'products': products,
        'total_products': product_list.count(),
        'page_numbers': page_numbers,
        'current_page': current_page,
        'has_previous': products.has_previous(),
        'has_next': products.has_next(),
        'previous_page': current_page - 1,
        'next_page': current_page + 1,
        'max_pages': max_pages,
    }
    
    return render(request, 'admin/manage_products.html', context)

def toggle_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_active = not product.is_active
    product.save()
    return redirect('product_management')

def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    return redirect('product_management')




def add_product(request):
    categories = Category.objects.all()

    if request.method == 'POST':
        name = request.POST.get('name')
        category_id = request.POST.get('category')
        price = request.POST.get('price')
        description = request.POST.get('description')  # Get description
        size = request.POST.get('size')
        color = request.POST.get('color')

        if not all([name, category_id, price, description, size, color]):
            messages.error(request, "All fields are required.")
            return redirect('add_product')

        # Validate price
        if not price.replace('.', '', 1).isdigit():
            messages.error(request, "Price must be a numeric value.")
            return redirect('add_product')

        price = Decimal(price)

        category = Category.objects.get(id=category_id)
        product = Product.objects.create(
            name=name,
            category=category,
            description=description,  # Save description
            created_by=request.user
        )

        # Create Product Variant for size, color and stock
        stock = request.POST.get('stock')
        if not stock.isdigit():
            messages.error(request, "Stock must be a numeric value.")
            return redirect('add_product')

        stock = int(stock)

        sku = f"{name[:3]}-{size}-{color}-{product.id}".upper()
        if ProductVariant.objects.filter(sku=sku).exists():
            messages.error(request, "Duplicate SKU detected. Please try again.")
            return redirect('add_product')

        product_variant = ProductVariant.objects.create(
            product=product,
            name=f"{size}-{color}",
            price=price,  # Variant price could be different
            sku=sku,
            size=size,  # Save size
            color=color,  # Save color
            stock_quantity=stock  # Assign stock to the variant
        )

             # Image Uploads
        for image_field in ['image1', 'image2', 'image3', 'image4']:
            if image_field in request.FILES:
                image = request.FILES[image_field]
                try:
                    upload_result = upload(image)
                    image_url = upload_result['url']
                    
                    # Ensure the `product_variant` instance is used here
                    ProductImage.objects.create(
                        product=product,  # Associate the image with the product
                        variant=product_variant,  # Associate the image with the specific variant
                        image_url=image_url,
                        is_primary=(image_field == 'image1')  # Mark the first image as primary
                    )
                except Exception as e:
                    messages.error(request, f"Failed to upload {image_field}: {e}")


        messages.success(request, "Product added successfully!")
        return redirect('product_management')

    return render(request, 'admin/add_product.html', {'categories': categories})

def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    categories = Category.objects.all()
    existing_images = product.images.all()  # Assuming a related `ProductImage` model
    additional_images_count = 4 - len(existing_images)  # Number of additional image fields needed

    # Get the first variant (if any) to pre-populate size, color, and stock
    variant = product.variants.first()  # Assuming there's at least one variant

    # Default values for size, color, and stock if no variant exists
    size = variant.size if variant else ''
    color = variant.color if variant else ''
    stock_quantity = variant.stock_quantity if variant else 0  # Stock for the first variant

    if request.method == 'POST':
        # Validate and Update product basic details
        name = request.POST.get('name')
        category_id = request.POST.get('category')
        price = request.POST.get('price')
        description = request.POST.get('description')
        size = request.POST.get('size')
        color = request.POST.get('color')
        stock = request.POST.get('stock')

        # Validate required fields
        if not all([name, category_id, price, description, size, color, stock]):
            messages.error(request, "All fields are required.")
            return redirect('edit_product', product_id=product.id)
        # Validate price
        if not price.replace('.', '', 1).isdigit():
            messages.error(request, "Price must be a numeric value.")
            return redirect('edit_product', product_id=product.id)

        price = Decimal(price)

        # Update product details
        product.name = name
        product.category_id = category_id  # Update category
        product.description = description  # Update description

        # Update product images
        for i in range(1, 5):  # For 4 image fields
            image_field = request.FILES.get(f'image-{i}')
            if image_field:
                try:
                    result = cloudinary.uploader.upload(image_field)
                    image_url = result.get('secure_url')

                    if i <= len(existing_images):
                        existing_image = existing_images[i - 1]
                        existing_image.image_url = image_url
                        existing_image.save()
                    else:
                        ProductImage.objects.create(product=product, image_url=image_url)

                except Exception as e:
                    messages.error(request, f"Error uploading image-{i}: {str(e)}")

        # Handle stock input and validation for the variant
        if not stock.isdigit():
            messages.error(request, "Stock must be a numeric value.")
            return redirect('edit_product', product_id=product.id)

        stock = int(stock)

        # Fetch the first variant (or the only one) for the product
        variant = product.variants.first()  # Get the first variant (assumes only one variant for now)

        if variant:
            # Update the existing variant (only one variant for now)
            variant.price = price
            variant.stock_quantity = stock  # Update stock quantity
            variant.name = f"{size}-{color}"  # Update name (size-color combination)
            variant.size = size  # Update size
            variant.color = color  # Update color
            variant.save()

            # Optionally update SKU if needed
            variant.sku = f"{name[:3]}-{size}-{color}-{product.id}".upper()
            variant.save()
        else:
            # If no variant exists, show an error message
            messages.error(request, "No variant found for this product. Please add a variant first.")
            return redirect('edit_product', product_id=product.id)

        # Save the product after variant update
        product.save()

        messages.success(request, "Product updated successfully!")
        return redirect('product_management')  # Redirect to product management page after successful edit

    return render(request, 'admin/edit_product.html', {
        'product': product,
        'categories': categories,
        'existing_images': existing_images,
        'additional_images_count': additional_images_count,
        'size': size,
        'color': color,
        'stock_quantity': stock_quantity,  # Pass the stock quantity to the template
    })

def add_variant(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        size = request.POST.get('size')
        color = request.POST.get('color')
        price = request.POST.get('price')
        stock_quantity = request.POST.get('stock')
        images = request.FILES.getlist('images')

        # Generate SKU
        sku = f"{product_id}-{size or 'NA'}-{color or 'NA'}"
        
        try:
            # Create ProductVariant
            variant = ProductVariant.objects.create(
                product=product,
                size=size,
                color=color,
                price=price,
                stock_quantity=stock_quantity,
                sku=sku,
                is_active=True
            )

            # Upload images to Cloudinary and associate them with the variant
            for image_field in ['image1', 'image2', 'image3', 'image4']:
                if image_field in request.FILES:
                    image = request.FILES[image_field]
                    try:
                        # Upload the image to Cloudinary
                        upload_result = cloudinary.uploader.upload(image)
                        image_url = upload_result['secure_url']

                        # Create a ProductImage object
                        ProductImage.objects.create(
                            product=product,          # Associate with the product
                            variant=variant,          # Associate with the specific variant
                            image_url=image_url,      # Store the Cloudinary URL
                            is_primary=(image_field == 'image1')  # Mark the first image as primary
                        )
                    except Exception as e:
                        messages.error(request, f"Failed to upload {image_field}: {e}")


            messages.success(request, 'Product variant created successfully.')
            return redirect('product_management')

        except Exception as e:
            messages.error(request, f"Error creating variant: {str(e)}")
            return redirect('add_variant', product_id=product.id)
    
    return render(request, 'admin/add_variant.html', {'product': product})


def manage_variant(request, product_id):
    # Get the product by its ID
    product = get_object_or_404(Product, id=product_id)
    
    # Get all variants associated with the product
   
    variants = ProductVariant.objects.filter(product=product)
    context = {
        'product': product,
        'variants': variants,
    }
    
    return render(request, 'admin/manage_variant.html', context)


def edit_product_variant(request, variant_id):
    # Fetch the product variant and its associated images
    variant = get_object_or_404(ProductVariant, id=variant_id)
    images = ProductImage.objects.filter(variant=variant)

    if request.method == 'POST':
        # Editing the ProductVariant fields directly
        variant.size = request.POST.get('size', variant.size)
        variant.color = request.POST.get('color', variant.color)
        variant.price = request.POST.get('price', variant.price)
        variant.stock_quantity = request.POST.get('stock_quantity', variant.stock_quantity)
        variant.is_active = 'is_active' in request.POST  # Check if the checkbox is ticked

        # Saving the updated variant
        variant.save()

        # Handling image updates (following your image upload method)
        existing_images = list(images)  # Convert to list to easily access by index
        for i in range(1, 5):  # For 4 image fields
            image_field = request.FILES.get(f'image-{i}')
            if image_field:
                try:
                    result = cloudinary.uploader.upload(image_field)
                    image_url = result.get('secure_url')

                    if i <= len(existing_images):
                        # Update existing image URL
                        existing_image = existing_images[i - 1]
                        
                        # Optional: Delete old image from Cloudinary before updating
                        if existing_image.image_url:
                            public_id = existing_image.image_url.split('/')[-1].split('.')[0]
                            try:
                                cloudinary.uploader.destroy(public_id)  # Delete the old image from Cloudinary
                            except cloudinary.exceptions.Error as e:
                                print(f"Error deleting old image from Cloudinary: {e}")
                        
                        # Update the image URL and save
                        existing_image.image_url = image_url
                        existing_image.save()

                except Exception as e:
                    messages.error(request, f"Error uploading image-{i}: {str(e)}")

        return redirect('manage_variant', product_id=variant.product.id)  # Redirect after saving changes

    return render(request, 'admin/edit_variant.html', {
        'variant': variant,
        'images': images
    })

def delete_variant(request, variant_id):
    if request.method == 'POST':
        variant = get_object_or_404(ProductVariant, id=variant_id)
        product_id = variant.product.id  
        images = ProductImage.objects.filter(variant=variant)
        for image in images:
            try:
                cloudinary.uploader.destroy(image.image_url.split('/')[-1].split('.')[0])
            except Exception as e:
                messages.error(request, f"Error deleting image: {str(e)}")
            
            image.delete()  
        variant.delete()
        messages.success(request, "Variant and associated images deleted successfully.")

        return redirect('manage_variant', product_id=product_id)
    
def delete_user(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('DELETE FROM userr_customuser WHERE id = %s', [user.id])
        messages.success(request, "User deleted successfully.")
    except Exception as e:
        messages.error(request, f"Error deleting user: {str(e)}")
    return redirect('user_management')




def admin_order_list(request):
    # Get all orders with related data
    orders = (
        Order.objects
        .select_related('user', 'shipping_address')
        .prefetch_related('order_items')
        .order_by('-order_date')
    )
    
    # Set 5 orders per page
    items_per_page = 5
    
    # Create paginator instance
    paginator = Paginator(orders, items_per_page)
    
    # Get the current page number from request GET parameters
    page_number = request.GET.get('page', 1)
    
    try:
        # Get the Page object for the current page
        page_obj = paginator.get_page(page_number)
    except:
        # If page is not an integer or out of range, deliver first page
        page_obj = paginator.get_page(1)
    
    context = {
        'orders': page_obj,  # Pass the page object instead of all orders
        'page_obj': page_obj,  # Additional pagination info
    }
    
    return render(request, 'admin/admin_order_list.html', context)

def admin_order_detail(request, order_no):
    order = get_object_or_404(Order, order_no=order_no)
    order_items = OrderItem.objects.filter(order=order)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        valid_statuses = ['Pending', 'Confirmed', 'Shipped', 'Delivered', 'Cancelled','Returned','Return pending']

        if new_status in valid_statuses:
            if new_status == 'Cancelled' or new_status=='Returned' and order.status != 'Cancelled' or order.status=='Returned':
                # Restore stock quantities for cancelled orders
                for item in order_items:
                    product_variant = item.product_variant
                    product_variant.stock_quantity += item.quantity
                    product_variant.save()

            # Update order status
            order.status = new_status
            order.save()

            # Update status for each order item
            for item in order_items:
                item.status = new_status
                item.save()

            messages.success(request, 'Order status updated successfully!')
        else:
            messages.error(request, 'Invalid status selected.')

        return redirect('admin_order_detail', order_no=order_no)

    return render(request, 'admin/admin_order_detail.html', {'order': order, 'order_items': order_items})













from django.shortcuts import render,redirect,get_object_or_404
from userr.models import Coupon,Offer
from datetime import datetime
from django.utils.timezone import make_aware
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core import serializers
from django.utils.dateparse import parse_date
from django.utils.timezone import now,localdate







@staff_member_required
def add_coupon(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        discount_percentage = request.POST.get('discount_percentage')
        valid_from = parse_date(request.POST.get('valid_from'))  # Parse as date
        valid_until = parse_date(request.POST.get('valid_until'))  # Parse as date
        is_active = request.POST.get('is_active') == 'on'

        # Validation
        if not code or not discount_percentage or not valid_from or not valid_until:
            messages.error(request, "All fields are required.")
            return redirect('add_coupon')
        elif Coupon.objects.filter(code__iexact=code).exists():
            messages.error(request, "A coupon with this code already exists.")
            return redirect('add_coupon')
        elif not (1 <= float(discount_percentage) <= 100):
            messages.error(request, "Discount percentage must be between 1 and 100.")
            return redirect('add_coupon')
        elif valid_from < localdate():  # Ensure 'valid_from' is today or in the future
            messages.error(request, "The 'valid from' date cannot be in the past.")
            return redirect('add_coupon')
        elif valid_from > valid_until:
            messages.error(request, "The 'valid from' date cannot be later than the 'valid until' date.")
            return redirect('add_coupon')
        else:
            Coupon.objects.create(
                code=code,
                discount_percentage=discount_percentage,
                valid_from=valid_from,
                valid_until=valid_until,
                is_active=is_active
            )
            messages.success(request, "Coupon added successfully.")
            return redirect('coupon_list')

    return render(request, 'admin/add_coupon.html')


@staff_member_required
def edit_coupon(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    if request.method == "POST":
        code = request.POST.get('code')
        discount_percentage = request.POST.get('discount_percentage')
        valid_from = parse_date(request.POST.get('valid_from'))  # Parse as date
        valid_until = parse_date(request.POST.get('valid_until'))  # Parse as date
        is_active = request.POST.get('is_active') == 'on'

        # Validation
        if not code or not discount_percentage or not valid_from or not valid_until:
            messages.error(request, "All fields are required.")
            return redirect('edit_coupon',pk=coupon.pk)
        elif Coupon.objects.exclude(pk=pk).filter(code__iexact=code).exists():  # Ensure the new code is unique
            messages.error(request, "A coupon with this code already exists.")
            return redirect('edit_coupon',pk=coupon.pk)
        elif not (1 <= float(discount_percentage) <= 100):
            messages.error(request, "Discount percentage must be between 1 and 100.")
            return redirect('edit_coupon',pk=coupon.pk)
        elif valid_from < localdate():  # Ensure 'valid_from' is today or in the future
            messages.error(request, "The 'valid from' date cannot be in the past.")
            return redirect('edit_coupon',pk=coupon.pk)
        elif valid_from > valid_until:
            messages.error(request, "The 'valid from' date cannot be later than the 'valid until' date.")
            return redirect('edit_coupon',pk=coupon.pk)
        else:
            coupon.code = code
            coupon.discount_percentage = discount_percentage
            coupon.valid_from = valid_from
            coupon.valid_until = valid_until
            coupon.is_active = is_active
            coupon.save()
            messages.success(request, "Coupon updated successfully.")
            return redirect('coupon_list')

    return render(request, 'admin/edit_coupon.html', {'coupon': coupon})


@staff_member_required
def remove_coupon(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    if request.method == 'POST':
        if coupon.is_listed:
            coupon.is_listed = False
            messages.success(request, 'Coupon has been unlisted.')
        else:
            coupon.is_listed = True
            messages.success(request, 'Coupon has been listed.')
        coupon.save()
        return redirect('coupon_list')


@staff_member_required
def coupon_list(request):

    coupons = Coupon.objects.all().order_by('valid_until')

    for coupon in coupons:
        if coupon.valid_until < now().date():
            coupon.is_active=False
            coupon.save()
    return render(request, 'admin/coupon_list.html', {'coupons': coupons})



# -------------------------------------------------------------------------------

@staff_member_required
def offer_list(request):
    offers=Offer.objects.all()
    return render(request,'admin/offer_list.html',{'offers':offers})



@staff_member_required
def add_offer(request):
    categories = Category.objects.all()
    products = Product.objects.all() 

    # Serialize the data
    serialized_categories = serializers.serialize('json', categories)
    serialized_products = serializers.serialize('json', products)

    if request.method == "POST":
        name = request.POST.get("name")
        discount = request.POST.get("discount")
        description = request.POST.get("description")
        offer_type = request.POST.get("offer_type")
        selected_id = request.POST.get("selected_id")
        end_date = request.POST.get("end_date")

        if not (name and discount and description and offer_type and selected_id and end_date):
            messages.error(request, "All fields are required.")
            return redirect('add_offer')
        if not (1 <= float(discount) <= 100):
            messages.error(request, "Discount must be between 1 and 100.")
            return redirect('add_offer')
        if localdate() > parse_date(end_date):
            messages.error(request, "End date cannot be in the past.")
            return redirect('add_offer')
        if Offer.objects.filter(name__iexact=name).exists():
            messages.error(request, "An offer with this name already exists.")
            return redirect('add_offer')
        if offer_type == "category" and not Category.objects.filter(pk=selected_id).exists():
            messages.error(request, "Selected category does not exist.")
            return redirect('add_offer')
        if offer_type == "product" and not Product.objects.filter(pk=selected_id).exists():
            messages.error(request, "Selected product does not exist.")
            return redirect('add_offer')

        offer = Offer(
            name=name,
            discount=discount,
            description=description,
            offer_type=offer_type,
            end_date=end_date,
        )

        if offer_type == "category":
            offer.category_id = selected_id
        elif offer_type == "product":
            offer.product_id = selected_id 

        offer.save()
        messages.success(request, "Offer added successfully")
        return redirect('offer_list')

    return render(request, "admin/add_offer.html", {
        "categories": serialized_categories,
        "products": serialized_products
    })



@staff_member_required
def edit_offer(request, pk):
    # Get the offer object to edit
    offer = get_object_or_404(Offer, pk=pk)
    
    categories = Category.objects.all()
    products = Product.objects.all()  # Get all products

    # Serialize categories and products
    serialized_categories = serializers.serialize('json', categories)
    serialized_products = serializers.serialize('json', products)

    if request.method == "POST":
        name = request.POST.get("name")
        discount = request.POST.get("discount")
        description = request.POST.get("description")
        offer_type = request.POST.get("offer_type")
        selected_id = request.POST.get("selected_id")
        end_date = request.POST.get("end_date")

        if not (name and discount and description and offer_type and selected_id and end_date):
            messages.error(request, "All fields are required.")
            return redirect('edit_offer', pk=pk)
        if not (1 <= float(discount) <= 100):
            messages.error(request, "Discount must be between 1 and 100.")
            return redirect('edit_offer', pk=pk)
        if localdate() > parse_date(end_date):
            messages.error(request, "End date cannot be in the past.")
            return redirect('edit_offer', pk=pk)
        if Offer.objects.filter(name__iexact=name).exclude(pk=pk).exists():
            messages.error(request, "An offer with this name already exists.")
            return redirect('edit_offer', pk=pk)
        if offer_type == "category" and not Category.objects.filter(pk=selected_id).exists():
            messages.error(request, "Selected category does not exist.")
            return redirect('edit_offer', pk=pk)
        if offer_type == "product" and not Product.objects.filter(pk=selected_id).exists():
            messages.error(request, "Selected product does not exist.")
            return redirect('edit_offer', pk=pk)

        offer.name = name
        offer.discount = discount
        offer.description = description
        offer.offer_type = offer_type
        offer.end_date = end_date

        if offer_type == "category":
            offer.category_id = selected_id
            offer.product = None  
        elif offer_type == "product":
            offer.product_id = selected_id  
            offer.category = None  

        offer.save()
        messages.success(request, "Offer updated successfully")
        return redirect('offer_list')

    return render(request, "admin/edit_offer.html", {
        "offer": offer,
        "categories": serialized_categories,
        "products": serialized_products
    })



@staff_member_required
def delete_offer(request, pk):
    offer = get_object_or_404(Offer, pk=pk)
    if request.method == 'POST':
        if offer.is_listed:
            offer.is_listed = False
            messages.success(request, 'Offer has been unlisted.')
        else:
            offer.is_listed = True
            messages.success(request,'Offer has been listed.')
        offer.save()
        return redirect('offer_list')





# Add to your view
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count
from django.db.models.functions import TruncYear, TruncMonth, TruncWeek, TruncDate
from decimal import Decimal
from datetime import datetime, timedelta
from io import BytesIO
import xlsxwriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from django.core.serializers.json import DjangoJSONEncoder
import json

@staff_member_required
def sales_report(request):
    # Get filter parameters
    date_filter = request.GET.get('date_filter', 'day')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Initialize date range based on filter
    today = datetime.now().date()
    
    if date_filter == 'day':
        start_date = today
        end_date = today
    elif date_filter == 'week':
        start_date = today - timedelta(days=7)
        end_date = today
    elif date_filter == 'month':
        start_date = today - timedelta(days=30)
        end_date = today
    elif date_filter == 'custom' and start_date and end_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        start_date = today - timedelta(days=30)
        end_date = today

    # Query orders
    orders = Order.objects.filter(
        order_date__range=[start_date, end_date],
        status='Delivered'  
    ).select_related('user').prefetch_related(
        'order_items', 
        'order_items__product_variant'
    )

    # Calculate summary statistics
    summary = {
        'total_orders': orders.count(),
        'total_amount': orders.aggregate(Sum('total'))['total__sum'] or Decimal('0.00'),
        'total_items': orders.aggregate(Sum('order_items__quantity'))['order_items__quantity__sum'] or 0
    }

    # Calculate discounts for each order
    orders_with_discounts = []
    total_discount = Decimal('0.00')
    
    for order in orders:
        order_discount = Decimal('0.00')
        try:
            original_total = sum(
                Decimal(str(item.product_variant.price)) * item.quantity 
                for item in order.order_items.all()
            )
            order_discount = original_total - Decimal(str(order.total))
            total_discount += order_discount
            
            # Store the calculated discount with the order
            order.calculated_discount = order_discount
            orders_with_discounts.append(order)
        except Exception as e:
            print(f"Error calculating discount for order {order.id}: {str(e)}")
            order.calculated_discount = Decimal('0.00')
            orders_with_discounts.append(order)

    # Sales data
    sales_data = orders.annotate(
        period=TruncDate('order_date')
    ).values('period').annotate(
        total_sales=Sum('total'),
        order_count=Count('id')
    ).order_by('period')

    # Top Products
    top_products = OrderItem.objects.filter(
        order__status='Delivered',
        order__order_date__range=[start_date, end_date]
    ).values(
        'product_variant__product__name'
    ).annotate(
        total_sold=Sum('quantity')
    ).order_by('-total_sold')[:10]

    # Top Categories
    top_categories = OrderItem.objects.filter(
        order__status='Delivered',
        order__order_date__range=[start_date, end_date]
    ).values(
        'product_variant__product__category__name'
    ).annotate(
        total_sold=Sum('quantity')
    ).order_by('-total_sold')[:5]

    sales_data = list(sales_data.values('period', 'total_sales', 'order_count'))
    products_data = list(top_products)
    categories_data = list(top_categories)

    context = {
        'orders': orders_with_discounts,
        'summary': summary,
        'total_discount': total_discount,
        'start_date': start_date,
        'end_date': end_date,
        'date_filter': date_filter,
        'sales_data_json': json.dumps(sales_data, cls=DjangoJSONEncoder),
        'products_data_json': json.dumps(products_data, cls=DjangoJSONEncoder),
        'categories_data_json': json.dumps(categories_data, cls=DjangoJSONEncoder),
    }

    # Handle export requests
    export_format = request.GET.get('export')
    if export_format:
        if export_format == 'pdf':
            return export_pdf(orders, summary, start_date, end_date)
        elif export_format == 'excel':
            return export_excel(orders, summary, start_date, end_date)

    return render(request, 'admin/dashboard.html', context)
from io import BytesIO
import xlsxwriter
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def export_excel(orders, summary, start_date, end_date):
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet("Sales Report")

    # Define styles
    header_format = workbook.add_format({'bold': True, 'bg_color': '#4F81BD', 'color': 'white', 'align': 'center'})
    currency_format = workbook.add_format({'num_format': '₹#,##0.00'})
    
    # Add LUELEE brand title
    worksheet.merge_range('A1:F1', 'LUELEE - Sales Report', workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'}))
    
    # Add report period
    worksheet.merge_range('A2:F2', f'Period: {start_date} to {end_date}', workbook.add_format({'align': 'center'}))

    # Headers
    headers = ['Order ID', 'Date', 'Customer', 'Items', 'Total Amount', 'Discount']
    for col, header in enumerate(headers):
        worksheet.write(3, col, header, header_format)  # Header row at index 3 (row 4 in Excel)

    # Add order data
    for row, order in enumerate(orders, start=4):
        worksheet.write(row, 0, order.order_no)
        worksheet.write(row, 1, order.order_date.strftime('%Y-%m-%d'))
        worksheet.write(row, 2, order.user.email)
        worksheet.write(row, 3, order.order_items.count())
        worksheet.write(row, 4, order.total, currency_format)
        worksheet.write(row, 5, order.calculated_discount, currency_format)

    # Add summary section
    summary_row = len(orders) + 6
    worksheet.write(summary_row, 0, 'Summary', workbook.add_format({'bold': True}))
    worksheet.write(summary_row + 1, 0, 'Total Orders')
    worksheet.write(summary_row + 1, 1, summary['total_orders'])
    worksheet.write(summary_row + 2, 0, 'Total Amount')
    worksheet.write(summary_row + 2, 1, summary['total_amount'], currency_format)

    workbook.close()
    output.seek(0)

    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=LUELEE_Sales_Report_{start_date}_{end_date}.xlsx'
    return response


def export_pdf(orders, summary, start_date, end_date):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=LUELEE_Sales_Report_{start_date}_{end_date}.pdf'

    # Create PDF
    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(letter),
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50
    )

    elements = []
    styles = getSampleStyleSheet()
    
    # Add LUELEE Branding Title
    title_style = ParagraphStyle('TitleStyle', fontSize=16, alignment=1, spaceAfter=20, textColor=colors.darkblue)
    elements.append(Paragraph('LUELEE - Sales Report', title_style))
    
    # Add report period
    subtitle_style = ParagraphStyle('SubtitleStyle', fontSize=12, alignment=1, spaceAfter=10)
    elements.append(Paragraph(f'Period: {start_date} to {end_date}', subtitle_style))
    elements.append(Spacer(1, 20))

    # Add summary section
    summary_style = ParagraphStyle('SummaryStyle', fontSize=12, spaceAfter=10)
    elements.append(Paragraph(f'<b>Total Orders:</b> {summary["total_orders"]}', summary_style))
    elements.append(Paragraph(f'<b>Total Amount:</b> ₹{summary["total_amount"]}', summary_style))
    elements.append(Paragraph(f'<b>Total Items:</b> {summary["total_items"]}', summary_style))
    elements.append(Spacer(1, 20))

    # Prepare data for orders table
    data = [['Order No', 'Date', 'Customer', 'Items', 'Total Amount', 'Discount']]
    for order in orders:
        data.append([
            order.order_no,
            order.order_date.strftime('%Y-%m-%d'),
            order.user.email,
            order.order_items.count(),
            f'₹{order.total}',
            f'₹{order.calculated_discount}'
        ])

    # Create the table with improved formatting
    table = Table(data, colWidths=[80, 100, 200, 60, 100, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))

    elements.append(table)

    # Build PDF
    doc.build(elements)
    return response


@staff_member_required
def manage_item_returns(request):
    # Get all returns ordered by creation date
    pending_returns = OrderItemReturn.objects.filter(
        approved=False,
        order_item__status='RETURN_PENDING'
    ).select_related(
        'order_item',
        'order_item__order',
        'order_item__product_variant',
        'order_item__product_variant__product'
    ).order_by('-created_at')

    approved_returns = OrderItemReturn.objects.filter(
        approved=True,
        order_item__status='Returned'
    ).select_related(
        'order_item',
        'order_item__order',
        'order_item__product_variant',
        'order_item__product_variant__product'
    ).order_by('-created_at')

    # Paginate the results
    pending_paginator = Paginator(pending_returns, 5)
    pending_page_number = request.GET.get('pending_page')
    pending_page_obj = pending_paginator.get_page(pending_page_number)

    approved_paginator = Paginator(approved_returns, 5)
    approved_page_number = request.GET.get('approved_page')
    approved_page_obj = approved_paginator.get_page(approved_page_number)

    context = {
        'pending_returns': pending_page_obj,
        'approved_returns': approved_page_obj,
    }

    return render(request, 'admin/manage_returns.html', context)

@staff_member_required
def approve_return_item(request, return_id):
    try:
        # Get the return request with related objects
        return_request = get_object_or_404(
            OrderItemReturn.objects.select_related(
                'order_item',
                'order_item__order',
                'order_item__product_variant'
            ),
            id=return_id
        )

        order_item = return_request.order_item
        order = order_item.order

        if return_request.approved:
            messages.error(request, "This return has already been approved.")
            return redirect('manage_returns')

        # Calculate refund amount with proper discount consideration
        item_total = Decimal(str(order_item.total_amount))
        
        # Get order total and all items total to calculate discount ratio
        order_items_total = Decimal(str(order.order_items.aggregate(Sum('total_amount'))['total_amount__sum']))
        order_total = order.total

        # Calculate discount ratio
        if order_items_total > 0:
            discount_ratio = order_total / order_items_total
            refund_amount = item_total * discount_ratio
        else:
            refund_amount = item_total

        # Process the refund to wallet
        try:
            wallet = Wallet.objects.get(user=order.user)
            wallet.credit(
                refund_amount,
                description=f"Refund for Order #{order.order_no} - Item: {order_item.product_variant.product.name}"
            )
        except Wallet.DoesNotExist:
            # Create wallet if it doesn't exist
            wallet = Wallet.objects.create(user=order.user)
            wallet.credit(
                refund_amount,
                description=f"Refund for Order #{order.order_no} - Item: {order_item.product_variant.product.name}"
            )

        # Update product variant stock
        product_variant = order_item.product_variant
        product_variant.stock_quantity += order_item.quantity
        product_variant.save()

        # Update return request and order item status
        return_request.approved = True
        return_request.save()

        order_item.status = 'Returned'
        order_item.save()

        # Check if all items in order are returned
        if all(item.status == 'Returned' for item in order.order_items.all()):
            order.status = 'Returned'
            order.save()

        messages.success(
            request,
            f"Return approved for {order_item.product_variant.product.name}. ₹{refund_amount} refunded to customer's wallet."
        )

    except Exception as e:
        messages.error(request, f"Error processing return: {str(e)}")

    return redirect('manage_returns')





@login_required
def banner_management(request):
    if not request.user.is_staff:
        return redirect('admin_login')
        
    banners = Banner.objects.all().order_by('position')
    available_positions = set([1, 2, 3]) - set(banners.values_list('position', flat=True))
    
    if request.method == 'POST':
        try:
            image = request.FILES.get('image')
            title = request.POST.get('title')
            link=request.POST.get('link')
            position = request.POST.get('position')
            
            if Banner.objects.filter(position=position).exists():
                messages.error(request, 'This banner position is already taken')
                return redirect('banner_management')
            
            if image:
                # Upload to cloudinary and get the URL
                upload_result = cloudinary.uploader.upload(image)
                image_url = upload_result['secure_url']
                
                Banner.objects.create(
                    title=title,
                    link=link,
                    image_url=image_url,
                    position=position
                )
                messages.success(request, 'Banner added successfully')
            else:
                messages.error(request, 'Please select an image')
                
        except Exception as e:
            messages.error(request, f'Error adding banner: {str(e)}')
        
        return redirect('banner_management')
    
    context = {
        'banners': banners,
        'available_positions': available_positions,
    }
    
    return render(request, 'admin/banner_management.html', context)
@login_required
def delete_banner(request, banner_id):
    if not request.user.is_staff:
        return redirect('admin_login')
        
    try:
        banner = Banner.objects.get(id=banner_id)
        banner.delete()
        messages.success(request, 'Banner deleted successfully')
    except Banner.DoesNotExist:
        messages.error(request, 'Banner not found')
    
    return redirect('banner_management')

@login_required
def toggle_banner(request, banner_id):
    if not request.user.is_staff:
        return redirect('admin_login')
        
    try:
        banner = Banner.objects.get(id=banner_id)
        banner.is_active = not banner.is_active
        banner.save()
        status = 'activated' if banner.is_active else 'deactivated'
        messages.success(request, f'Banner {status} successfully')
    except Banner.DoesNotExist:
        messages.error(request, 'Banner not found')
    
    return redirect('banner_management')