# Generated by Django 5.2.1 on 2025-06-13 10:24

import django.contrib.auth.models
import django.contrib.auth.validators
import django.contrib.postgres.fields
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('deposit', models.DecimalField(decimal_places=2, default=0.0, max_digits=20)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'abstract': False,
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('risk_percent', models.DecimalField(decimal_places=5, default=3.0, max_digits=10)),
                ('exchange', models.CharField(choices=[('BingX', 'BingX'), ('ByBit', 'ByBit')], max_length=120)),
                ('api_key', models.TextField()),
                ('secret_key', models.TextField()),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='accounts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('name', 'user')},
            },
        ),
        migrations.CreateModel(
            name='Tool',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Tool name WITH exchange-appropriate suffix, e.g: BTC-USDT, not just BTC', max_length=120)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tools', to='trading_buddy.account')),
            ],
            options={
                'unique_together': {('name', 'account')},
            },
        ),
        migrations.CreateModel(
            name='Trade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('side', models.CharField(choices=[('LONG', 'Long'), ('SHORT', 'Short')], max_length=5)),
                ('start_time', models.DateTimeField(null=True)),
                ('end_time', models.DateTimeField(null=True)),
                ('risk_percent', models.DecimalField(decimal_places=5, default=0, max_digits=10)),
                ('risk_usd', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('pnl_usd', models.DecimalField(decimal_places=8, default=0, help_text='Net profit, after commissions', max_digits=20)),
                ('commission_usd', models.DecimalField(decimal_places=8, default=0, max_digits=20)),
                ('description', models.TextField(null=True)),
                ('result', models.TextField(null=True)),
                ('screenshot', models.ImageField(null=True, upload_to='screenshots')),
                ('account', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='trades', to='trading_buddy.account')),
                ('tool', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='trades', to='trading_buddy.tool')),
            ],
        ),
        migrations.CreateModel(
            name='Position',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('side', models.CharField(choices=[('LONG', 'Long'), ('SHORT', 'Short')], max_length=5, null=True)),
                ('leverage', models.IntegerField()),
                ('trigger_price', models.DecimalField(decimal_places=12, default=0.0, max_digits=20)),
                ('entry_price', models.DecimalField(decimal_places=12, max_digits=20)),
                ('stop_price', models.DecimalField(decimal_places=12, max_digits=20)),
                ('take_profit_prices', django.contrib.postgres.fields.ArrayField(base_field=models.DecimalField(decimal_places=12, max_digits=20), default=list, size=None)),
                ('cancel_levels', django.contrib.postgres.fields.ArrayField(base_field=models.DecimalField(decimal_places=12, max_digits=20), default=list, size=None)),
                ('start_time', models.DateTimeField(null=True)),
                ('move_stop_after', models.IntegerField()),
                ('primary_volume', models.DecimalField(decimal_places=12, max_digits=20)),
                ('current_volume', models.DecimalField(decimal_places=12, max_digits=20)),
                ('fill_history', django.contrib.postgres.fields.ArrayField(base_field=django.contrib.postgres.fields.ArrayField(base_field=models.DecimalField(decimal_places=12, max_digits=20), size=None), default=list, null=True, size=None)),
                ('last_status', models.CharField(default='NEW', max_length=50, null=True)),
                ('breakeven', models.BooleanField(default=False)),
                ('pnl_usd', models.DecimalField(decimal_places=8, default=0, max_digits=20)),
                ('commission_usd', models.DecimalField(decimal_places=8, default=0, max_digits=20)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='positions', to='trading_buddy.account')),
                ('tool', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='positions', to='trading_buddy.tool')),
                ('trade', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='position', to='trading_buddy.trade')),
            ],
        ),
    ]
