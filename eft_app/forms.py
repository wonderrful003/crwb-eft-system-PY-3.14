# eft_app/forms.py - COMPLETE FIXED VERSION
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User, Group
from .models import (
    Bank, Zone, Scheme, Supplier, DebitAccount,
    EFTBatch, EFTTransaction, ApprovalAuditLog
)

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    role = forms.ChoiceField(choices=[
        ('System Admin', 'System Admin'),
        ('Accounts Personnel', 'Accounts Personnel'),
        ('Authorizer', 'Authorizer'),
    ], widget=forms.Select(attrs={'class': 'form-control'}))
    
    # Add password fields with proper widgets
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text="Enter a strong password"
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text="Enter the same password as above"
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'role']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter username'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make help texts more user-friendly
        self.fields['username'].help_text = "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        self.fields['email'].help_text = "Enter a valid email address"
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            role = self.cleaned_data.get('role')
            if role:
                group, created = Group.objects.get_or_create(name=role)
                user.groups.add(group)
                if role == 'System Admin':
                    user.is_staff = True
                    user.save()
        return user
class UserEditForm(forms.ModelForm):
    role = forms.ChoiceField(
        choices=[
            ('', 'Select Role'),
            ('System Admin', 'System Admin'),
            ('Accounts Personnel', 'Accounts Personnel'),
            ('Authorizer', 'Authorizer'),
        ], 
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            user_groups = self.instance.groups.all()
            if user_groups.exists():
                self.fields['role'].initial = user_groups.first().name
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        if commit:
            user.save()
            
            role = self.cleaned_data.get('role')
            if role:
                user.groups.clear()
                group, created = Group.objects.get_or_create(name=role)
                user.groups.add(group)
                user.is_staff = (role == 'System Admin')
                user.save()
            elif not role and user.groups.exists():
                user.groups.clear()
        
        return user

class BankForm(forms.ModelForm):
    class Meta:
        model = Bank
        fields = ['bank_name', 'swift_code', 'is_active']
        widgets = {
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'swift_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., NBMAMWM0'}),
        }

class ZoneForm(forms.ModelForm):
    class Meta:
        model = Zone
        fields = ['zone_code', 'zone_name', 'description']
        widgets = {
            'zone_code': forms.TextInput(attrs={'class': 'form-control'}),
            'zone_name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class SchemeForm(forms.ModelForm):
    class Meta:
        model = Scheme
        fields = ['scheme_code', 'scheme_name', 'zone', 'default_cost_center', 'is_active']
        widgets = {
            'scheme_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., SCHEME001'}),
            'scheme_name': forms.TextInput(attrs={'class': 'form-control'}),
            'zone': forms.Select(attrs={'class': 'form-control'}),
            'default_cost_center': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'e.g., 03000101 Administration'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['default_cost_center'].help_text = "Default cost center for this scheme"

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = [
            'supplier_code', 'supplier_name', 'bank', 'account_number',
            'account_name', 'employee_number', 'national_id',
            'credit_reference', 'cost_center', 'source', 'is_active'
        ]
        widgets = {
            'supplier_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '7-digit vendor code'}),
            'supplier_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank': forms.Select(attrs={'class': 'form-control'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'account_name': forms.TextInput(attrs={'class': 'form-control'}),
            'employee_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional'}),
            'national_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional'}),
            'credit_reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Invoice number'}),
            'cost_center': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 03000101 Administration'}),
            'source': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Unique IFMIS reference'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['supplier_code'].help_text = "7-digit vendor code (e.g., 57819)"
        self.fields['account_name'].help_text = "Payee Details/Beneficiary Name"
        self.fields['credit_reference'].help_text = "Payees Reference/Invoice Number"
        self.fields['cost_center'].help_text = "Originating Cost/Funds Centre"
        self.fields['source'].help_text = "Unique reference number from IFMIS"

class DebitAccountForm(forms.ModelForm):
    class Meta:
        model = DebitAccount
        fields = ['account_number', 'account_name', 'description', 'is_active']
        widgets = {
            'account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 13006161244'}),
            'account_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., (ORT) MG Other Recurrent Expenditure A/C'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class EFTBatchForm(forms.ModelForm):
    class Meta:
        model = EFTBatch
        fields = ['batch_name', 'file_reference']
        widgets = {
            'batch_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Jan 2024 Suppliers'}),
            'file_reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., WTC01-31.01.2023'}),
        }

class EFTTransactionForm(forms.ModelForm):
    class Meta:
        model = EFTTransaction
        fields = [
            'debit_account', 'supplier', 'scheme', 'amount',
            'narration', 'reference_number', 'employee_number',
            'national_id', 'cost_center', 'source_reference'
        ]
        widgets = {
            'debit_account': forms.Select(attrs={'class': 'form-control'}),
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'scheme': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'narration': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Description of transaction'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Invoice Number'}),
            'employee_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional'}),
            'national_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional'}),
            'cost_center': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 03000101'}),
            'source_reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'IFMIS reference'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['supplier'].queryset = Supplier.objects.filter(is_active=True)
        self.fields['scheme'].queryset = Scheme.objects.filter(is_active=True)
        self.fields['debit_account'].queryset = DebitAccount.objects.filter(is_active=True)
        
        self.fields['reference_number'].help_text = "Payees Reference Number/Invoice Number"
        self.fields['narration'].help_text = "Description of the transaction (max 200 chars)"

class BatchApprovalForm(forms.Form):
    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label='Approval Remarks'
    )

class BatchRejectionForm(forms.Form):
    rejection_reason = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label='Rejection Reason'
    )