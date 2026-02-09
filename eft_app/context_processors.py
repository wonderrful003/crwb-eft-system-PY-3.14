from .models import EFTBatch

def pending_count(request):
    """Add pending batch count to templates for Authorizers"""
    if request.user.is_authenticated and request.user.groups.filter(name='Authorizer').exists():
        count = EFTBatch.objects.filter(status='PENDING').count()
        return {'pending_count': count}
    return {'pending_count': 0}