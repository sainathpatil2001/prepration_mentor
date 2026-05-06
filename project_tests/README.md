# Project Test Suite

This folder contains a separate, documented Django test suite for the Online Examination System.
It does not modify or depend on changes to existing application code.

## Scope Covered

- `test_models.py`: model behavior, computed fields, publish side effects, uniqueness constraints.
- `test_forms.py`: validation rules for admin test forms, question form, and support message form.
- `test_accounts_views.py`: auth utilities, OTP verification, save/unsave tests, exam submit scoring, contact flow.
- `test_support_views.py`: user/admin support workflows, feedback rules, exports, bulk delete behavior.
- `test_api_endpoints.py`: registration/login, user profile actions, exam attempt flow, support and notification API actions.
- `test_middleware_and_signals.py`: single-session enforcement middleware and login signal behavior.
- `test_urls.py`: named URL reverse smoke checks for core and API routes.

## How To Run

Run only this separate suite:

```powershell
python manage.py test project_tests
```

Run a specific module:

```powershell
python manage.py test project_tests.test_api_endpoints
```

Run with higher verbosity:

```powershell
python manage.py test project_tests --verbosity 2
```

PowerShell helper script:

```powershell
.\project_tests\run_tests.ps1
.\project_tests\run_tests.ps1 -TestLabel project_tests.test_models -VerboseOutput
```

## Notes

- Tests use Django's default `TestCase`/`APITestCase` and run against an isolated test database.
- Email in tests is routed to Django's in-memory email backend where applicable.
- The suite is intentionally isolated in this folder so you can run it independently from existing app-level tests.

