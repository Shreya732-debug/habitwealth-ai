# API Contract — Personal Finance GenAI Agent
# This file defines every endpoint before we build them.
# Think of it as the blueprint for the entire backend.

## Base URL
Development:  http://localhost:8000
Production:   https://your-app.onrender.com

## Authentication
All routes except /health and /auth/* require:
  Header: Authorization: Bearer <supabase_jwt_token>

## Endpoints

### Health
GET    /health                  # confirm server is running

### Authentication
POST   /auth/signup             # create new account (email + password)
POST   /auth/login              # returns JWT access token

### Budget
POST   /budget/start-month      # set opening balance + savings goal for a month
GET    /budget/current          # get current month budget + computed fields

### Transactions
POST   /transactions/add        # manual expense/income entry
POST   /transactions/upload-csv # CSV bank statement upload (Day 6)
GET    /transactions            # list all transactions for current month

### Recurring Commitments
POST   /commitments/add         # add a recurring commitment (rent, Netflix, etc.)
PATCH  /commitments/:id/pay     # mark a commitment as paid this month
GET    /commitments             # list all commitments for current month

### Agent
POST   /agent/ask               # natural language question → reasoned answer