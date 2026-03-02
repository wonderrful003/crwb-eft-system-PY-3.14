from .models import EFTBatch


def pending_count(request):
    """Add pending batch counts to templates for Finance Manager and Director of Finance."""
    if not request.user.is_authenticated:
        return {'pending_count': 0, 'pending_fm_count': 0, 'pending_director_count': 0}

    groups = set(request.user.groups.values_list('name', flat=True))

    if 'Finance Manager' in groups:
        count = EFTBatch.objects.filter(status='PENDING_FM').count()
        return {
            'pending_count': count,
            'pending_fm_count': count,
            'pending_director_count': 0,
        }

    if 'Director of Finance' in groups:
        count = EFTBatch.objects.filter(status='PENDING_DIRECTOR').count()
        return {
            'pending_count': count,
            'pending_fm_count': 0,
            'pending_director_count': count,
        }

    # Legacy: keep Authorizer badge working if that group still exists
    if 'Authorizer' in groups:
        count = EFTBatch.objects.filter(status__in=['PENDING_FM', 'PENDING_DIRECTOR']).count()
        return {'pending_count': count, 'pending_fm_count': 0, 'pending_director_count': 0}

    return {'pending_count': 0, 'pending_fm_count': 0, 'pending_director_count': 0}