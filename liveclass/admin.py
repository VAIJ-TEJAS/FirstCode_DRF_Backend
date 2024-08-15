from django.contrib import admin
from .models import LiveClass, UserLiveClass

class UserLiveClassInline(admin.TabularInline):
    model = UserLiveClass
    extra = 1  

@admin.register(LiveClass)
class LiveClassAdmin(admin.ModelAdmin):
    list_display = ['name', 'batch_name', 'start_date', 'duration', 'medium', 'is_paid']
    inlines = [UserLiveClassInline]

@admin.register(UserLiveClass)
class UserLiveClassAdmin(admin.ModelAdmin):
    list_display = ['user', 'live_class', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['user__username', 'live_class__name']
