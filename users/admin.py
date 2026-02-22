from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
	fieldsets = UserAdmin.fieldsets + (
		(
			"营养信息",
			{
				"fields": (
					"age",
					"weight",
					"height",
					"goal",
				)
			},
		),
	)

	add_fieldsets = UserAdmin.add_fieldsets + (
		(
			"营养信息",
			{
				"fields": (
					"age",
					"weight",
					"height",
					"goal",
				)
			},
		),
	)

	list_display = UserAdmin.list_display + ("age", "weight", "height", "goal")
