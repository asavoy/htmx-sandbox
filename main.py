import uvicorn
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio
import json
import time
import datetime
from pathlib import Path

# Create the FastAPI app
app = FastAPI(title="HTMX Sandbox")

# Set up templates
Path("templates").mkdir(exist_ok=True)
templates = Jinja2Templates(directory="templates")


# Add custom filters to Jinja2 templates
def strftime(format_string):
    return datetime.datetime.now().strftime(format_string)


templates.env.filters["strftime"] = strftime

# Sample data for demonstration
users = [
    {"id": 1, "name": "John Doe", "email": "john@example.com"},
    {"id": 2, "name": "Jane Smith", "email": "jane@example.com"},
    {"id": 3, "name": "Bob Johnson", "email": "bob@example.com"},
]

# Create static directory if it doesn't exist
Path("static").mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/inline-edit", response_class=HTMLResponse)
async def inline_edit(request: Request):
    return templates.TemplateResponse(
        "inline_edit.html", {"request": request, "users": users}
    )


@app.get("/user/{user_id}", response_class=HTMLResponse)
async def get_user(request: Request, user_id: int):
    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return templates.TemplateResponse(
        "user_detail.html", {"request": request, "user": user}
    )


@app.get("/user/{user_id}/edit", response_class=HTMLResponse)
async def edit_user_form(request: Request, user_id: int):
    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return templates.TemplateResponse(
        "user_edit_form.html", {"request": request, "user": user}
    )


@app.post("/user/{user_id}/update", response_class=HTMLResponse)
async def update_user(
    request: Request, user_id: int, name: str = Form(...), email: str = Form(...)
):
    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate the email (simple validation for demo)
    if "@" not in email:
        return templates.TemplateResponse(
            "user_edit_form.html",
            {
                "request": request,
                "user": {"id": user_id, "name": name, "email": email},
                "error": "Invalid email format",
            },
        )

    # Update the user
    user["name"] = name
    user["email"] = email

    # Return both the updated user detail and notification for out-of-band swap
    response_content = templates.TemplateResponse(
        "user_detail.html", {"request": request, "user": user}
    )

    response_content.headers["HX-Trigger"] = json.dumps(
        {"showMessage": "User updated successfully"}
    )

    return response_content


@app.get("/oob-swaps", response_class=HTMLResponse)
async def oob_swaps(request: Request):
    return templates.TemplateResponse(
        "oob_swaps.html", {"request": request, "users": users}
    )


@app.get("/user/{user_id}/oob-detail", response_class=HTMLResponse)
async def user_oob_detail(request: Request, user_id: int):
    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Set up context with the user
    context = {"request": request, "user": user}

    # Create the main response
    response = templates.TemplateResponse("user_oob_detail.html", context)

    # Add out-of-band swaps
    response.headers["HX-Trigger"] = json.dumps({"incrementClicks": "1"})

    return response


@app.get("/custom-events", response_class=HTMLResponse)
async def custom_events(request: Request):
    return templates.TemplateResponse("custom_events.html", {"request": request})


@app.post("/trigger-event", response_class=HTMLResponse)
async def trigger_event(request: Request):
    response = HTMLResponse("<div>Event triggered</div>")
    response.headers["HX-Trigger"] = json.dumps(
        {
            "myCustomEvent": {
                "message": "Hello from the server!",
                "timestamp": time.time(),
            }
        }
    )
    return response


@app.get("/sse", response_class=HTMLResponse)
async def sse_page(request: Request):
    return templates.TemplateResponse("sse.html", {"request": request})


@app.get("/events")
async def event_stream():
    async def generate():
        count = 0
        # Start with the required headers for SSE
        yield "retry: 1000\n\n"

        while True:
            if count >= 10:  # Limit for the demo
                break

            count += 1
            message_data = json.dumps(
                {"message": f"Notification {count}", "timestamp": time.time()}
            )

            # Format according to SSE spec with the event name "message"
            yield f"event: message\ndata: {message_data}\n\n"

            await asyncio.sleep(2)

    response = StreamingResponse(generate(), media_type="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"  # Disable buffering for Nginx
    return response


chat_messages = []
client_queues = set()


@app.get("/sse-chat", response_class=HTMLResponse)
async def sse_chat(request: Request):
    return templates.TemplateResponse(
        "sse_chat.html", {"request": request, "rendered_messages": chat_messages}
    )


@app.post("/sse-chat/post-message")
async def sse_chat_post_message(request: Request, message: str = Form(...)):
    template = templates.get_template("sse_chat_message.html")
    rendered_message = template.render({"message": message})
    chat_messages.append(rendered_message)
    for queue in client_queues:
        queue.put_nowait(rendered_message)
    return templates.TemplateResponse("sse_chat_form.html", {"request": request})


@app.get("/sse-chat/messages")
async def sse_chat_messages(request: Request):
    queue = asyncio.Queue()
    client_queues.add(queue)

    async def generate():
        try:
            while True:
                if await request.is_disconnected():
                    break

                message = await queue.get()

                yield f"event: ChatMessageEvent\ndata: {message}\n\n"
        finally:
            client_queues.remove(queue)

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/loaders", response_class=HTMLResponse)
async def loaders(request: Request):
    return templates.TemplateResponse("loaders.html", {"request": request})


@app.get("/slow-response", response_class=HTMLResponse)
async def slow_response(request: Request):
    await asyncio.sleep(3)  # Simulate slow response
    return templates.TemplateResponse(
        "slow_response.html",
        {"request": request, "data": "This data was loaded after 3 seconds"},
    )


@app.get("/modal", response_class=HTMLResponse)
async def modal_demo(request: Request):
    return templates.TemplateResponse("modal_demo.html", {"request": request})


@app.get("/modal-form", response_class=HTMLResponse)
async def get_modal_form(request: Request):
    return templates.TemplateResponse("modal_form.html", {"request": request})


@app.post("/submit-modal", response_class=HTMLResponse)
async def submit_modal(request: Request, name: str = Form(...), email: str = Form(...)):
    # Simple validation
    if "@" not in email:
        return templates.TemplateResponse(
            "modal_form.html",
            {
                "request": request,
                "name": name,
                "email": email,
                "error": "Invalid email format",
            },
        )

    # If valid, return a response that will close the modal and update the page
    response = HTMLResponse(
        """
    <div id="result" hx-swap-oob="innerHTML">
        <div class="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
            Form submitted successfully for {name} ({email})
        </div>
    </div>
    <div id="modal-backdrop" hx-swap-oob="delete"></div>
    <div id="modal" hx-swap-oob="delete"></div>
    """.format(name=name, email=email)
    )

    return response


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
