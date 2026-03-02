"""
permissions.py — Role definitions for CRWB EFT System.

Roles:
  System Admin       — full CRUD on reference data; no batch access
  Accounts Personnel — create/edit/submit/export their own batches
  Finance Manager    — Stage 1 reviewer (forward or reject)
  Director of Finance — Stage 2 approver (approve or reject); can export
"""
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_migrate
from django.dispatch import receiver


def create_groups_and_permissions():
    from .models import Bank, Zone, Scheme, Supplier, DebitAccount, EFTBatch

    content_types = {
        'bank':         ContentType.objects.get_for_model(Bank),
        'zone':         ContentType.objects.get_for_model(Zone),
        'scheme':       ContentType.objects.get_for_model(Scheme),
        'supplier':     ContentType.objects.get_for_model(Supplier),
        'debitaccount': ContentType.objects.get_for_model(DebitAccount),
        'eftbatch':     ContentType.objects.get_for_model(EFTBatch),
    }

    # Collect standard Django CRUD permissions
    permissions = {}
    for model_name, ct in content_types.items():
        for perm in Permission.objects.filter(content_type=ct):
            permissions[perm.codename] = perm

    # Custom permissions
    custom = [
        ('can_approve_eft',    'Can approve EFT batches (Director of Finance)'),
        ('can_export_eft',     'Can export EFT files to RBM'),
        ('can_fm_review_eft',  'Can review EFT batches as Finance Manager'),
    ]
    for codename, name in custom:
        perm, _ = Permission.objects.get_or_create(
            codename=codename,
            defaults={'name': name, 'content_type': content_types['eftbatch']}
        )
        permissions[codename] = perm

    base_view = [
        'view_bank', 'view_zone', 'view_scheme',
        'view_supplier', 'view_debitaccount',
    ]

    role_permissions = {
        # Full CRUD on all reference data; manages users via Django admin / custom UI
        'System Admin': [
            'add_bank',         'change_bank',         'delete_bank',         'view_bank',
            'add_zone',         'change_zone',         'delete_zone',         'view_zone',
            'add_scheme',       'change_scheme',       'delete_scheme',       'view_scheme',
            'add_supplier',     'change_supplier',     'delete_supplier',     'view_supplier',
            'add_debitaccount', 'change_debitaccount', 'delete_debitaccount', 'view_debitaccount',
        ],

        # Creates, edits, submits and exports batches
        'Accounts Personnel': [
            'add_eftbatch', 'change_eftbatch', 'view_eftbatch',
            'can_export_eft',
        ] + base_view,

        # Stage 1: reviews submitted batches — forwards to Director or rejects
        'Finance Manager': [
            'view_eftbatch',
            'can_fm_review_eft',
        ] + base_view,

        # Stage 2: final approval / rejection; can also download exported files
        'Director of Finance': [
            'view_eftbatch',
            'can_approve_eft',
            'can_export_eft',
        ] + base_view,
    }

    # Remove the legacy Authorizer group if it still exists
    Group.objects.filter(name='Authorizer').delete()

    for role_name, perm_codenames in role_permissions.items():
        group, _ = Group.objects.get_or_create(name=role_name)
        group.permissions.clear()
        for codename in perm_codenames:
            if codename in permissions:
                group.permissions.add(permissions[codename])


@receiver(post_migrate)
def setup_user_roles(sender, **kwargs):
    if sender.name == 'eft_app':
        create_groups_and_permissions()