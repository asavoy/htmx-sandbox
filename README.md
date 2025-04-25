# HTMX Sandbox

A sandbox application to demonstrate various features of HTMX with FastAPI.

## Features Demonstrated

This sandbox demonstrates the following HTMX features:

1. **Inline Editing:** Click to swap to an editable form, POST to update, with error handling
2. **Out-of-Band Swaps:** Update multiple parts of a page in a single response
3. **Custom Events:** Trigger and handle custom events from the server
4. **Server-Sent Events:** Real-time notifications without WebSockets
5. **Loaders:** Show loading indicators during long-running requests

## Setup

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) for dependency management (optional)

### Installation

1. Create a virtual environment (optional):

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -e .
# or with uv
uv pip install -e .
```

## Running the App

```bash
python hello.py
```

Then access the application at http://localhost:8000

## How It's Built

- **Backend:** Python with FastAPI
- **Frontend:** HTMX + minimal Tailwind CSS
- **Templates:** Jinja2

## File Structure

- `hello.py` - Main FastAPI application
- `templates/` - Jinja2 HTML templates
- `static/` - Static assets (created on first run)