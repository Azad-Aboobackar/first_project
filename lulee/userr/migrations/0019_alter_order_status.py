# Generated by Django 5.1.4 on 2025-01-16 08:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('userr', '0018_wallet_transaction'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('shipped', 'Shipped'), ('delivered', 'Delivered'), ('cancelled', 'Cancelled'), ('PAYMENT_PENDING', 'PAYMENT_PENDING')], default='Pending', max_length=20),
        ),
    ]
