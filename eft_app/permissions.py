from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_migrate
from django.dispatch import receiver

def create_groups_and_permissions():
    """Create user roles and assign permissions"""
    from .models import Bank, Zone, Scheme, Supplier, DebitAccount, EFTBatch
    
    # Get content types
    content_types = {
        'bank': ContentType.objects.get_for_model(Bank),
        'zone': ContentType.objects.get_for_model(Zone),
        'scheme': ContentType.objects.get_for_model(Scheme),
        'supplier': ContentType.objects.get_for_model(Supplier),
        'debitaccount': ContentType.objects.get_for_model(DebitAccount),
        'eftbatch': ContentType.objects.get_for_model(EFTBatch),
    }
    
    # Get all permissions
    permissions = {}
    for model_name, ct in content_types.items():
        model_perms = Permission.objects.filter(content_type=ct)
        for perm in model_perms:
            permissions[f'{perm.codename}'] = perm
    
    # Create custom permissions
    can_approve_eft, _ = Permission.objects.get_or_create(
        codename='can_approve_eft',
        defaults={
            'name': 'Can approve EFT batches',
            'content_type': content_types['eftbatch']
        }
    )
    
    can_export_eft, _ = Permission.objects.get_or_create(
        codename='can_export_eft',
        defaults={
            'name': 'Can export EFT files',
            'content_type': content_types['eftbatch']
        }
    )
    
    permissions['can_approve_eft'] = can_approve_eft
    permissions['can_export_eft'] = can_export_eft
    
    # Define role permissions
    role_permissions = {
        'System Admin': [
            'add_bank', 'change_bank', 'delete_bank', 'view_bank',
            'add_zone', 'change_zone', 'delete_zone', 'view_zone',
            'add_scheme', 'change_scheme', 'delete_scheme', 'view_scheme',
            'add_supplier', 'change_supplier', 'delete_supplier', 'view_supplier',
            'add_debitaccount', 'change_debitaccount', 'delete_debitaccount', 'view_debitaccount',
        ],
        'Accounts Personnel': [
            'add_eftbatch', 'change_eftbatch', 'view_eftbatch',
            'view_bank', 'view_zone', 'view_scheme', 'view_supplier', 'view_debitaccount',
            'can_export_eft',
        ],
        'Authorizer': [
            'view_eftbatch',
            'view_bank', 'view_zone', 'view_scheme', 'view_supplier', 'view_debitaccount',
            'can_approve_eft', 'can_export_eft',
        ]
    }
    
    # Create groups and assign permissions
    for role_name, perm_codenames in role_permissions.items():
        group, created = Group.objects.get_or_create(name=role_name)
        group.permissions.clear()
        
        for codename in perm_codenames:
            if codename in permissions:
                group.permissions.add(permissions[codename])

@receiver(post_migrate)
def setup_user_roles(sender, **kwargs):
    """Signal handler to setup roles after migrations"""
    if sender.name == 'eft_app':
        create_groups_and_permissions()