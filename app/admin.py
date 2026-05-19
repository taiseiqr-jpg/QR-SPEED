from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import Worker, Product, WorkerOutput, Item, Customer, Partname, QRCode, VerificationLog


class PartnameInline(admin.TabularInline):
    model = Partname
    extra = 1
    fields = ('part_name', 'maker')
    show_change_link = True


class ItemInline(admin.TabularInline):
    model = Item
    extra = 1
    fields = ('item', 'part_count_display')
    readonly_fields = ('part_count_display',)
    show_change_link = True

    def part_count_display(self, obj):
        if obj.pk:
            count = obj.partnames.count()
            return f"{count} part{'s' if count != 1 else ''}"
        return "New item"
    part_count_display.short_description = 'Parts'


class CustomerAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'total_items', 'total_parts_across_items', 'items_preview')
    search_fields = ('customer_name',)
    inlines = [ItemInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            items_count=Count('items', distinct=True),
            parts_count=Count('items__partnames', distinct=True)
        )

    def total_items(self, obj):
        return obj.items.count()
    total_items.short_description = 'Total Items'
    total_items.admin_order_field = 'items_count'

    def total_parts_across_items(self, obj):
        if hasattr(obj, 'parts_count'):
            return obj.parts_count
        return sum(item.partnames.count() for item in obj.items.all())
    total_parts_across_items.short_description = 'Total Parts'
    total_parts_across_items.admin_order_field = 'parts_count'

    def items_preview(self, obj):
        items = obj.items.all()[:3]
        if not items:
            return "No items"

        preview = []
        for item in items:
            part_count = item.partnames.count()
            preview.append(f"• {item.item} ({part_count} parts)")

        if obj.items.count() > 3:
            preview.append(f"... and {obj.items.count() - 3} more")

        return format_html('<br>'.join(preview))
    items_preview.short_description = 'Items Preview'


class ItemAdmin(admin.ModelAdmin):
    list_display = ('item', 'customer', 'part_count', 'parts_preview', 'has_parts_status')
    list_filter = ('customer',)
    search_fields = ('item', 'customer__customer_name')
    inlines = [PartnameInline]
    autocomplete_fields = ['customer']

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            parts_count=Count('partnames', distinct=True)
        ).select_related('customer')

    def part_count(self, obj):
        if hasattr(obj, 'parts_count'):
            return obj.parts_count
        return obj.partnames.count()
    part_count.short_description = '# of Parts'
    part_count.admin_order_field = 'parts_count'

    def parts_preview(self, obj):
        parts = obj.partnames.all()[:3]
        if not parts:
            return "No parts"

        preview = [f"• {part.part_name} ({part.maker})" for part in parts]

        if obj.partnames.count() > 3:
            preview.append(f"... and {obj.partnames.count() - 3} more")

        return format_html('<br>'.join(preview))
    parts_preview.short_description = 'Parts Preview'

    def has_parts_status(self, obj):
        count = self.part_count(obj)
        if count == 0:
            return "❌ Empty"
        if count < 5:
            return f"⚠️ {count} parts"
        return f"✅ {count} parts"
    has_parts_status.short_description = 'Status'


class PartnameAdmin(admin.ModelAdmin):
    list_display = ('part_name', 'maker', 'item', 'customer_name', 'full_hierarchy')
    list_filter = ('maker', 'item__customer')
    search_fields = ('part_name', 'maker', 'item__item', 'item__customer__customer_name')
    list_select_related = ('item', 'item__customer')
    autocomplete_fields = ['item']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('item__customer')

    def customer_name(self, obj):
        return obj.item.customer.customer_name
    customer_name.short_description = 'Customer'
    customer_name.admin_order_field = 'item__customer__customer_name'

    def full_hierarchy(self, obj):
        return format_html(
            '{} → {} → <strong>{}</strong>',
            obj.item.customer.customer_name,
            obj.item.item,
            obj.part_name
        )
    full_hierarchy.short_description = 'Hierarchy Path'


class WorkerAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'first_name', 'last_name', 'username', 'role')


