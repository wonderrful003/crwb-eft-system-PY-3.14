"""
Final minimal fix for Django 5.0.6 + Python 3.14
Only fixes the essential __copy__ method issue
"""
import django.template.context
import django.template.base

# Simple flag to prevent double application
if not hasattr(django.template.context.BaseContext, '__314_fixed'):
    print("🔧 Applying minimal Django 5.0.6 + Python 3.14 fix")
    
    # Store original for reference
    _original_copy = django.template.context.BaseContext.__copy__
    
    def simple_fixed_copy(self):
        """
        Minimal fix for context copying in Python 3.14.
        Avoids using super().__copy__() which fails.
        """
        # Create new instance
        new_instance = object.__new__(self.__class__)
        
        # Copy dicts
        new_instance.dicts = getattr(self, 'dicts', [{}])[:]
        
        # Copy other attributes
        for attr in ['_mutate', 'render_context', 'request', 'template']:
            if hasattr(self, attr):
                try:
                    setattr(new_instance, attr, getattr(self, attr))
                except:
                    pass
        
        return new_instance
    
    # Apply to all context classes
    django.template.context.BaseContext.__copy__ = simple_fixed_copy
    
    # Mark as fixed
    django.template.context.BaseContext.__314_fixed = True
    
    # Also ensure Template._render adds template attribute
    if not hasattr(django.template.base.Template, '__314_fixed'):
        _orig_render = django.template.base.Template._render
        
        def ensure_template(self, context):
            """Make sure context has template attribute."""
            if not hasattr(context, 'template'):
                context.template = self
            return _orig_render(self, context)
        
        django.template.base.Template._render = ensure_template
        django.template.base.Template.__314_fixed = True
    
    print("✅ Fix applied")