# VisoWay API

Welcome to the backend API for the VisoWay project. This is a Django (v6.0+) and Django REST Framework application managing Countries and Visas information, including an AI integration in the admin panel to automatically generate and fill data using OpenRouter.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Local Setup](#local-setup)
- [Environment Variables](#environment-variables)
- [Project Structure](#project-structure)
- [Development Best Practices](#development-best-practices)
- [AI Admin Integration](#ai-admin-integration)

## Prerequisites

- Python 3.10+
- `pip` or another package manager (like `pipenv` or `poetry`)
- SQLite (default for development) or PostgreSQL (recommended for production)

## Local Setup

1. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   Copy the example environment variables (if any) or create a new `.env` file at the root of the `api` folder.
   ```bash
   touch .env
   ```

4. **Run Database Migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Create a Superuser (for Admin panel access):**
   ```bash
   python manage.py createsuperuser
   ```

6. **Start the Development Server:**
   ```bash
   python manage.py runserver
   ```
   The API will be available at `http://localhost:8000/`.

## Environment Variables

For the project to work properly, especially the AI features in the Django admin, you should define the following environment variables in your `.env` file:

```env
# Core Django settings (Defaults exist for dev, but override in prod)
SECRET_KEY=your_secret_key
DEBUG=True

# OpenRouter / AI Generation Settings
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=nvidia/nemotron-3-super-120b-a12b:free
OPENROUTER_TIMEOUT=120
```

## Project Structure

- **`config/`**: Main project configuration (settings, core routing, WSGI/ASGI).
- **`countries/`**: App managing country data (ISO codes, flags, featured countries).
- **`visas/`**: Core app managing visa types, roadmap steps, required documents, FAQs, and tips. Includes the `services/` directory for AI generation logic.

## Development Best Practices

### 1. Code Style and Formatting
- **PEP 8**: Follow PEP 8 guidelines for Python code.
- **Auto-formatters**: We recommend using [Black](https://github.com/psf/black) and [isort](https://pycqa.github.io/isort/) for automated code formatting.
- **Linting**: Use [Ruff](https://docs.astral.sh/ruff/) or [Flake8](https://flake8.pycqa.org/en/latest/) to enforce code quality.

### 2. Django & Architecture Patterns
- **Fat Models, Thin Views**: Keep business logic in the models, services, or managers rather than crowding the views. The `services/` pattern (e.g., `visas/services/ai_generator.py`) is encouraged for complex integrations.
- **Use Django Choices**: For fields with predefined options (like `VisaType` or `VisaDifficulty`), continue to use Django's `IntegerChoices` or `TextChoices` instead of loose strings.
- **Optimize Database Queries**: Use `select_related` and `prefetch_related` in serializers and views to prevent N+1 query problems when fetching Visas and their related countries or roadmap steps.

### 3. API Design
- **RESTful Principles**: Rely on Django REST Framework's `ModelViewSet` and routers for standard CRUD endpoints.
- **Pagination**: The API enforces pagination by default (`PageNumberPagination` with `PAGE_SIZE=20`). Maintain this standard for endpoints returning lists.
- **Validation**: Put validation logic inside DRF Serializers, not in the view layer.

### 4. Security
- **Never commit `.env` or sensitive keys** (like `OPENROUTER_API_KEY` or `SECRET_KEY`) to version control.
- Ensure `DEBUG=False` in production.
- Configure `ALLOWED_HOSTS` properly for production deployments.

## AI Admin Integration

This project uses **OpenRouter** to dynamically fetch and generate visa information directly from the Django Admin panel. 
- Ensure your `OPENROUTER_API_KEY` is set.
- The service prompts OpenRouter's LLM to generate details like Roadmap Steps, Tips, FAQs, and Required Documents.
- The integration is found in `visas/ai_admin.py` and `visas/services/ai_generator.py`. Avoid making synchronous external requests in standard client-facing views; keep them restricted to async workers or admin actions where slightly higher latency is acceptable.