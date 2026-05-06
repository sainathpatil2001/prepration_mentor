# API Reference

Auth
- POST /api/auth/login
  - body: { "email": "...", "password": "..." }
  - returns: { "token": "JWT", "user": { id, role, name } }
- POST /api/auth/register (if enabled)

Users
- GET /api/users/:id
- POST /api/users
- PUT /api/users/:id

Exams
- GET /api/exams
- GET /api/exams/:id
- POST /api/exams
  - body: { title, duration, questions: [ids], settings: {...} }
- PUT /api/exams/:id
- DELETE /api/exams/:id

Submissions
- POST /api/exams/:id/submissions
  - body: { answers: [...] }
- GET /api/submissions/:id
- GET /api/exams/:id/submissions (instructor)

Results
- GET /api/results/:submissionId
- GET /api/users/:userId/results

Examples (curl)
- Login
  curl -X POST https://.../api/auth/login -d '{"email":"x","password":"y"}' -H "Content-Type: application/json"

Notes
- All endpoints require Authorization: Bearer <token> unless public
- Use pagination for list endpoints: ?page=1&limit=20
