# NutriScan AI

NutriScan AI is a production-ready food intelligence platform that combines OCR, machine learning, and nutrition analysis with a modern authentication and user management foundation.

## What is included
- OCR-based food scanning and nutrition extraction
- Health scoring and explainable AI insights
- User registration, login, logout, and session persistence
- Password reset and email verification flow
- Protected routes for dashboard, history, profile, and future AI modules
- User profile management and future-ready preference placeholders

## Authentication architecture
- Flask + Flask-Login for session management
- Flask-Bcrypt for secure password hashing
- SQLAlchemy models for users, preferences, and future health/AI profiles
- Reusable auth helpers for validation, password strength, email delivery, and Google OAuth wiring

## Project structure
- app.py: main Flask application, routes, and scanner logic
- models.py: database models for users, scan history, feedback, and auth preferences
- auth_utils.py: validation, password strength, email, and OAuth helpers
- templates/: authentication, profile, scanner, and dashboard pages
- static/: shared styles and UI assets

## Environment variables
Set the following before running locally:
- SECRET_KEY
- DATABASE_URL (optional; defaults to SQLite)
- MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM (optional; used for verification emails)
- GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI (optional; used for Google login)

## Run locally
1. Create and activate a virtual environment
2. Install dependencies: pip install -r requirements.txt
3. Start the app: python app.py
4. Open http://127.0.0.1:5000

## Notes
The existing OCR, barcode scanner, ingredient analysis, nutrition analysis, health score, product analysis, AI explanation, and alternative recommendation modules remain intact and continue to work alongside the new authentication foundation.
