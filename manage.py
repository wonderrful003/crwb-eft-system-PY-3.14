#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

def main():
    """Run administrative tasks."""
    # Apply fix before setting up Django
    try:
        project_root = os.path.dirname(os.path.abspath(__file__))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        import django_fix_final
    except ImportError:
        # Try to apply fix directly
        try:
            import django.template.context
            import django.template.base
            
            def quick_fix(self):
                new_ctx = object.__new__(self.__class__)
                new_ctx.dicts = getattr(self, 'dicts', [{}])[:]
                return new_ctx
            
            django.template.context.BaseContext.__copy__ = quick_fix
            print("✅ Applied quick fix for Python 3.14")
        except:
            pass
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eft_system.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()