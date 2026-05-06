@login_required
@require_POST
def toggle_save_test(request, test_id):
    """Toggle saved status for a test"""
    try:
        test = get_object_or_404(Test, id=test_id)
        saved_test = SavedTest.objects.filter(user=request.user, test=test).first()
        
        if saved_test:
            # Already saved, so remove it
            saved_test.delete()
            is_saved = False
            message = "Test removed from saved list"
        else:
            # Not saved, so save it
            SavedTest.objects.create(user=request.user, test=test)
            is_saved = True
            message = "Test saved for later"
            
        return JsonResponse({'success': True, 'is_saved': is_saved, 'message': message})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
def saved_tests_list(request):
    """List all saved tests"""
    # Simply redirect to test_list with filter
    return redirect(f"{reverse('test_list')}?filter=saved")
