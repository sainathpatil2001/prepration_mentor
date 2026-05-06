
def _annotate_test_data(user, tests):
    """
    Annotate tests with user specific data (attempts, status, score).
    """
    # Create a list if tests is a queryset to allow setting attributes
    if hasattr(tests, 'exists'): # It's a queryset
        tests = list(tests)
        
    if not tests:
        return tests
        
    test_ids = [t.id for t in tests]
    
    # Avoid query if user is not authenticated
    if not user.is_authenticated:
        return tests

    from .models import TestAttempt
    attempts = TestAttempt.objects.filter(user=user, test_id__in=test_ids).order_by('started_at')
    
    attempt_map = {}
    for a in attempts:
        if a.test_id not in attempt_map:
            attempt_map[a.test_id] = {
                'count': 0, 
                'status': 'not_started',
                'last_score': 0,
                'last_attempt_id': 0
            }
        
        data = attempt_map[a.test_id]
        data['count'] += 1
        
        if a.status == 'in_progress':
            data['status'] = 'in_progress'
            data['last_attempt_id'] = a.id
        elif a.status == 'completed':
            # Only overwrite if not currently in progress
            if data['status'] != 'in_progress':
                data['status'] = 'completed'
                data['last_score'] = a.percentage
                data['last_attempt_id'] = a.id
                
    for test in tests:
        test.user_data = attempt_map.get(test.id)
        
    return tests
