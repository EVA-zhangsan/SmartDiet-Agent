from django.contrib import admin

from .models import DietPlan, DietPlanItem


class DietPlanItemInline(admin.TabularInline):
	model = DietPlanItem
	extra = 1


@admin.register(DietPlan)
class DietPlanAdmin(admin.ModelAdmin):
	list_display = ("user", "date", "target_calories")
	list_filter = ("date",)
	search_fields = ("user__username",)
	inlines = (DietPlanItemInline,)


@admin.register(DietPlanItem)
class DietPlanItemAdmin(admin.ModelAdmin):
	list_display = ("diet_plan", "meal_type", "recipe", "portion")
	list_filter = ("meal_type",)
