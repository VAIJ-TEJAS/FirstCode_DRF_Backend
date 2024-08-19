from django.contrib import admin
from .models import Pattern, UserProfile


class UserProfileInline(admin.TabularInline):
    model = UserProfile
    extra = 1


@admin.register(Pattern)
class PatternAdmin(admin.ModelAdmin):
    list_display = ["name"]
    inlines = [UserProfileInline]


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "pattern"]
    list_filter = ["pattern"]
    search_fields = ["user__username"]
