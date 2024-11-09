# FastAPI Application

This is a FastAPI-based web application managed with Poetry for dependency management.

## Prerequisites

Before running the application, ensure you have the following installed:
- Python 3.8 or higher
- [Poetry](https://python-poetry.org/docs/#installation)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <project-directory>
```

2. Install dependencies using Poetry:
```bash
poetry install
```

## Running the Application

1. Activate the Poetry shell:
```bash
poetry shell
```

2. Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```

The application will be available at `http://localhost:8000`

You can access the automatic API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`