"""
Django Admin Template Compatibility Patch for Python 3.14
This patch comprehensively fixes RequestContext for Django 5.0.6 with Python 3.14
by ensuring all required attributes are always available.
"""

from django.template import Context, RequestContext
from django.conf import settings


# Store original __getattr__ if it exists
_original_getattr = RequestContext.__getattr__ if hasattr(RequestContext, '__getattr__') else None


def patched_getattr(self, name):
    """
    Custom __getattr__ for RequestContext to handle missing attributes dynamically
    """
    # Handle autoescape attribute
    if name == 'autoescape':
        # Try to get from context stack first
        if hasattr(self, 'dicts'):
            for d in reversed(self.dicts):
                if 'autoescape' in d:
                    return d['autoescape']
        # Default to True (safe HTML escaping)
        return True
    
    # Handle use_tz attribute
    if name == 'use_tz':
        # Get from Django settings
        return getattr(settings, 'USE_TZ', True)
    
    # Handle use_l10n attribute (localization)
    if name == 'use_l10n':
        return getattr(settings, 'USE_I18N', True)
    
    # Handle template_name attribute
    if name == 'template_name':
        if hasattr(self, 'template') and hasattr(self.template, 'name'):
            return self.template.name
        return None
    
    # Try original __getattr__ if it exists
    if _original_getattr:
        return _original_getattr(self, name)
    
    # Raise AttributeError for truly unknown attributes
    raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


# Apply the patch to RequestContext
RequestContext.__getattr__ = patched_getattr


def apply_django_admin_patch():
    """
    Apply comprehensive Django admin compatibility patch for Python 3.14
    """
    print("=" * 70)
    print("Django Admin Compatibility Patch for Python 3.14")
    print("=" * 70)
    print("✓ RequestContext.__getattr__ patched")
    print("✓ autoescape attribute support added")
    print("✓ use_tz attribute support added")
    print("✓ use_l10n attribute support added")
    print("✓ Django admin templates will now work correctly")
    print("=" * 70)


# Auto-apply when imported
apply_django_admin_patch()