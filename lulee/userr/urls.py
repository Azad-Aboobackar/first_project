from django.urls import path
from .views import usersignup,userlogin,signup_otp,reset_password,home_page,men_page,women_page,kid_page,buying_page,user_profile,userlogout
from . import views
urlpatterns = [
    path('signup/',usersignup,name='usersignup'), 
    path('login/',userlogin,name='userlogin'),
    path('signup_otp/',signup_otp,name='signup_otp'),
    path('reset_password/',reset_password,name='reset_password'),
    path('',home_page,name='home'),
    path('men/',men_page,name='men'),
    path('women/',women_page,name='women'),
    path('kid/',kid_page,name='kid'),
    path('buying/<int:product_id>/',buying_page,name='buying'),
    path('userprofile/',user_profile,name='userprofile'),
    path('userlogout/',userlogout,name='userlogout'),
    path('manage-address/', views.manage_address, name='manage_address'),
    path('add-address/', views.add_address, name='add_address'),
    path('edit-address/<int:address_id>/', views.edit_address, name='edit_address'),
    path('edit-profile/<int:user_id>/', views.edit_profile, name='edit_profile'),
    path('manage-password',views.manage_password,name='manage_password'),
    path('cart/', views.cart_page, name='cart_page'),
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('cart/update-quantity/<int:item_id>/', views.update_cart_item_quantity, name='update_cart_item_quantity'),
    path('cart/remove/<int:item_id>/', views.remove_cart_item, name='remove_cart_item'),
    path('shop/', views.shop_view, name='shop'),
    path('set-primary/<int:address_id>/', views.set_primary_address, name='set_primary_address'),
    path('checkout/',views.checkout,name='checkout'),
    path('address-add/', views.address_add, name='address_add'),
    path('place-order',views.create_order,name='place_order'),
    path('order/success/<int:order_id>/', views.order_success, name='order_success'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('cancel-order/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('order-details/<int:order_id>/', views.order_details, name='order_details'),
    path('password-reset/', views.password_reset_request, name='password_reset_request'),
    path('password-reset/otp/', views.password_reset_otp, name='password_reset_otp'),
    path('password-reset/<str:email>/', views.password_reset, name='password_reset'),
    path('delete-address/<int:address_id>/', views.delete_address, name='delete_address'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('add-to-wishlist/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:variant_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('check-wishlist-status/', views.check_wishlist_status, name='check_wishlist_status'),
    path('wishlist/add_all_to_cart/', views.add_all_to_cart, name='add_all_to_cart'),
    path('razorpay-payment/<int:order_id>/', views.razorpay_payment, name='razorpay_payment'),
    path('wallet/', views.wallet_details, name='wallet'),
    path('add-money/', views.add_money, name='add_money'),
    path('apply-coupon/', views.apply_coupon, name='apply_coupon'), 
    path('remove-coupon/', views.remove_coupon, name='remove_coupon'),
    path('invoice/<int:order_id>/',views.generate_invoice, name='generate_invoice'),
    path('return-item/<int:order_item_id>/', views.return_order_item, name='return_order_item'),
    path('wish_addtocart/<int:variant_id>/', views.wish_addtocart, name='wish_addtocart'),
    path('repay-order/<int:order_id>/', views.repay_order, name='repay_order'),
    path('verify-repayment/<int:order_id>/', views.verify_repayment, name='verify_repayment'),
]
