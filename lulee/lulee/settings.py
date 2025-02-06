"""
Django settings for luelee project.

Generated by 'django-admin startproject' using Django 5.1.4.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path
import cloudinary
import cloudinary.uploader
import cloudinary.api
from dotenv import load_dotenv
import os

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-i8h%f(#47vo$1)f(*n6((5+s@pnx1ye2qdv73_e&$)ou^uz+so'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'userr',
    'django.contrib.sites',    # Required for managing social authentication sites
    'social_django',
    'cloudinary',
    'cloudinary_storage',
    'adminn',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'lulee.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'lulee.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'luelee',
        'USER': 'postgres',
        'PASSWORD': '123456',
        'HOST': 'localhost',
        'PORT': '5433',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]


# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587  # or 465 for SSL
EMAIL_USE_TLS = True  # or use SSL with port 465
EMAIL_HOST_USER = 'azadaboobackar2@gmail.com'  # Your Gmail address
EMAIL_HOST_PASSWORD = 'dpln apzd tqxr nuzg'  # Replace with your app-specific password
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER




AUTHENTICATION_BACKENDS = (
    'social_core.backends.google.GoogleOAuth2',   # Google OAuth2 backend
    'django.contrib.auth.backends.ModelBackend',  # Django's default auth backend
)



SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = '127995760400-pv46tn92uuog8f6a87c3n81nq5v1vf6g.apps.googleusercontent.com'
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = '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'

# Optional: Redirect URLs
LOGIN_REDIRECT_URL = '/'  # Redirect after login
LOGOUT_REDIRECT_URL = 'userlogin'  # Redirect after logout
LOGIN_URL='login/'



site_id = 2

AUTH_USER_MODEL = 'userr.CustomUser'


SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',       # Get user details from provider
    'social_core.pipeline.social_auth.social_uid',           # Get unique social ID
    'social_core.pipeline.social_auth.auth_allowed',         # Check if login is allowed
    'social_core.pipeline.social_auth.social_user',          # Try to find the user by social ID
    'social_core.pipeline.user.get_username',                # Generate a username if needed
    'userr.pipeline.create_user',                    # Custom pipeline function for user creation
    'social_core.pipeline.social_auth.associate_user',       # Associate social account with user
    'social_core.pipeline.social_auth.load_extra_data',      # Load extra data from provider
    'social_core.pipeline.user.user_details',                # Update user details if needed
)




cloudinary.config(
    cloud_name='dmbj17v75',  # Replace with your Cloudinary cloud name
    api_key='492781415636527',        # Replace with your API key
    api_secret='JZvfsCm6myc9zRTwvViKKUKLBWM'   # Replace with your API secret
)

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'





# Then get the keys using os.environ.get()
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET')
RAZORPAY_CURRENCY = 'INR'  # Add this line
