from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _

class CustomAuthenticationForm(AuthenticationForm):
    email = forms.EmailField(
        label=_("Email"),
        widget=forms.TextInput(attrs={"autofocus": True})
    )

from django import forms
from .models import Address  # Import your Address model

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['name', 'phone_no', 'street_address', 'city', 'state', 'pin_code', 'country', 'is_primary']