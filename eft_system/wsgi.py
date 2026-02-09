"""
WSGI config for eft_system project.

It exposes the WSGI callable as a module-level variable named ``application``.
"""

import os
import sys

# ==============================================
# LOAD DJANGO FIX BEFORE ANYTHING ELSE
# ==============================================
try:
    # Add project root to Python path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # Import and apply the Django fix
    import django_fix_final
except ImportError as e:
    print(f"⚠️  Could not load django_fix_final: {e}")
    # Try to apply a minimal fix directly
    try:
        import django.template.context
        import django.template.base
        
        def emergency_fix(self):
            """Emergency fix for context copying."""
            new_ctx = object.__new__(self.__class__)
            new_ctx.dicts = getattr(self, 'dicts', [{}])[:]
            return new_ctx
        
        django.template.context.BaseContext.__copy__ = emergency_fix
        print("✅ Applied emergency Django 5.0.6 + Python 3.14 fix")
    except Exception as fix_error:
        print(f"❌ Could not apply emergency fix: {fix_error}")

# ==============================================

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eft_system.settings')

application = get_wsgi_application()