from django.contrib import admin
from .models import Order

class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'subscription', 'subscription_type', 'completed', 'created_at')
    list_filter = ('completed', 'subscription_type')
    search_fields = ('order_id', 'subscription__name')  # Assuming Subscription has a 'name' field
    ordering = ('-created_at',)  # Order by creation date, most recent first
    actions = ['delete_expired_orders']

    def delete_expired_orders(self, request, queryset):
        Order.delete_expired_orders()
        self.message_user(request, "Expired orders have been deleted.")
    delete_expired_orders.short_description = "Delete expired orders"

admin.site.register(Order, OrderAdmin)
