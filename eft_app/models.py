"""
Models for EFT System - Python 3.14 + Django 5.0.6
Two-stage approval: Accounts → Finance Manager → Director of Finance
Updated with OBDX file type support
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, RegexValidator
from django.utils import timezone
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

    def clean(self):
        """Validate BIC codes - RBM BICs must end with 0, not W"""
        super().clean()
        if self.swift_code:
            if self.swift_code.startswith('NBMA') and self.swift_code.endswith('W'):
                raise ValidationError({
                    'swift_code': f'RBM BIC codes must end with "0", not "W". Please correct to {self.swift_code[:-1]}0'
                })


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
    """EFT Batch Header — two-stage approval workflow with OBDX file type support"""

    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING_FM', 'Pending Finance Manager'),
        ('PENDING_DIRECTOR', 'Pending Director of Finance'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('EXPORTED', 'Exported to RBM'),
    ]

    # OBDX File Type Choices
    FILE_TYPE_CHOICES = [
        ('OBDXPMN', 'Payment File - Domestic Suppliers'),
        ('OBDXFX', 'Foreign Payment File - Cross Border'),
        ('OBDXRM', 'Remittance File - Intra-account Transfers'),
        ('OBDXRP', 'Remittance with PRN - Tax Payments to MRA'),
        ('OBDXSF', 'Salary File - Employee Payments'),
    ]

    batch_name = models.CharField(max_length=100, help_text="Custom part of the OBDX filename (max 50 chars including underscores)")
    batch_reference = models.CharField(max_length=50, unique=True, blank=True)
    currency = models.CharField(max_length=3, default='MWK')
    total_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    record_count = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    file_reference = models.CharField(max_length=16, blank=True, help_text="RBM File Reference (e.g., WTC01-31.01.2023)")
    
    # OBDX File Type
    file_type = models.CharField(
        max_length=10, 
        choices=FILE_TYPE_CHOICES, 
        default='OBDXPMN',
        help_text="OBDX file type determines the prefix of the exported file"
    )

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
    remarks = models.TextField(blank=True, help_text="Director's remarks")
    rejection_reason = models.TextField(blank=True)

    generated_file = models.TextField(blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.batch_reference} - {self.batch_name}"

    def save(self, *args, **kwargs):
        # Generate batch reference if not set
        if not self.batch_reference:
            now = timezone.now()
            self.batch_reference = f"CRWB-{now.strftime('%Y%m%d-%H%M%S')}"
        
        # Generate file reference if not set
        if not self.file_reference:
            now = timezone.now()
            self.file_reference = f"CRWB-{now.strftime('%d.%m.%Y')}"
        
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

    def get_party_id(self):
        """
        Extract Party ID (first 9 digits) from debit account number.
        Priority:
        1. Batch's debit_account (if set)
        2. First transaction's debit_account (auto-detect)
        3. Fallback "000000000"
        """
        # Priority 1: Try batch's debit account first
        if self.debit_account and self.debit_account.account_number:
            account_num = self.debit_account.account_number
            if len(account_num) >= 9:
                return account_num[:9]
        
        # Priority 2: Try first transaction's debit account
        first_transaction = self.transactions.first()
        if first_transaction and first_transaction.debit_account:
            account_num = first_transaction.debit_account.account_number
            if account_num and len(account_num) >= 9:
                return account_num[:9]
        
        # Priority 3: Fallback
        return "000000000"

    def get_obdx_filename(self, extension='txt'):
        """
        Generate OBDX-compliant filename:
        Format: OBDXPMN_PARTYID_DD.MM.YYYYCustomName.ext
        Example: OBDXPMN_001300616_10.04.2026Salary_Payments.txt
        """
        prefix = self.file_type
        party_id = self.get_party_id()
        date_str = timezone.now().strftime('%d.%m.%Y')
        
        # Sanitize batch name for filename
        custom_part = self.batch_name.replace(' ', '_').replace('.', '_')[:50]
        
        filename = f"{prefix}_{party_id}_{date_str}{custom_part}"
        return f"{filename}.{extension}"


class EFTTransaction(models.Model):
    """Individual EFT Transaction — RBM Compliant (17-field body record)"""
    batch = models.ForeignKey(EFTBatch, on_delete=models.CASCADE, related_name='transactions')
    sequence_number = models.CharField(max_length=4)

    debit_account = models.ForeignKey(DebitAccount, on_delete=models.PROTECT, related_name='transactions')
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='transactions')
    scheme = models.ForeignKey(Scheme, on_delete=models.PROTECT, related_name='transactions')
    zone = models.ForeignKey(Zone, on_delete=models.PROTECT, related_name='transactions')

    amount = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(0.01)])

    # RBM Required Fields — matches exact column order in RBM spec
    narration = models.CharField(max_length=200)       # Field 16: Description
    reference_number = models.CharField(max_length=16) # Field 10: Invoice Number / Payee's Reference
    source_reference = models.CharField(max_length=18) # Field 15: Source reference (IFMIS)

    # Optional Fields
    employee_number = models.CharField(max_length=6, blank=True)   # Field 8: UDF2
    national_id = models.CharField(max_length=8, blank=True)       # Field 9: UDF3
    cost_center = models.CharField(max_length=50, blank=True)      # Field 13: Cost Centre

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