class ProductAdmin(admin.ModelAdmin):
    list_display = ('item_code', 'part_no', 'process', 'customer', 'product_family')


class WorkerOutputAdmin(admin.ModelAdmin):
    list_display = ('lot_no', 'current_status', 'output_data')


class QRCodeAdmin(admin.ModelAdmin):
    list_display = [
        'qr_uuid_short',
        'item_name',
        'part_name',
        'lot_no',
        'status_colored',
        'qr_image_preview',
        'verified_at_short',
        'created_at_short'
    ]
    list_filter = ['status', 'part_maker', 'created_at', 'verified_at']
    search_fields = ['qr_uuid', 'item_name', 'part_name', 'part_maker', 'lot_no']
    readonly_fields = ['qr_uuid', 'created_at', 'qr_image_display', 'qr_data_preview']
    fieldsets = [
        ('Item Information', {'fields': ['item_name', 'part_name', 'part_maker', 'lot_no']}),
        ('QR Code', {'fields': ['qr_uuid', 'qr_image', 'qr_image_display', 'qr_data_preview']}),
        ('Status Information', {'fields': ['status', 'verified_at', 'created_by']}),
        ('Metadata', {'fields': ['created_at'], 'classes': ['collapse']}),
    ]
    list_per_page = 25
    date_hierarchy = 'created_at'
    actions = ['mark_as_good', 'mark_as_no_good', 'clear_status']

    def qr_uuid_short(self, obj):
        return str(obj.qr_uuid)[:8] + '...'
    qr_uuid_short.short_description = 'QR ID'
    qr_uuid_short.admin_order_field = 'qr_uuid'

    def status_colored(self, obj):
        if obj.status == QRCode.Status.GOOD:
            return format_html('<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">✓ {}</span>', obj.get_status_display())
        if obj.status == QRCode.Status.NO_GOOD:
            return format_html('<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">✗ {}</span>', obj.get_status_display())
        return format_html('<span style="background-color: #6c757d; color: white; padding: 3px 10px; border-radius: 3px;">⏳ Pending</span>')
    status_colored.short_description = 'Status'
    status_colored.admin_order_field = 'status'

    def qr_image_preview(self, obj):
        if obj.qr_image and hasattr(obj.qr_image, 'url'):
            return format_html('<img src="{}" style="max-height: 50px; max-width: 50px; border-radius: 5px; border: 1px solid #ddd;" />', obj.qr_image.url)
        return format_html('<span style="color: #999;">No image</span>')
    qr_image_preview.short_description = 'QR'

    def qr_image_display(self, obj):
        if obj.qr_image and hasattr(obj.qr_image, 'url'):
            return format_html(
                '<div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; display: inline-block;">'
                '<img src="{}" style="max-height: 300px; max-width: 300px; border: 2px solid #ddd; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />'
                '<br><br><a href="{}" target="_blank" style="background-color: #007bff; color: white; padding: 8px 15px; text-decoration: none; border-radius: 5px;">🔍 View Full Size</a></div>',
                obj.qr_image.url, obj.qr_image.url
            )
        return format_html('<div style="background-color: #f8f9fa; padding: 40px; border-radius: 10px; text-align: center; color: #999;"><span style="font-size: 48px;">📷</span><br><span>No QR code image uploaded</span></div>')
    qr_image_display.short_description = 'QR Code Image'

    def verified_at_short(self, obj):
        if obj.verified_at:
            return obj.verified_at.strftime('%Y-%m-%d %H:%M')
        return '-'
    verified_at_short.short_description = 'Verified'
    verified_at_short.admin_order_field = 'verified_at'

    def created_at_short(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_short.short_description = 'Created'
    created_at_short.admin_order_field = 'created_at'

    def qr_data_preview(self, obj):
        import json
        data = obj.generate_qr_data()
        formatted_json = json.dumps(data, indent=2)
        return format_html('<div style="background-color: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 8px; font-family: monospace;"><pre style="margin: 0; color: inherit;">{}</pre></div>', formatted_json)
    qr_data_preview.short_description = 'QR Code Data'

    def mark_as_good(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status=QRCode.Status.GOOD, verified_at=timezone.now())
        self.message_user(request, f'✅ {updated} QR code(s) marked as GOOD.')
    mark_as_good.short_description = "Mark selected as GOOD"

    def mark_as_no_good(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status=QRCode.Status.NO_GOOD, verified_at=timezone.now())
        self.message_user(request, f'❌ {updated} QR code(s) marked as NO GOOD.')
    mark_as_no_good.short_description = "Mark selected as NO GOOD"

    def clear_status(self, request, queryset):
        updated = queryset.update(status=None, verified_at=None)
        self.message_user(request, f'⏳ Status cleared from {updated} QR code(s).')
    clear_status.short_description = "Clear status"

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user.username
        super().save_model(request, obj, form, change)


class VerificationLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'qr_uuid_short', 'part_name', 'qr_item', 'status_colored', 'result_colored', 'backend_updated_badge', 'timestamp_short', 'verified_by']
    list_filter = ['status', 'result', 'backend_updated', 'timestamp', 'verified_by']
    search_fields = ['qr_uuid', 'qr_item', 'user_item', 'verified_by']
    readonly_fields = ['id', 'qr_uuid', 'timestamp']
    list_per_page = 25
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    actions = ['mark_backend_updated', 'mark_backend_not_updated']

    def qr_uuid_short(self, obj):
        return str(obj.qr_uuid)[:8] + '...'
    qr_uuid_short.short_description = 'QR ID'
    qr_uuid_short.admin_order_field = 'qr_uuid'

    def status_colored(self, obj):
        if obj.status == VerificationLog.Result.GOOD:
            return format_html('<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">✓ {}</span>', obj.get_status_display())
        if obj.status == VerificationLog.Result.NO_GOOD:
            return format_html('<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">✗ {}</span>', obj.get_status_display())
        return format_html('<span style="background-color: #6c757d; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>', obj.get_status_display())
    status_colored.short_description = 'Status'
    status_colored.admin_order_field = 'status'

    def result_colored(self, obj):
        if obj.result == VerificationLog.Result.GOOD:
            return format_html('<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">✓ {}</span>', obj.get_result_display())
        if obj.result == VerificationLog.Result.NO_GOOD:
            return format_html('<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">✗ {}</span>', obj.get_result_display())
        return format_html('<span style="background-color: #6c757d; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>', obj.get_result_display())
    result_colored.short_description = 'Result'
    result_colored.admin_order_field = 'result'

    def backend_updated_badge(self, obj):
        if obj.backend_updated:
            return format_html('<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">✓ Yes</span>')
        return format_html('<span style="background-color: #ffc107; color: black; padding: 3px 10px; border-radius: 3px; font-weight: bold;">⚠ No</span>')
    backend_updated_badge.short_description = 'Backend Updated'
    backend_updated_badge.admin_order_field = 'backend_updated'

    def timestamp_short(self, obj):
        return obj.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    timestamp_short.short_description = 'Timestamp'
    timestamp_short.admin_order_field = 'timestamp'

    def mark_backend_updated(self, request, queryset):
        updated = queryset.update(backend_updated=True)
        self.message_user(request, f'✅ {updated} verification log(s) marked as backend updated.')
    mark_backend_updated.short_description = "Mark selected as backend updated"

    def mark_backend_not_updated(self, request, queryset):
        updated = queryset.update(backend_updated=False)
        self.message_user(request, f'⚠ {updated} verification log(s) marked as backend not updated.')
    mark_backend_not_updated.short_description = "Mark selected as backend not updated"


admin.site.register(Worker, WorkerAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(WorkerOutput, WorkerOutputAdmin)
admin.site.register(Customer, CustomerAdmin)
admin.site.register(Item, ItemAdmin)
admin.site.register(Partname, PartnameAdmin)
admin.site.register(QRCode, QRCodeAdmin)
admin.site.register(VerificationLog, VerificationLogAdmin)
