# Architecture

Overview
Describe the overall system architecture: client, server, database, and optional services (auth, file storage, reporting).

Components
- Frontend: UI app for students and instructors; handles routing, form validation, and client-side state.
- Backend API: REST/GraphQL service that exposes endpoints for exams, questions, users, and results.
- Database: Stores users, questions, exams, submissions, and results.
- Worker/Jobs: Optional background workers for report generation, notifications, and heavy processing.
- Auth service: Handles login, roles (student, instructor, admin), and permissions.

Data flow (example)
1. Instructor creates an exam via frontend -> POST /api/exams
2. Student requests exam -> GET /api/exams/:id (backend verifies access/time)
3. Student submits answers -> POST /api/exams/:id/submissions (backend persists and enqueues grading)
4. Worker grades auto-gradable items and updates result -> results available at GET /api/results/:submissionId

Security considerations
- Validate all inputs and use parameterized queries
- Protect endpoints with authentication and role-based authorization
- Rate-limit sensitive endpoints (login, submission)
- Store secrets securely (env, vault)

Scaling & availability
- Horizontal scale stateless backend
- Use connection pooling for DB
- Cache static/config data (Redis)
- Offload heavy tasks to background workers
