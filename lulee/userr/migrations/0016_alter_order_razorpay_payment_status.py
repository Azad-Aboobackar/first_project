# Generated by Django 5.1.4 on 2025-01-16 05:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('userr', '0015_order_razorpay_payment_status_alter_order_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='razorpay_payment_status',
            field=models.CharField(default='PENDING', max_length=20),
        ),
    ]
