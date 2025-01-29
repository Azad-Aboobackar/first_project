# Generated by Django 5.1.4 on 2025-01-17 04:19

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('userr', '0019_alter_order_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='Coupon',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=20, unique=True)),
                ('discount_percentage', models.DecimalField(decimal_places=2, max_digits=5)),
                ('valid_from', models.DateField()),
                ('valid_until', models.DateField()),
                ('is_active', models.BooleanField(default=True)),
                ('is_listed', models.BooleanField(default=True)),
            ],
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('shipped', 'Shipped'), ('delivered', 'Delivered'), ('cancelled', 'Cancelled'), ('PAYMENT_PENDING', 'PAYMENT_PENDING'), ('return', 'Return'), ('returned', 'Returned')], default='Pending', max_length=20),
        ),
        migrations.CreateModel(
            name='Offer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('discount', models.DecimalField(decimal_places=2, max_digits=5)),
                ('description', models.TextField()),
                ('offer_type', models.CharField(choices=[('category', 'Category'), ('product', 'Product')], max_length=10)),
                ('end_date', models.DateField()),
                ('is_listed', models.BooleanField(default=True)),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='userr.category')),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='userr.product')),
            ],
        ),
    ]
