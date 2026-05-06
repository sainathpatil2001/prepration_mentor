# Installation

Prerequisites
- Node.js >= X.Y (or backend runtime)
- Database engine (Postgres/MySQL) installed
- Docker (optional for local DB)
- Git

Environment
Create a copy of the environment file:
cp .env.example .env
Edit .env to set DB connection, JWT secret, and other required values:
- DATABASE_URL
- JWT_SECRET
- PORT
- STORAGE_BACKEND

Database
- Run migrations:
  - npm run migrate
  - or use chosen migration tool (flyway, alembic, etc.)
- Seed initial data (admin user, sample questions) if seeding script exists:
  - npm run seed

Run locally
- Install dependencies:
  - npm install
- Start development server:
  - npm run dev
- Run frontend (if separate):
  - cd frontend && npm install && npm start

Docker (optional)
- Use docker-compose.yml if present:
  - docker-compose up --build

Testing
- Run unit and integration tests:
  - npm test
- Linting and formatting:
  - npm run lint
  - npm run format
