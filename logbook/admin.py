from django.contrib import admin
from .models import Profile, Boat, Trip, Tag, LogEntry

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number')
    search_fields = ('user__username', 'phone_number')

@admin.register(Boat)
class BoatAdmin(admin.ModelAdmin):
    list_display = ('name',)
    filter_horizontal = ('shared_users',)

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('title', 'boat', 'start_date', 'is_active')
    list_filter = ('is_active', 'boat')
    prepopulated_fields = {'slug': ('title',)}

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('trip', 'timestamp', 'latitude', 'longitude')
    list_filter = ('trip', 'tags')
    filter_horizontal = ('tags',)
