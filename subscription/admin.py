from django.contrib import admin
from .models import Subscription, UserSubscription

class UserSubscriptionInline(admin.TabularInline):
    model = UserSubscription
    extra = 1  

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['name', 'validity', 'price']
    inlines = [UserSubscriptionInline]

@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['subscription', 'payment_id', 'status', 'subscription_start_date', 'subscription_end_date']
    list_filter = ['status', 'payment_method']
    search_fields = ['payment_id', 'order_id']
