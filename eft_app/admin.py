from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User, Group
from django.contrib import messages
from .models import (
    Bank, Zone, Scheme, Supplier, DebitAccount,
    EFTBatch, EFTTransaction, ApprovalAuditLog
)

# Custom User Admin - SIMPLIFIED for Django Admin
class CustomUserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_groups', 'is_staff', 'is_active')
    list_filter = ('groups', 'is_staff', 'is_active')
    
    def get_groups(self, obj):
        return ", ".join([g.name for g in obj.groups.all()])
    get_groups.short_description = 'Roles'

# Unregister default and register custom
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Bank Admin
@admin.register(Bank)
class BankAdmin(admin.ModelAdmin):
    list_display = ('bank_name', 'swift_code', 'is_active', 'created_by', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('bank_name', 'swift_code')
    readonly_fields = ('created_by', 'created_at')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

# Zone Admin
@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ('zone_code', 'zone_name', 'is_active', 'created_at')
    search_fields = ('zone_code', 'zone_name')

# Scheme Admin
@admin.register(Scheme)
class SchemeAdmin(admin.ModelAdmin):
    list_display = ('scheme_code', 'scheme_name', 'zone', 'default_cost_center', 'is_active', 'created_at')
    list_filter = ('zone', 'is_active')
    search_fields = ('scheme_code', 'scheme_name')

# Supplier Admin
@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('supplier_code', 'supplier_name', 'bank', 'account_number', 'is_active', 'created_by', 'created_at')
    list_filter = ('bank', 'is_active')
    search_fields = ('supplier_code', 'supplier_name', 'account_number')
    readonly_fields = ('created_by', 'created_at')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

# Debit Account Admin
@admin.register(DebitAccount)
class DebitAccountAdmin(admin.ModelAdmin):
    list_display = ('account_number', 'account_name', 'is_active', 'created_at')
    search_fields = ('account_number', 'account_name')

# Inline for EFT Transactions
class EFTTransactionInline(admin.TabularInline):
    model = EFTTransaction
    extra = 0
    readonly_fields = ('sequence_number', 'zone', 'created_at')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False

# EFT Batch Admin
@admin.register(EFTBatch)
class EFTBatchAdmin(admin.ModelAdmin):
    list_display = ('batch_reference', 'batch_name', 'status', 'total_amount', 
                   'record_count', 'created_by', 'created_at', 'approved_by', 'approved_at')
    list_filter = ('status', 'created_at')
    search_fields = ('batch_reference', 'batch_name')
    readonly_fields = ('batch_reference', 'total_amount', 'record_count', 'created_by', 
                      'created_at', 'approved_by', 'approved_at', 'rejection_reason')
    inlines = [EFTTransactionInline]
    
    def has_add_permission(self, request):
        return False

# Approval Audit Log Admin
@admin.register(ApprovalAuditLog)
class ApprovalAuditLogAdmin(admin.ModelAdmin):
    list_display = ('batch', 'action', 'user', 'timestamp', 'ip_address')
    list_filter = ('action', 'timestamp')
    search_fields = ('batch__batch_reference', 'user__username')
    readonly_fields = ('batch', 'action', 'user', 'timestamp', 'remarks', 'ip_address')
    
    def has_add_permission(self, request):
        return False

# Custom Group Admin
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_permissions_count')
    filter_horizontal = ('permissions',)
    
    def get_permissions_count(self, obj):
        return obj.permissions.count()
    get_permissions_count.short_description = 'Permissions Count'

admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)