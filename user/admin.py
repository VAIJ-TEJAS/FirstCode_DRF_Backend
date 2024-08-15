from django.contrib import admin
from .models import Pattern, UserProfile

class UserProfileInline(admin.TabularInline):
    model = UserProfile
    extra = 1  

@admin.register(Pattern)
class PatternAdmin(admin.ModelAdmin):
    list_display = ['name']
    inlines = [UserProfileInline]

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'user_subscription', 'pattern']
    list_filter = ['user_subscription', 'pattern']
    search_fields = ['user__username']
