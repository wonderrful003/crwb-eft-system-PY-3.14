"""
Models for EFT System - Python 3.14 + Django 5.0.6
Two-stage approval: Accounts → Finance Manager → Director of Finance
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, RegexValidator
from django.utils import timezone
import uuid
from django.db.models import Sum, Count
from django.core.exceptions import ValidationError


class Bank(models.Model):
    bank_name = models.CharField(max_length=100)
    swift_code = models.CharField(
        max_length=11,
        unique=True,
        validators=[RegexValidator(r'^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$', 'Invalid SWIFT code')]
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='banks_created')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['bank_name']

    def __str__(self):
        return f"{self.bank_name} ({self.swift_code})"

    @property
    def code(self):
        return self.swift_code[:4] if self.swift_code else ""


class Zone(models.Model):
    zone_code = models.CharField(max_length=10, unique=True)
    zone_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['zone_code']

    def __str__(self):
        return f"{self.zone_code} - {self.zone_name}"


class Scheme(models.Model):
    scheme_code = models.CharField(max_length=10, unique=True)
    scheme_name = models.CharField(max_length=200)
    zone = models.ForeignKey(Zone, on_delete=models.PROTECT, related_name='schemes')
    default_cost_center = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['scheme_code']

    def __str__(self):
        return f"{self.scheme_code} - {self.scheme_name}"


class Supplier(models.Model):
    supplier_code = models.CharField(max_length=20, unique=True)
    supplier_name = models.CharField(max_length=200)
    bank = models.ForeignKey(Bank, on_delete=models.PROTECT, related_name='suppliers')
    account_number = models.CharField(max_length=30)
    account_name = models.CharField(max_length=200)
    employee_number = models.CharField(max_length=6, blank=True)
    national_id = models.CharField(max_length=8, blank=True)
    credit_reference = models.CharField(max_length=50, blank=True)
    cost_center = models.CharField(max_length=50, blank=True)
    source = models.CharField(max_length=18, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='suppliers_created')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['supplier_name']

    def __str__(self):
        return f"{self.supplier_code} - {self.supplier_name}"


class DebitAccount(models.Model):
    account_number = models.CharField(max_length=20, unique=True)
    account_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['account_number']

    def __str__(self):
        return f"{self.account_number} - {self.account_name}"


class EFTBatch(models.Model):
    """EFT Batch Header — two-stage approval workflow"""

    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING_FM', 'Pending Finance Manager'),
        ('PENDING_DIRECTOR', 'Pending Director of Finance'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('EXPORTED', 'Exported to RBM'),
    ]

    batch_name = models.CharField(max_length=100)
    batch_reference = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    currency = models.CharField(max_length=3, default='MWK')
    total_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    record_count = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    file_reference = models.CharField(max_length=16, blank=True)

    debit_account = models.ForeignKey(DebitAccount, on_delete=models.PROTECT, null=True, blank=True, related_name='batches')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='batches_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Finance Manager review
    fm_reviewed_by = models.ForeignKey(
        User, on_delete=models.PROTECT,
        null=True, blank=True, related_name='batches_fm_reviewed'
    )
    fm_reviewed_at = models.DateTimeField(null=True, blank=True)
    fm_remarks = models.TextField(blank=True)

    # Director of Finance approval
    approved_by = models.ForeignKey(
        User, on_delete=models.PROTECT,
        null=True, blank=True, related_name='batches_approved'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    generated_file = models.TextField(blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.batch_reference} - {self.batch_name}"

    def save(self, *args, **kwargs):
        if not self.file_reference:
            date_str = timezone.now().strftime('%d.%m.%Y')
            self.file_reference = f"CRWB-{date_str}"
        super().save(*args, **kwargs)

    def update_totals(self):
        totals = self.transactions.aggregate(
            total_amount=Sum('amount'),
            transaction_count=Count('id')
        )
        self.total_amount = totals.get('total_amount') or 0
        self.record_count = totals.get('transaction_count') or 0
        self.save(update_fields=['total_amount', 'record_count', 'updated_at'])
        return self.total_amount, self.record_count

    @property
    def can_fm_review(self):
        return self.status == 'PENDING_FM'

    @property
    def can_director_approve(self):
        return self.status == 'PENDING_DIRECTOR'


class EFTTransaction(models.Model):
    """Individual EFT Transaction — RBM Compliant (16-field body record)"""
    batch = models.ForeignKey(EFTBatch, on_delete=models.CASCADE, related_name='transactions')
    sequence_number = models.CharField(max_length=4)

    debit_account = models.ForeignKey(DebitAccount, on_delete=models.PROTECT, related_name='transactions')
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='transactions')
    scheme = models.ForeignKey(Scheme, on_delete=models.PROTECT, related_name='transactions')
    zone = models.ForeignKey(Zone, on_delete=models.PROTECT, related_name='transactions')

    amount = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(0.01)])

    # RBM Required Fields — matches exact column order in RBM spec
    narration = models.CharField(max_length=200)       # Field 16: Description
    reference_number = models.CharField(max_length=16) # Field 11: Invoice Number / Payee's Reference
    source_reference = models.CharField(max_length=18) # Field 15: Source reference (IFMIS)

    # Optional Fields
    employee_number = models.CharField(max_length=6, blank=True)   # Field 9: UDF2
    national_id = models.CharField(max_length=8, blank=True)       # Field 10: UDF3
    cost_center = models.CharField(max_length=50, blank=True)      # Field 14: Cost Centre

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sequence_number']
        unique_together = ['batch', 'sequence_number']

    def __str__(self):
        return f"{self.batch.batch_reference}-{self.sequence_number}"

    def save(self, *args, **kwargs):
        if not self.zone_id and self.scheme_id:
            self.zone = self.scheme.zone
        if not self.cost_center and self.scheme_id and self.scheme.default_cost_center:
            self.cost_center = self.scheme.default_cost_center
        super().save(*args, **kwargs)

    def clean(self):
        if not self.reference_number:
            raise ValidationError({'reference_number': 'Invoice Number is required'})
        if not self.source_reference:
            raise ValidationError({'source_reference': 'Source Reference (IFMIS) is required'})
        if not self.narration:
            raise ValidationError({'narration': 'Description/Narration is required'})


class ApprovalAuditLog(models.Model):
    ACTION_CHOICES = [
        ('SUBMITTED', 'Submitted for Finance Manager Review'),
        ('FM_REVIEWED', 'Reviewed by Finance Manager'),
        ('FM_REJECTED', 'Rejected by Finance Manager'),
        ('APPROVED', 'Approved by Director of Finance'),
        ('REJECTED', 'Rejected by Director of Finance'),
        ('EXPORTED', 'Exported to RBM'),
    ]

    batch = models.ForeignKey(EFTBatch, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='audit_logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.batch.batch_reference} - {self.action}"