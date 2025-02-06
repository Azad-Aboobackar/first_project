from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.cache import cache
from django.contrib.auth import login, authenticate, logout
from django.core.mail import send_mail
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth.decorators import login_required
import random
from django.contrib.auth import get_user_model
from .models import Category,Product,ProductImage,ProductVariant,Order, OrderItem,Address, Wishlist,Wallet, Transaction ,Offer,Coupon,OrderItemReturn,Banner
from cloudinary.uploader import upload
from decimal import Decimal 
from django.db.models import Prefetch
from django.views.decorators.cache import never_cache
from django.urls import reverse 
from django.contrib.auth.hashers import check_password
from django.contrib.auth import update_session_auth_hash
from .models import CartItem
from django.utils.crypto import get_random_string
from django.shortcuts import render
from django.http import JsonResponse,HttpResponseRedirect
from django.db.models import Q,Min
from django.views.decorators.csrf import csrf_exempt
import razorpay
from django.db import transaction
from django.db.models import F
from datetime import date





CustomUser = get_user_model()

def send_otp_email(email, otp):
    try:
        print(f"Sending OTP to {email}: {otp}")
        send_mail(
            'Your OTP Code',
            f'Your OTP code is {otp}. Please use it to complete your signup.',
            'no-reply@yourdomain.com',
            [email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"Error sending OTP email: {e}")
        return False
    return True

@never_cache
def usersignup(request):
    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('firstName')
        last_name = request.POST.get('lastName', '')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirmPassword')
        phone_no = request.POST.get('phone')  

        if not first_name or len(first_name.strip()) < 2:
            messages.error(request, "First name must be at least 2 characters long.")
            return redirect('usersignup')

        if CustomUser.objects.filter(first_name__iexact=first_name).exists():
            messages.error(request, "A user with this first name already exists.")
            return redirect('usersignup')

        if last_name and len(last_name.strip()) < 2:
            messages.error(request, "Last name must be at least 2 characters long.")
            return redirect('usersignup')

        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Invalid email format.")
            return redirect('usersignup')

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered.")
            return redirect('usersignup')

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return redirect('usersignup')
        if not any(char.isdigit() for char in password):
            messages.error(request, "Password must contain at least one number.")
            return redirect('usersignup')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('usersignup')

        if not phone_no.isdigit() or len(phone_no) != 10:
            messages.error(request, "Phone number must be 10 digits.")
            return redirect('usersignup')

        if CustomUser.objects.filter(phone_no=phone_no).exists():
            messages.error(request, "Phone number is already registered.")
            return redirect('usersignup')

        otp = random.randint(100000, 999999)
        cache.set(f"otp_{email}", otp, timeout=300)
        print(otp)  

        if send_otp_email(email, otp):
            temp_user = {
                'email': email,
                'password': password,
                'first_name': first_name,
                'last_name': last_name,
                'phone_no': phone_no,  
            }
            cache.set(f"temp_user_{email}", temp_user, timeout=300)
            request.session['email'] = email
            messages.info(request, "OTP sent to your email.")
            return redirect('signup_otp')
        else:
            messages.error(request, "Error sending OTP. Please try again.")
            return redirect('usersignup')

    return render(request, 'usersignup.html')


@never_cache
def signup_otp(request):
    email = request.session.get('email') or request.GET.get('email')
    if not email:
        messages.error(request, "Session expired or email missing.")
        return redirect('usersignup')

    if request.method == 'POST':
        if 'resend_otp' in request.POST:
            otp = random.randint(100000, 999999)
            print(f"Generated OTP: {otp}") 
            cache.set(f"otp_{email}", otp, timeout=300)  
            if send_otp_email(email, otp):
                messages.info(request, "A new OTP has been sent to your email.")
            else:
                messages.error(request, "Error sending OTP. Please try again.")
            return redirect(f'{reverse("signup_otp")}?email={email}')
        
        elif 'otp' in request.POST:
            entered_otp = request.POST.get('otp')
            stored_otp = cache.get(f"otp_{email}")

            if stored_otp:
                if str(stored_otp) == entered_otp:
                    temp_user = cache.get(f"temp_user_{email}")
                    if not temp_user:
                        messages.error(request, "Session expired. Please sign up again.")
                        return redirect('usersignup')

                    user = CustomUser.objects.create_user(
                        email=email,
                        password=temp_user['password'],
                        first_name=temp_user['first_name'],
                        last_name=temp_user['last_name'],
                        phone_no=temp_user['phone_no'],  
                    )
                    user.save()

                    user.backend = 'django.contrib.auth.backends.ModelBackend'
                    login(request, user)

                    cache.delete(f"otp_{email}")
                    cache.delete(f"temp_user_{email}")

                    messages.success(request, "Signup successful! Welcome.")
                    return redirect('home')
                else:
                    messages.error(request, "Incorrect OTP. Please try again.")
            else:
                messages.error(request, "OTP has expired. Please request a new one.")

            return render(request, 'signup_otp.html', {'email': email})  
    return render(request, 'signup_otp.html', {'email': email})







CustomUser = get_user_model()

def send_password_reset_otp(email, otp):
    try:
        send_mail(
            'Password Reset OTP',
            f'Your OTP code for password reset is {otp}. Please use it to reset your password.',
            'no-reply@yourdomain.com',
            [email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"Error sending OTP email: {e}")
        return False
    return True

@never_cache
def password_reset_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        user = CustomUser.objects.filter(email=email).first()

        if user:
            otp = random.randint(100000, 999999)
            cache.set(f"password_reset_otp_{email}", otp, timeout=300)
            print(otp)  

            if send_password_reset_otp(email, otp):
                request.session['email'] = email
                messages.info(request, "OTP sent to your email for password reset.")
                return redirect('password_reset_otp')
            else:
                messages.error(request, "Error sending OTP. Please try again.")
        else:
            messages.error(request, "Email not found.")

        return render(request, 'password_reset_request.html')

    return render(request, 'password_reset_request.html')


@never_cache
def password_reset_otp(request):
    email = request.session.get('email')
    
    if not email:
        messages.error(request, "Session expired or email missing.")
        return redirect('password_reset_request')

    if request.method == 'POST':
        if 'resend_otp' in request.POST:
            otp = random.randint(100000, 999999)
            print(otp) 
            cache.set(f"password_reset_otp_{email}", otp, timeout=300)
            if send_password_reset_otp(email, otp):
                messages.info(request, "A new OTP has been sent to your email.")
            else:
                messages.error(request, "Error sending OTP. Please try again.")
            return redirect('password_reset_otp')

        elif 'otp' in request.POST:
            entered_otp = request.POST.get('otp')
            stored_otp = cache.get(f"password_reset_otp_{email}")

            if stored_otp and str(stored_otp) == entered_otp:
                return redirect(reverse('password_reset', kwargs={'email': email}))
            else:
                messages.error(request, "Invalid or expired OTP.")

        return render(request, 'password_reset_otp.html', {'email': email})

    return render(request, 'password_reset_otp.html', {'email': email})



@never_cache
def password_reset(request, email):
    try:
        if request.method == 'POST':
            new_password = request.POST.get('password')
            confirm_password = request.POST.get('confirmPassword')



            if not email or email.strip() == "":
                messages.error(request, "Invalid email address.")
                return redirect(f'/password-reset/{email}/')
            


            if not new_password or " " in new_password:
                messages.error(request, "Password cannot contain spaces.")
                return redirect(f'/password-reset/{email}/')
            if not new_password.isdigit():
                messages.error(request, "Password can only contain numbers.")
                return redirect(f'password-reset/{email}/')
            if len(new_password) < 8:
                messages.error(request, "Password must be at least 8 characters long.")
                return redirect(f'/password-reset/{email}/')

            if new_password != confirm_password:
                messages.error(request, "Passwords do not match.")
                return redirect(f'/password-reset/{email}/')

            user = CustomUser.objects.filter(email=email).first()
            if user:
                user.set_password(new_password)
                user.save()

                cache.delete(f"password_reset_otp_{email}")
                cache.delete(f"temp_user_reset_{email}")

                messages.success(request, "Your password has been successfully reset.")
                return redirect('userlogin')
            else:
                messages.error(request, "User not found.")
                return redirect('password_reset_request')

        return render(request, 'password_reset_form.html', {'email': email})
    except Exception as e:
        print(f"Error in password_reset: {str(e)}")
        messages.error(request, "An unexpected error occurred. Please try again.")
        return redirect('password_reset_request')


@never_cache
def userlogin(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        
        try:
            user = CustomUser.objects.get(email=email)
            
            if not user.is_active:
                messages.error(request, "Your account is blocked. Please contact support.")
                return render(request, 'userlogin.html')

        except CustomUser.DoesNotExist:
            user = None

        if user is not None:
            user = authenticate(request, email=email, password=password)
            
            if user is not None:
                login(request, user)
                return redirect('home')
            else:
                messages.error(request, "Invalid email or password.")
        else:
            messages.error(request, "Invalid email or password.")
    
    return render(request, 'userlogin.html')

def userlogout(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('userlogin')


@login_required(login_url='userlogin')
def user_profile(request):
    if not request.user.is_authenticated:
        return redirect('userlogin')
    return render(request, 'user_profile.html')



def reset_password(request):
    return render(request, 'reset_password.html')



def home_page(request):
    banners = Banner.objects.filter(is_active=True).order_by('position')
    
    if request.user.is_authenticated:
        cart_count = CartItem.objects.filter(user=request.user).count()
        wishlist_count = Wishlist.objects.filter(user=request.user).count()
    else:
        cart_count = 0
        wishlist_count = 0

    context = {
        'cart_count': cart_count,
        'wishlist_count': wishlist_count,
        'banners': banners,
    }
    return render(request, 'home.html', context)





def shop_view(request):
    # Calculate counts for authenticated users
    cart_count = 0
    wishlist_count = 0
    if request.user.is_authenticated:
        cart_count = CartItem.objects.filter(user=request.user).count()
        wishlist_count = Wishlist.objects.filter(user=request.user).count()

    # Return HTML template for non-AJAX requests
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Get all active categories for the filter
        categories = Category.objects.filter(is_active=True)
        return render(request, 'shop.html', {
            'cart_count': cart_count,
            'wishlist_count': wishlist_count,
            'categories': categories
        })

    try:
        # Get query parameters
        search_query = request.GET.get('search', '').strip()
        sort_by = request.GET.get('sort', '')
        category_id = request.GET.get('category', '')

        # Base queryset with optimized joins
        products = Product.objects.filter(
            is_active=True, 
            is_deleted=False
        ).select_related(
            'category'
        ).prefetch_related(
            'images',
            'variants'
        ).distinct()

        # Apply category filter if specified
        if category_id:
            products = products.filter(category_id=category_id)

        # Apply search filter if query exists
        if search_query:
            products = products.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )

        # Apply sorting
        if sort_by:
            if sort_by == 'newest':
                products = products.order_by('-created_at')
            elif sort_by == 'price_low_high':
                products = products.annotate(
                    min_price=Min('variants__price')
                ).order_by('min_price')
            elif sort_by == 'price_high_low':
                products = products.annotate(
                    min_price=Min('variants__price')
                ).order_by('-min_price')
            elif sort_by == 'name_asc':
                products = products.order_by('name')
            elif sort_by == 'name_desc':
                products = products.order_by('-name')

        # Prepare products data
        response_data = []
        for product in products:
            try:
                # Get primary image
                primary_image = ProductImage.objects.filter(
                    product=product,
                    is_primary=True
                ).first()

                # Get first variant's price
                first_variant = product.variants.first()
                variant_data = None

                if first_variant:
                    try:
                        category_discount = Decimal('0')
                        product_discount = Decimal('0')

                        category_offer = Offer.objects.filter(
                            offer_type='category',
                            category=product.category,
                            end_date__gte=date.today(),
                            is_listed=True
                        ).order_by('-discount').first()
                        
                        product_offer = Offer.objects.filter(
                            offer_type='product',
                            product=product,
                            end_date__gte=date.today(),
                            is_listed=True
                        ).order_by('-discount').first()

                        if category_offer:
                            category_discount = category_offer.discount
                        if product_offer:
                            product_discount = product_offer.discount

                        highest_discount = max(category_discount, product_discount)
                        discounted_price = first_variant.price * (1 - (highest_discount / Decimal('100')))

                        variant_data = {
                            'id': first_variant.id,
                            'price': float(first_variant.price if first_variant.price else 0),
                            'discounted_price': float(discounted_price) if highest_discount > 0 else None,
                            'discount_percentage': float(highest_discount) if highest_discount > 0 else None,
                            'name': first_variant.name,
                            'size': first_variant.size,
                            'color': first_variant.color
                        }
                    except (ValueError, TypeError, AttributeError) as e:
                        print(f"Error processing variant price for product {product.id}: {e}")
                        variant_data = None

                # Check wishlist status
                in_wishlist = False
                if request.user.is_authenticated and first_variant:
                    in_wishlist = Wishlist.objects.filter(
                        user=request.user,
                        product_variant=first_variant
                    ).exists()

                product_data = {
                    'product': {
                        'id': product.id,
                        'name': product.name,
                        'description': product.description,
                        'category': product.category.name
                    },
                    'primary_image': {
                        'image_url': primary_image.image_url if primary_image else "https://via.placeholder.com/150"
                    },
                    'variants': [variant_data] if variant_data else [],
                    'in_wishlist': in_wishlist
                }

                response_data.append(product_data)
            except Exception as e:
                print(f"Error processing product {product.id}: {e}")
                continue

        return JsonResponse(response_data, safe=False)

    except Exception as e:
        print(f"Error in shop view: {e}")
        return JsonResponse({
            'error': 'An error occurred while loading products.',
            'details': str(e)
        }, status=500)




def men_page(request):
    # Check if it's an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # Get search and sort parameters
    search_query = request.GET.get('search', '')
    sort_param = request.GET.get('sort', '')
    
    try:
        # Get the category for men's products
        men_category = Category.objects.get(name__iexact='men')
        
        # Base queryset for men's products
        products = Product.objects.filter(
            category=men_category,
            is_active=True
        ).prefetch_related(
            'variants',
            'images',
        ).distinct()
        
        # Apply search filter if provided
        if search_query:
            products = products.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # Apply sorting
        if sort_param:
            if sort_param == 'newest':
                products = products.order_by('-created_at')
            elif sort_param == 'price_low_high':
                products = products.order_by('variants__price').distinct()
            elif sort_param == 'price_high_low':
                products = products.order_by('-variants__price').distinct()
            elif sort_param == 'name_asc':
                products = products.order_by('name')
            elif sort_param == 'name_desc':
                products = products.order_by('-name')
        
        # Prepare data for each product
        products_data = []
        processed_products = set()  # To prevent duplicate products
        
        for product in products:
            # Skip if we've already processed this product
            if product.id in processed_products:
                continue
                
            processed_products.add(product.id)
            
            # Get variants for the product
            variants = product.variants.all()
            
            # Get primary image
            primary_image = product.images.filter(is_primary=True).first()
            
            # Check if product is in user's wishlist
            in_wishlist = False
            if request.user.is_authenticated:
                in_wishlist = Wishlist.objects.filter(
                    user=request.user,
                    product_variant__in=variants
                ).exists()
            
            # Prepare variant data
            variant_data = []
            for variant in variants:
                discount_percentage = None
                discounted_price = None
                
                if hasattr(variant, 'get_discounted_price'):
                    try:
                        discounted_price = variant.get_discounted_price()
                        # Only include discount if it actually provides a lower price
                        if discounted_price and discounted_price < variant.price:
                            discount_percentage = round(((variant.price - discounted_price) / variant.price) * 100)
                        else:
                            discounted_price = None  # Reset to None if no actual discount
                            discount_percentage = None
                    except:
                        discounted_price = None
                        discount_percentage = None
                
                variant_data.append({
                    'id': variant.id,
                    'size': variant.size,
                    'price': float(variant.price),
                    'discounted_price': float(discounted_price) if discounted_price else None,
                    'discount_percentage': discount_percentage,
                    'stock': variant.stock_quantity
                })
                        
            # Only add product if it has variants
            if variant_data:
                product_data = {
                    'product': {
                        'id': product.id,
                        'name': product.name,
                        'category': men_category.id,
                    },
                    'variants': variant_data,
                    'primary_image': {
                        'image_url': primary_image.image_url if primary_image else None
                    },
                    'in_wishlist': in_wishlist
                }
                products_data.append(product_data)
        
        # Return JSON response for AJAX requests
        if is_ajax:
            return JsonResponse(products_data, safe=False)
        
        # For regular requests, get cart and wishlist counts
        context = {
            'products_with_images': products_data,
            'search_query': search_query,
        }
        
        if request.user.is_authenticated:
            context.update({
                'wishlist_count': Wishlist.objects.filter(user=request.user).count(),
                'cart_count': CartItem.objects.filter(user=request.user).count(),
            })
        
        return render(request, 'men.html', context)
        
    except Category.DoesNotExist:
        if is_ajax:
            return JsonResponse([], safe=False)
        return render(request, 'men.html', {'products_with_images': []})





def women_page(request):
    # Check if it's an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # Get search and sort parameters
    search_query = request.GET.get('search', '')
    sort_param = request.GET.get('sort', '')
    
    try:
        # Get the category ID for women's products
        women_category = Category.objects.get(name__iexact='women')
        
        # Base queryset for women's products
        products = Product.objects.filter(
            category=women_category,
            is_active=True
        ).prefetch_related(
            'variants',
            'images',
        ).distinct()
        
        # Apply search filter if provided
        if search_query:
            products = products.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # Apply sorting
        if sort_param:
            if sort_param == 'newest':
                products = products.order_by('-created_at')
            elif sort_param == 'price_low_high':
                products = products.order_by('variants__price').distinct()
            elif sort_param == 'price_high_low':
                products = products.order_by('-variants__price').distinct()
            elif sort_param == 'name_asc':
                products = products.order_by('name')
            elif sort_param == 'name_desc':
                products = products.order_by('-name')
        
        # Prepare data for each product
        products_data = []
        processed_products = set()  # To prevent duplicate products
        
        for product in products:
            # Skip if we've already processed this product
            if product.id in processed_products:
                continue
                
            processed_products.add(product.id)
            
            # Get variants for the product
            variants = product.variants.all()
            
            # Get primary image
            primary_image = product.images.filter(is_primary=True).first()
            
            # Check if product is in user's wishlist
            in_wishlist = False
            if request.user.is_authenticated:
                in_wishlist = Wishlist.objects.filter(
                    user=request.user,
                    product_variant__in=variants
                ).exists()
            
            # Prepare variant data
# Prepare variant data
            variant_data = []
            for variant in variants:
                discount_percentage = None
                discounted_price = None
                
                if hasattr(variant, 'get_discounted_price'):
                    try:
                        discounted_price = variant.get_discounted_price()
                        # Only include discount if there's an active offer and it provides a lower price
                        if discounted_price and discounted_price < variant.price:
                            discount_percentage = round(((variant.price - discounted_price) / variant.price) * 100)
                        else:
                            discounted_price = None
                            discount_percentage = None
                    except Exception as e:
                        print(f"Error calculating discount for variant {variant.id}: {str(e)}")
                        discounted_price = None
                        discount_percentage = None
                
                variant_data.append({
                    'id': variant.id,
                    'size': variant.size,
                    'price': float(variant.price),
                    'discounted_price': float(discounted_price) if discounted_price else None,
                    'discount_percentage': discount_percentage,
                    'stock': variant.stock_quantity
                })
            
            # Only add product if it has variants
            if variant_data:
                product_data = {
                    'product': {
                        'id': product.id,
                        'name': product.name,
                        'category': women_category.id,
                    },
                    'variants': variant_data,
                    'primary_image': {
                        'image_url': primary_image.image_url if primary_image else None
                    },
                    'in_wishlist': in_wishlist
                }
                products_data.append(product_data)
        
        # Return JSON response for AJAX requests
        if is_ajax:
            return JsonResponse(products_data, safe=False)
        
        # For regular requests, get cart and wishlist counts
        context = {
            'products_with_images': products_data,
            'search_query': search_query,
        }
        
        if request.user.is_authenticated:
            context.update({
                'wishlist_count': Wishlist.objects.filter(user=request.user).count(),
                'cart_count': CartItem.objects.filter(user=request.user).count(),
            })
        
        return render(request, 'women.html', context)
        
    except Category.DoesNotExist:
        if is_ajax:
            return JsonResponse([], safe=False)
        return render(request, 'women.html', {'products_with_images': []})


def kid_page(request):
    # Check if it's an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # Get search and sort parameters
    search_query = request.GET.get('search', '')
    sort_param = request.GET.get('sort', '')
    
    try:
        # Get the category ID for kid's products
        kid_category = Category.objects.get(name__iexact='kid')
        
        # Get today's date for offer validation
        today = date.today()
        
        # Base queryset for kid's products
        products = Product.objects.filter(
            category=kid_category,
            is_active=True
        ).prefetch_related(
            'variants',
            'images',
        ).distinct()
        
        # Apply search filter if provided
        if search_query:
            products = products.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # Apply sorting
        if sort_param:
            if sort_param == 'newest':
                products = products.order_by('-created_at')
            elif sort_param == 'price_low_high':
                products = products.order_by('variants__price').distinct()
            elif sort_param == 'price_high_low':
                products = products.order_by('-variants__price').distinct()
            elif sort_param == 'name_asc':
                products = products.order_by('name')
            elif sort_param == 'name_desc':
                products = products.order_by('-name')
        
        # Prepare data for each product
        products_data = []
        processed_products = set()  # To prevent duplicate products
        
        for product in products:
            if product.id in processed_products:
                continue
                
            processed_products.add(product.id)
            
            # Get variants for the product
            variants = product.variants.all()
            
            # Get primary image
            primary_image = product.images.filter(is_primary=True).first()
            
            # Check for active offers for this product
            active_product_offer = Offer.objects.filter(
                Q(offer_type='product', product=product) | 
                Q(offer_type='category', category=kid_category),
                end_date__gte=today,
                is_listed=True
            ).exists()
            
            # Check if product is in user's wishlist
            in_wishlist = False
            if request.user.is_authenticated:
                in_wishlist = Wishlist.objects.filter(
                    user=request.user,
                    product_variant__in=variants
                ).exists()
            
            # Prepare variant data
            variant_data = []
            for variant in variants:
                discount_percentage = None
                discounted_price = None
                
                if hasattr(variant, 'get_discounted_price') and active_product_offer:
                    try:
                        discounted_price = variant.get_discounted_price()
                        if discounted_price and discounted_price < variant.price:
                            discount_percentage = round(((variant.price - discounted_price) / variant.price) * 100)
                        else:
                            discounted_price = None
                            discount_percentage = None
                    except Exception as e:
                        print(f"Error calculating discount for variant {variant.id}: {str(e)}")
                        discounted_price = None
                        discount_percentage = None
                
                variant_data.append({
                    'id': variant.id,
                    'size': variant.size,
                    'price': float(variant.price),
                    'discounted_price': float(discounted_price) if discounted_price else None,
                    'discount_percentage': discount_percentage,
                    'stock': variant.stock_quantity
                })
            
            # Only add product if it has variants
            if variant_data:
                product_data = {
                    'product': {
                        'id': product.id,
                        'name': product.name,
                        'category': kid_category.id,
                    },
                    'variants': variant_data,
                    'primary_image': {
                        'image_url': primary_image.image_url if primary_image else None
                    },
                    'in_wishlist': in_wishlist
                }
                products_data.append(product_data)
        
        # Return JSON response for AJAX requests
        if is_ajax:
            return JsonResponse(products_data, safe=False)
        
        # For regular requests, get cart and wishlist counts
        context = {
            'products_with_images': products_data,
            'search_query': search_query,
        }
        
        if request.user.is_authenticated:
            context.update({
                'wishlist_count': Wishlist.objects.filter(user=request.user).count(),
                'cart_count': CartItem.objects.filter(user=request.user).count(),
            })
        
        return render(request, 'kid.html', context)
        
    except Category.DoesNotExist:
        if is_ajax:
            return JsonResponse([], safe=False)
        return render(request, 'kid.html', {'products_with_images': []})




def buying_page(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.user.is_authenticated:
        cart_count = CartItem.objects.filter(user=request.user).count()
        wishlist_count = Wishlist.objects.filter(user=request.user).count()
    else:
        cart_count = 0
        wishlist_count = 0
    related_products = Product.objects.filter(
        category=product.category
    ).exclude(
        id=product.id
    ).prefetch_related(
        'images',
        'variants'
    )[:4] 
    # Get active offers for this product and its category
    category_offer = Offer.objects.filter(
        offer_type='category',
        category=product.category,
        end_date__gte=date.today(),
        is_listed=True
    ).order_by('-discount').first()

    product_offer = Offer.objects.filter(
        offer_type='product',
        product=product,
        end_date__gte=date.today(),
        is_listed=True
    ).order_by('-discount').first()

    # Calculate highest applicable discount
    category_discount = category_offer.discount if category_offer else Decimal('0')
    product_discount = product_offer.discount if product_offer else Decimal('0')
    highest_discount = max(category_discount, product_discount)

    # Add discount info to variant data
    variants_with_discounts = []
    for variant in product.variants.all():
        discounted_price = variant.price * (1 - (highest_discount / Decimal('100')))
        variants_with_discounts.append({
            'id': variant.id,
            'color': variant.color,
            'size': variant.size,
            'price': float(variant.price),
            'stock': variant.stock_quantity,
            'has_discount': highest_discount > 0,
            'discounted_price': float(discounted_price) if highest_discount > 0 else None,
            'discount_percentage': float(highest_discount) if highest_discount > 0 else None,
            'images': [img.image_url for img in variant.images.all()]
        })

    context = {
        "product": product,
        "variants_with_discounts": variants_with_discounts,
        "has_offer": highest_discount > 0,
        "discount_percentage": float(highest_discount),
        "cart_count": cart_count ,
        "wishlist_count":wishlist_count,
        'related_products': related_products,
    }
    return render(request, "buying.html", context)



@login_required
def manage_address(request):
    user = request.user
    addresses = Address.objects.filter(user=user) 
    cart_count = CartItem.objects.filter(user=request.user).count()
    wishlist_count = Wishlist.objects.filter(user=request.user).count()


    if request.method == 'POST':
        action = request.POST.get('action')
        address_id = request.POST.get('address_id')

        if action == 'delete':
            if address_id:
                try:
                    address = get_object_or_404(Address, id=address_id, user=user)
                    address.delete()
                    messages.success(request, "Address deleted successfully.")
                except Exception as e:
                    messages.error(request, f"Error: {str(e)}")
            else:
                messages.error(request, "Invalid address ID.")
        else:
            messages.error(request, "Invalid action.")

        return redirect('manage_address')

    return render(request, 'manage_address.html', {'addresses': addresses})



@login_required
def set_primary_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    if request.method == 'POST':
        Address.objects.filter(user=request.user, is_primary=True).update(is_primary=False)
        
        address.is_primary = True
        address.save()
        
        messages.success(request, "Primary address updated successfully.")
        return redirect('manage_address') 

    messages.error(request, "Invalid request.")
    return redirect('manage_address')




@login_required
def add_address(request):
    """
    View to add a new address for the logged-in user.
    """
    if request.method == 'POST':
        # Retrieve form data
        name = request.POST.get('name')
        phone_no = request.POST.get('phone.no')  
        street = request.POST.get('street')
        city = request.POST.get('city')
        state = request.POST.get('state')
        postal_code = request.POST.get('postal_code')
        country = request.POST.get('country')

        errors = []
        if not name:
            errors.append("Name is required.")
        if not name or " " in name:
            errors.append( "Name cannot contain spaces.")
        if not phone_no or not phone_no.isdigit() or int(phone_no) <= 0 or len(phone_no) < 10:
            errors.append("Valid phone number is required (minimum 10 digits and non-negative).")
        if not street:
            errors.append("Street is required.")
        if not city:
            errors.append("City is required.")
        if not state:
            errors.append("State is required.")
        if not postal_code or not postal_code.isdigit():
            errors.append("Valid postal code is required.")
        if not country:
            errors.append("Country is required.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'add_address.html')

        try:
            address = Address.objects.create(
                name=name,
                phone_no=phone_no,
                street_address=street,
                city=city,
                state=state,
                country=country,
                pin_code=postal_code,
                user=request.user
            )

            if not Address.objects.filter(user=request.user, is_primary=True).exists():
                address.is_primary = True
                address.save()

            messages.success(request, "Address added successfully.")
            return redirect('manage_address')  
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return render(request, 'add_address.html')

    return render(request, 'add_address.html')



@login_required
def edit_address(request, address_id):
    """
    View to edit an existing address.
    """
    user = request.user
    address = get_object_or_404(Address, id=address_id, user=user)

    if request.method == 'POST':
        name = request.POST.get('name')
        phone_no = request.POST.get('phone.no')  
        street = request.POST.get('street')
        city = request.POST.get('city')
        state = request.POST.get('state')
        postal_code = request.POST.get('postal_code')
        country = request.POST.get('country')

        errors = []
        if not name or " " in name:
             errors.append( "Name cannot contain spaces.")
        if not name:
            errors.append("Name is required.")
        if not phone_no or not phone_no.isdigit() or int(phone_no) <= 0 or len(phone_no) < 10:
            errors.append("Valid phone number is required (minimum 10 digits and non-negative).")
        if not street:
            errors.append("Street is required.")
        if not city:
            errors.append("City is required.")
        if not state:
            errors.append("State is required.")
        if not postal_code or not postal_code.isdigit():
            errors.append("Valid postal code is required.")
        if not country:
            errors.append("Country is required.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'edit_address.html', {'address': address})

        try:
            address.name = name
            address.phone_no = phone_no
            address.street_address = street
            address.city = city
            address.state = state
            address.pin_code = postal_code
            address.country = country
            address.save()

            messages.success(request, "Address updated successfully.")
            return redirect('manage_address') 
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return render(request, 'edit_address.html', {'address': address})

    return render(request, 'edit_address.html', {'address': address})

@login_required
def edit_profile(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    if request.user != user:
        messages.error(request, "You do not have permission to edit this profile.")
        return redirect('profile')  
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone_no = request.POST.get('phone_no')

        if not first_name or not last_name:
            messages.error(request, "First Name and Last Name are required.")
            return redirect('edit_profile', user_id=user.id)  

        user.first_name = first_name
        user.last_name = last_name
        user.phone_no = phone_no 

        user.save()

        messages.success(request, "Your profile has been updated successfully.")
        return redirect('userprofile') 

    return render(request, 'edit_profile.html', {'user': user})






@login_required
def manage_password(request):
    """
    View for managing and updating user passwords.
    """
    user = request.user  

    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not check_password(current_password, user.password):
            messages.error(request, "The current password you entered is incorrect.")
            return render(request, 'manage_password.html')

        if len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return redirect('manage_password')

        if new_password != confirm_password:
            messages.error(request, "New password and confirmation do not match.")
            return render(request, 'manage_password.html')

        user.set_password(new_password)
        user.save()

        logout(request)

        messages.success(request, "Your password has been updated successfully. Please log in again.")
        return redirect('userlogin') 

    return render(request, 'manage_password.html')





def cart_page(request):
    if request.user.is_authenticated:
        cart_items = CartItem.objects.filter(user=request.user).prefetch_related('product_variant__images').filter(user=request.user)
        subtotal = sum(item.total_amount for item in cart_items)
        total = subtotal  
        return render(request, 'cart.html', {
            'cart_items': cart_items,
            'subtotal': subtotal,
            'total': total,
        })
    return redirect('userlogin')






@csrf_exempt
def add_to_cart(request):
    if request.method == "POST":
        try:
            product_variant_id = request.POST.get("product_variant_id")
            quantity = int(request.POST.get("quantity", 1))
            color = request.POST.get("color", "")

            if not request.user.is_authenticated:
                return JsonResponse({"error": "Login to add the item to cart."}, status=401)

            product_variant = get_object_or_404(ProductVariant, id=product_variant_id)

            if quantity > product_variant.stock_quantity:
                return JsonResponse({"error": "Insufficient stock."}, status=400)

            cart_item, created = CartItem.objects.get_or_create(
                user=request.user,
                product_variant=product_variant,
                defaults={"quantity": 0, "color": color},
            )

            cart_item.quantity += quantity

            if cart_item.quantity > 5:
                return JsonResponse({"error": "Maximum of 5 items per product variant allowed."}, status=400)

            cart_item.save()

            return JsonResponse({
                "message": "Item added to cart successfully.",
                "cart_item_id": cart_item.id,
                "quantity": cart_item.quantity,
                "total_amount": str(cart_item.total_amount),
            })

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method."}, status=405)





def update_cart_item_quantity(request, item_id):
    if request.method == 'POST':
        action = request.POST.get('action') 
        cart_item = get_object_or_404(CartItem, id=item_id, user=request.user)
        product_variant = cart_item.product_variant

        if action == 'increase':
            if cart_item.quantity < 5:  
                cart_item.quantity += 1
                if cart_item.quantity > product_variant.stock_quantity:
                    return JsonResponse({'success': False, 'error': 'Quantity exceeds available stock.'}, status=400)
                message = 'Quantity updated.'
            else:
                message = 'Maximum quantity of 5 reached.'
        elif action == 'decrease' and cart_item.quantity > 1:
            cart_item.quantity -= 1
            message = 'Quantity updated.'
        else:
            message = 'Cannot decrease quantity below 1.'

        cart_item.save()

        total_amount = cart_item.quantity * cart_item.product_variant.price
        cart_total = sum(item.quantity * item.product_variant.price for item in CartItem.objects.filter(user=request.user))

        return JsonResponse({
            'success': True,
            'quantity': cart_item.quantity,
            'total_amount': total_amount,
            'cart_total': cart_total,
            'message': message
        })

    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)




def remove_cart_item(request, item_id):
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, id=item_id, user=request.user)
        cart_item.delete()

        # Recalculate cart total
        cart_total = sum(item.quantity * item.product_variant.price for item in CartItem.objects.filter(user=request.user))

        return JsonResponse({
            'success': True,
            'cart_total': cart_total,
            'message': 'Item removed from cart.'
        })

    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)





@login_required
def checkout(request):
    addresses = Address.objects.filter(user=request.user).order_by('-is_primary')
    coupons = Coupon.objects.filter(is_listed=True)
    cart_items = CartItem.objects.filter(user=request.user).select_related('product_variant')
    
    # Calculate initial total
    total_price = sum(item.total_amount for item in cart_items)
    
    # Handle coupon if exists in session
    coupon_id = request.session.get('coupon_id')
    final_total = total_price
    applied_coupon = None
    discount_amount = Decimal('0')
    
    if coupon_id:
        try:
            coupon = Coupon.objects.get(
                id=coupon_id,
                is_active=True,
                is_listed=True,
                valid_from__lte=timezone.now().date(),
                valid_until__gte=timezone.now().date()
            )
            # Calculate discount
            discount_amount = (total_price * coupon.discount_percentage / 100).quantize(Decimal('0.01'))
            final_total = total_price - discount_amount
            applied_coupon = coupon
            
        except Coupon.DoesNotExist:
            # Clear invalid coupon from session
            if 'coupon_id' in request.session:
                del request.session['coupon_id']
            if 'discount_amount' in request.session:
                del request.session['discount_amount']

    # Prepare cart details
    cart_details = []
    for item in cart_items:
        variant = item.product_variant
        product = variant.product 
        primary_image = ProductImage.objects.filter(variant=variant, is_primary=True).first()
        image_url = primary_image.image_url if primary_image else None

        cart_details.append({
            'item': item,
            'variant': variant,
            'product': product,
            'image_url': image_url,
        })

    context = {
        'razorpay_key': settings.RAZORPAY_KEY_ID,
        'cart_details': cart_details,
        'addresses': addresses,
        'total_price': total_price,
        'final_total': final_total,
        'discount_amount': discount_amount,
        'coupons': coupons,
        'applied_coupon': applied_coupon
    }
    
    return render(request, 'checkout.html', context)





def address_add(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'User is not authenticated.'})

        name = request.POST.get('name')
        phone_no = request.POST.get('phone_no')
        street_address=request.POST.get('street_address')
        city = request.POST.get('city')
        state = request.POST.get('state')
        pin_code = request.POST.get('pin_code')
        country = request.POST.get('country')

        if not name or not city or not pin_code:
            return JsonResponse({'success': False, 'error': 'Required fields are missing.'})

        try:
            address = Address(
                user=request.user,
                name=name,
                phone_no=phone_no,
                street_address=street_address,
                city=city,
                state=state,
                pin_code=pin_code,
                country=country,
                is_primary=True

            )
            address.save()
            return JsonResponse({
                'success': True,
                'message': 'Address saved successfully!',
                'refresh': True  
            })


        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})







@login_required
def create_order(request):
   if request.method == 'POST':
       if request.headers.get('Content-Type') == 'application/json':
           data = json.loads(request.body)
           address_id = data.get('address_id')
           payment_method = data.get('payment_method')
           
           if payment_method == 'razorpay':
               try:
                   address = get_object_or_404(Address, id=address_id)
                   cart_items = CartItem.objects.filter(user=request.user)
                   
                   if not cart_items.exists():
                       return JsonResponse({'status': 'error', 'message': 'Cart is empty'})
                   
                   cart_total = sum(item.total_amount for item in cart_items)
                   final_total = cart_total

                   coupon_id = request.session.get('coupon_id')
                   if coupon_id:
                       try:
                           coupon = Coupon.objects.get(
                               id=coupon_id,
                               is_active=True,
                               valid_from__lte=timezone.now().date(),
                               valid_until__gte=timezone.now().date()
                           )
                           discount = (cart_total * coupon.discount_percentage / 100)
                           final_total = cart_total - discount
                       except Coupon.DoesNotExist:
                           pass

                   order = Order.objects.create(
                       user=request.user,
                       payment='RAZORPAY',
                       shipping_address=address,
                       status='PAYMENT_PENDING',
                       order_no='ORD' + get_random_string(10).upper(),
                       total=final_total,
                       currency='INR'
                   )
                   
                   client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                   razorpay_order = client.order.create({
                       "amount": int(final_total * 100),
                       "currency": "INR",
                       "payment_capture": 1,
                       "receipt": f"order_{order.id}"
                   })
                   
                   order.razorpay_order_id = razorpay_order['id']
                   order.save()
                   
                   for item in cart_items:
                       OrderItem.objects.create(
                           order=order,
                           status='Confirmed',
                           product_variant=item.product_variant,
                           quantity=item.quantity,
                           total_amount=float(item.total_amount)
                       )

                       variant = item.product_variant
                       if variant.stock_quantity >= item.quantity:
                           variant.stock_quantity -= item.quantity
                           variant.save()
                   
                   cart_items.delete()
                   request.session.pop('coupon_id', None)
                   request.session.pop('discount_amount', None)
                   request.session.pop('new_total', None)

                   messages.warning(request, f'Order placed! Payment pending. <a href="/my-orders/" class="alert-link">Complete payment here</a>')

                   return JsonResponse({
                       'status': 'success',
                       'order_id': order.id,  
                       'rzp_order_id': razorpay_order['id'],
                       'amount': razorpay_order['amount'],
                       'currency': 'INR'
                   })
                   
               except Exception as e:
                   if 'order' in locals():
                       order.delete()
                   return JsonResponse({'status': 'error', 'message': str(e)})

       else:
           try:
               address_id = request.POST.get('selected_address')
               payment_method = request.POST.get('payment_method', '').lower()
               
               if payment_method in ['cod', 'wallet']:
                   address = get_object_or_404(Address, id=address_id)
                   cart_items = CartItem.objects.filter(user=request.user)
                   
                   if not cart_items.exists():
                       messages.error(request, 'Your cart is empty')
                       return redirect('cart_page')
                   
                   cart_total = sum(item.total_amount for item in cart_items)
                   final_total = cart_total

                   if payment_method == 'cod' and final_total < 1000:
                       messages.error(request, 'Cash on Delivery is only available for orders above ₹1000')
                       return redirect('checkout')

                   coupon_id = request.session.get('coupon_id')
                   if coupon_id:
                       try:
                           coupon = Coupon.objects.get(
                               id=coupon_id,
                               is_active=True,
                               valid_from__lte=timezone.now().date(),
                               valid_until__gte=timezone.now().date()
                           )
                           discount = (cart_total * coupon.discount_percentage / 100)
                           final_total = cart_total - discount
                       except Coupon.DoesNotExist:
                           pass
                   
                   if payment_method == 'wallet':
                       wallet = Wallet.objects.get(user=request.user)
                       if wallet.balance < final_total:
                           messages.error(request, 'Insufficient wallet balance')
                           return redirect('checkout')
                   
                   status = 'Confirmed' if payment_method == 'wallet' else 'Pending'
                   
                   order = Order.objects.create(
                       user=request.user,
                       payment=payment_method.upper(),
                       shipping_address=address,
                       status=status,
                       order_no='ORD' + get_random_string(10).upper(),
                       total=final_total,
                       currency='INR'
                   )
                   
                   for item in cart_items:
                       OrderItem.objects.create(
                           order=order,
                           status=status,
                           product_variant=item.product_variant,
                           quantity=item.quantity,
                           total_amount=float(item.total_amount)
                       )
                       
                       variant = item.product_variant
                       if variant.stock_quantity >= item.quantity:
                           variant.stock_quantity -= item.quantity
                           variant.save()
                   
                   if payment_method == 'wallet':
                       wallet.debit(final_total, description=f"Order payment for {order.order_no}")
                   
                   cart_items.delete()
                   request.session.pop('coupon_id', None)
                   request.session.pop('discount_amount', None) 
                   request.session.pop('new_total', None)

                   messages.success(request, 'Order placed successfully!')
                   return redirect('order_success', order_id=order.id)
                   
           except Address.DoesNotExist:
               messages.error(request, 'Please select a valid delivery address')
               return redirect('checkout')
           except Exception as e:
               print(f"Error creating order: {str(e)}")
               messages.error(request, 'Something went wrong. Please try again.')
               return redirect('checkout')
                   
   return redirect('shop')



@login_required
def order_success(request, order_id):
    order = Order.objects.get(id=order_id, user=request.user)
    return render(request, 'order_success.html', {'order': order})



from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.utils import timezone
from datetime import timedelta, datetime
from django.shortcuts import render
from .models import Order  # Ensure Order model is imported

@login_required
def my_orders(request):
    # Get all orders sorted by date (newest first)
    order_list = Order.objects.filter(user=request.user).order_by('-order_date')
    current_time = timezone.now()  # This is timezone-aware

    # Annotate orders with a flag for recent orders
    for order in order_list:
        order_datetime = datetime.combine(order.order_date, datetime.min.time())  # Convert date to datetime
        order_datetime = timezone.make_aware(order_datetime, timezone.get_current_timezone())  # Make it timezone-aware

        order.is_within_two_days = (current_time - order_datetime) <= timedelta(days=2)

    # Set number of orders per page
    items_per_page = 2
    paginator = Paginator(order_list, items_per_page)

    # Get page number from URL parameters
    page = request.GET.get('page', 1)

    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        orders = paginator.page(1)
    except EmptyPage:
        orders = paginator.page(paginator.num_pages)

    context = {
        'orders': orders,
        'total_orders': order_list.count(),
    }

    return render(request, 'my_orders.html', context)

@login_required
@transaction.atomic
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    print("Order Status:", order.status)  # Debug
    print("Payment Method:", order.payment)  # Debug
    
    # Make status comparison case-insensitive
    if order.status.lower() in ['pending', 'confirmed', 'payment_pending']:
        try:
            # Return items to stock
            order_items = order.order_items.all()
            for item in order_items:
                product_variant = item.product_variant
                product_variant.stock_quantity += item.quantity
                product_variant.save()

            print("Processing refund for payment method:", order.payment)  # Debug
            
            # Process refund if payment was made (case-insensitive check)
            if order.payment.upper() in ['RAZORPAY', 'WALLET']:
                print("Initiating wallet credit")  # Debug
                wallet = Wallet.objects.get(user=request.user)
                print("Current wallet balance:", wallet.balance)  # Debug
                
                wallet.credit(
                    amount=order.total,
                    description=f"Refund for cancelled order {order.order_no}"
                )
                print("New wallet balance:", wallet.balance)  # Debug
                
                messages.success(request, f'Order cancelled and amount ₹{order.total} credited to wallet.')
            else:
                messages.success(request, 'Order has been cancelled successfully.')

            order.status = 'Cancelled'
            order.save()

        except Exception as e:
            print("Error:", str(e))  # Debug
            messages.error(request, f'Error cancelling order: {str(e)}')
            
    else:
        messages.error(request, 'This order cannot be cancelled.')

    return redirect('my_orders')


@login_required
def order_details(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    order_items = OrderItem.objects.filter(order=order)  
    
    return render(request, 'order_details.html', {'order': order, 'order_items': order_items})



@login_required
def delete_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    address.delete()
    messages.success(request, "Address deleted successfully.")
    return redirect('manage_address')




from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Wishlist, ProductVariant

@csrf_exempt
def add_to_wishlist(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            product_variant_id = data.get('product_variant_id')

            if not product_variant_id:
                return JsonResponse({"success": False, "error": "Product variant not specified."}, status=400)

            # Get the product variant or return an error if it doesn't exist
            variant = get_object_or_404(ProductVariant, id=product_variant_id)

            # Create or retrieve the wishlist entry for the user and variant
            wishlist, created = Wishlist.objects.get_or_create(
                user=request.user,
                product_variant=variant
            )

            if created:
                return JsonResponse({"success": True, "message": "Item added to your wishlist!"})
            else:
                return JsonResponse({"success": False, "message": "Item already in your wishlist."})

        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON data."}, status=400)

    return JsonResponse({"success": False, "error": "Invalid request method."}, status=405)


@login_required
def remove_from_wishlist(request, variant_id):
    product_variant = get_object_or_404(ProductVariant, id=variant_id)
    Wishlist.objects.filter(user=request.user, product_variant=product_variant).delete()
    messages.success(request, "Product variant removed from your wishlist.")
    return redirect('wishlist')

@login_required
def wishlist_view(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)
    
    # Add the primary image for each item in the wishlist (for specific product variant)
    for item in wishlist_items:
        primary_image = item.product_variant.images.filter(is_primary=True).first()
        item.primary_image = primary_image  # Add primary_image to each wishlist item
    
    return render(request, 'wishlist.html', {'wishlist_items': wishlist_items})

from django.views.decorators.http import require_GET

@login_required
@require_GET
def check_wishlist_status(request):
    variant_id = request.GET.get('variant_id')
    if not variant_id:
        return JsonResponse({'error': 'No variant ID provided'}, status=400)
    
    try:
        in_wishlist = Wishlist.objects.filter(user=request.user, product_variant_id=variant_id).exists()
        return JsonResponse({'in_wishlist': in_wishlist})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    



def add_all_to_cart(request):
    if request.method == 'POST':
        wishlist_items = Wishlist.objects.filter(user=request.user)
        
        if wishlist_items.exists():
            cart_items = []
            insufficient_stock_items = []
            added_to_cart = []
            
            for item in wishlist_items:
                # Check if the stock is available
                if item.product_variant.stock_quantity > 0:
                    # If stock is available, add to cart
                    cart_items.append(CartItem(user=request.user, product_variant=item.product_variant))
                    added_to_cart.append(item)
                else:
                    # If stock is insufficient, store the item for feedback
                    insufficient_stock_items.append(item.product_variant.product.name)
            
            # Bulk create cart items for available stock
            if cart_items:
                CartItem.objects.bulk_create(cart_items)
            
            # Remove only the items that were successfully added to the cart from the wishlist
            if added_to_cart:
                Wishlist.objects.filter(id__in=[item.id for item in added_to_cart]).delete()
            
            # Provide feedback to the user
            if insufficient_stock_items:
                messages.warning(request, f"The following items are out of stock: {', '.join(insufficient_stock_items)}")
            else:
                messages.success(request, 'All available items have been added to your cart!')
        else:
            messages.warning(request, 'Your wishlist is empty.')
    
    return redirect('wishlist')  # Redirect back to wishlist page or cart page



@login_required
def razorpay_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.payment != 'RAZORPAY':
        messages.error(request, "Invalid payment method.")
        return JsonResponse({'status': 'error', 'message': 'Invalid payment method'})

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    if request.method == 'POST':
        try:
            # Get payment details from JSON data
            data = json.loads(request.body)
            payment_id = data.get('razorpay_payment_id')
            razorpay_order_id = data.get('razorpay_order_id')
            signature = data.get('razorpay_signature')

            # Verify the payment signature
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }

            try:
                client.utility.verify_payment_signature(params_dict)

                # Update order in transaction
                with transaction.atomic():
                    # Update order status
                    order.razorpay_payment_id = payment_id
                    order.razorpay_signature = signature
                    order.razorpay_payment_status = 'PAID'
                    order.status = 'confirmed' 
                    order.save()

                    # Update stock
                    for item in order.order_items.all():
                        variant = item.product_variant
                        if variant.stock_quantity >= item.quantity:
                            variant.stock_quantity -= item.quantity
                            variant.save()

                    # Clear cart
                    CartItem.objects.filter(user=request.user).delete()

                return JsonResponse({
                    'status': 'success',
                    'redirect_url': reverse('order_success', args=[order.id])
                })

            except razorpay.errors.SignatureVerificationError:
                order.razorpay_payment_status = 'FAILED'
                order.status = 'PAYMENT_PENDING'
                order.save()
                return JsonResponse({
                    'status': 'error',
                    'message': 'Payment verification failed'
                })

        except Exception as e:
            print(f"Payment error: {str(e)}")  # For debugging
            return JsonResponse({
                'status': 'error',
                'message': 'Payment processing failed'
            })

    # For GET requests
    try:
        razorpay_order = client.order.fetch(order.razorpay_order_id)
        return render(request, 'razorpay_payment.html', {
            'order': order,
            'razorpay_key': settings.RAZORPAY_KEY_ID,
            'razorpay_order_id': order.razorpay_order_id,
            'amount': razorpay_order['amount'],
        })
    except Exception as e:
        messages.error(request, "Failed to fetch payment details.")
        return redirect('checkout')
    
from django.core.paginator import Paginator

def wallet_details(request):
    try:
        wallet = Wallet.objects.get(user=request.user)
        transactions = wallet.transactions.all()
    except Wallet.DoesNotExist:
        messages.error(request, "Wallet not found. Creating a new wallet for you.")
        wallet = Wallet.objects.create(user=request.user)
        transactions = []
    paginator = Paginator(transactions, 5)  # Show 5 transactions per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'wallet.html', {'wallet': wallet, 'transactions': transactions ,'page_obj': page_obj})

def add_money(request):
    if request.method == "POST":
        amount = request.POST.get('amount')

        try:
            # Convert the amount to Decimal to ensure compatibility with the Decimal field
            amount = Decimal(amount)
            
            if amount <= 0:
                messages.error(request, "Amount must be greater than zero.")
                return redirect('wallet')

            # Get the user's wallet
            wallet = Wallet.objects.get(user=request.user)
            wallet.credit(amount, "Added money to wallet")

            messages.success(request, f"₹{amount} added to your wallet.")
        except ValueError:
            messages.error(request, "Invalid amount entered.")
        except Wallet.DoesNotExist:
            messages.error(request, "Wallet not found.")
    
    return redirect('wallet') 


from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from decimal import Decimal
from .models import Coupon

@require_POST
@login_required
def apply_coupon(request):
    code = request.POST.get('coupon_code')
    subtotal = Decimal(request.POST.get('subtotal', '0'))
    
    try:
        # Find and validate coupon
        coupon = Coupon.objects.get(
            code__iexact=code,
            is_active=True,
            is_listed=True,
            valid_from__lte=timezone.now().date(),
            valid_until__gte=timezone.now().date()
        )
        
        # Calculate discount
        discount_amount = (subtotal * coupon.discount_percentage / 100).quantize(Decimal('0.01'))
        new_total = (subtotal - discount_amount).quantize(Decimal('0.01'))
        
        # Store in session
        request.session['coupon_id'] = coupon.id
        request.session['discount_amount'] = str(discount_amount)
        request.session['new_total'] = str(new_total)
        
        return JsonResponse({
            'status': 'success',
            'discount_percentage': float(coupon.discount_percentage),
            'discount_amount': float(discount_amount),
            'new_total': float(new_total),
            'message': f'Coupon applied successfully! You saved ₹{discount_amount}'
        })
        
    except Coupon.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid or expired coupon code'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@require_POST
@login_required
def remove_coupon(request):
    try:
        # Get the original subtotal from request
        data = json.loads(request.body)
        subtotal = Decimal(str(data.get('subtotal', '0')))
        
        # Clear coupon data from session
        request.session.pop('coupon_id', None)
        request.session.pop('discount_amount', None)
        request.session.pop('new_total', None)
        
        return JsonResponse({
            'status': 'success',
            'new_total': float(subtotal),
            'message': 'Coupon removed successfully'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)
    




from io import BytesIO
from decimal import Decimal
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

# Register custom font
pdfmetrics.registerFont(TTFont('DejaVuSans', '/home/ubuntu/first_project/lulee/fonts/DejaVuSans.ttf'))

def generate_invoice(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return HttpResponse("Order not found", status=404)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    # Get styles
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    title_style.fontName = "DejaVuSans"
    normal_style = styles["Normal"]
    normal_style.fontName = "DejaVuSans"

    # Title
    title = Paragraph("<b>LUELEE</b>", title_style)
    elements.append(title)
    elements.append(Spacer(1, 12))

    # Invoice Details
    invoice_details = f"""
    <b>Invoice for Order #{order.id}</b><br/>
    Customer: {order.shipping_address.name}<br/>
    Address: {order.shipping_address.city}, {order.shipping_address.state} - {order.shipping_address.pin_code}, {order.shipping_address.country}<br/>
    Phone: {order.shipping_address.phone_no}<br/>
    Date: {order.order_date}
    """
    elements.append(Paragraph(invoice_details, normal_style))
    elements.append(Spacer(1, 12))

    # Table Data
    data = [["Product", "Quantity", "Price (₹)", "Total (₹)"]]
    for item in order.order_items.all():
        data.append([
            str(item.product_variant),
            str(item.quantity),
            f"₹{item.total_amount / item.quantity:.2f}",
            f"₹{item.total_amount:.2f}"
        ])

    # Table
    table = Table(data, colWidths=[250, 80, 100, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 12))

    # Summary
    subtotal = order.total - Decimal(order.shipping_chrg)
    summary_data = f"""
    <b>Subtotal:</b> ₹{subtotal:.2f}<br/>
    <b>Shipping:</b> ₹{order.shipping_chrg:.2f}<br/>
    <b>Total:</b> <b>₹{order.total:.2f}</b>
    """
    elements.append(Paragraph(summary_data, normal_style))

    # Build the PDF
    doc.build(elements)
    buffer.seek(0)

    # Prepare and send the response
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="invoice_{order.id}.pdf"'
    return response




@csrf_exempt
@login_required
def return_order_item(request, order_item_id):
    if request.method == "POST":
        
        order_item = get_object_or_404(OrderItem, id=order_item_id)

       
        if hasattr(order_item, 'order_item_return'):
            messages.error(request, "A return request already exists for this item.")
            return redirect('order_details', order_id=order_item.order.id)  # Redirect back to the order items page

        
        sizing_issues = request.POST.get('sizing_issues', 'off') == 'on'
        damaged_item = request.POST.get('damaged_item', 'off') == 'on'
        incorrect_order = request.POST.get('incorrect_order', 'off') == 'on'
        delivery_delays = request.POST.get('delivery_delays', 'off') == 'on'
        other_reason = request.POST.get('other_reason', '')

       
        OrderItemReturn.objects.create(
            order_item=order_item,
            sizing_issues=sizing_issues,
            damaged_item=damaged_item,
            incorrect_order=incorrect_order,
            delivery_delays=delivery_delays,
            other_reason=other_reason,
        )

        
        order_item.status = "RETURN_PENDING"
        order_item.save()

        messages.success(request, "Return initiated successfully.")
        return redirect('order_details', order_id=order_item.order.id)  # Redirect back to the order items page

    messages.error(request, "Invalid request method.")
    return redirect('order_details', order_id=order_item.order.id)

@login_required

def wish_addtocart(request, variant_id):
    try:
        # Fetch the wishlist item for the current user based on variant_id
        wishlist_item = get_object_or_404(Wishlist, product_variant__id=variant_id, user=request.user)
        product_variant = wishlist_item.product_variant

        # Check if the product variant has enough stock
        if product_variant.stock_quantity <= 0:
            messages.error(request, f"'{product_variant.product.name}' is out of stock and cannot be added to your cart.")
            return redirect('wishlist')

        # Add or update the product variant in the cart
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            product_variant=product_variant,
            defaults={'quantity': 1, 'total_amount': product_variant.price}
        )

        # If the cart item already exists, check if stock allows increasing quantity
        if not created:
            if cart_item.quantity + 1 > product_variant.stock:
                messages.error(request, f"Only {product_variant.stock} units of '{product_variant.product.name}' are available.")
                return redirect('wishlist')

            # Update the quantity and total amount
            cart_item.quantity += 1
            cart_item.total_amount = cart_item.quantity * product_variant.price
            cart_item.save()

        # Remove the item from the wishlist
        wishlist_item.delete()

        # Success message
        messages.success(request, f"'{product_variant.product.name}' has been added to your cart.")
    except Wishlist.DoesNotExist:
        # Handle the case where the wishlist item doesn't exist
        messages.error(request, "The selected item does not exist in your wishlist.")
    except Exception as e:
        # Catch any other exceptions
        messages.error(request, f"An unexpected error occurred: {str(e)}")

    # Redirect to the wishlist page
    return redirect('wishlist')

from django.http import JsonResponse
import razorpay
from django.conf import settings

@login_required
def repay_order(request, order_id):
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        payment_data = {
            'amount': int(order.total * 100),
            'currency': 'INR',
            'receipt': f'order_{order.id}'
        }
        
        payment = client.order.create(data=payment_data)
        
        return JsonResponse({
            'status': 'success',
            'razorpay_key': settings.RAZORPAY_KEY_ID,
            'amount': payment_data['amount'],
            'rzp_order_id': payment['id']
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def verify_repayment(request, order_id):
    try:
        payment_data = json.loads(request.body)
        order = Order.objects.get(id=order_id, user=request.user)
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        verify = client.utility.verify_payment_signature({
            'razorpay_payment_id': payment_data['razorpay_payment_id'],
            'razorpay_order_id': payment_data['razorpay_order_id'],
            'razorpay_signature': payment_data['razorpay_signature']
        })
        
        if verify:
            order.status = 'Confirmed'
            order.save()
            return JsonResponse({'status': 'success'})
            
        return JsonResponse({'status': 'error', 'message': 'Payment verification failed'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
    



