# Generated by Django 5.2.1 on 2025-06-14 12:35

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trading_buddy', '0003_alter_trade_commission_usd_alter_trade_pnl_usd'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='current_account',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='trading_buddy.account'),
        ),
    ]
