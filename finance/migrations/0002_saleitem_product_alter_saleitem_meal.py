# Generated by Django 5.0.6 on 2024-08-12 10:41

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0001_initial'),
        ('inventory', '0005_rename_raw_material_dish_major_raw_material_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='saleitem',
            name='product',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='inventory.product'),
        ),
        migrations.AlterField(
            model_name='saleitem',
            name='meal',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='inventory.meal'),
        ),
    ]