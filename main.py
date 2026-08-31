from fastapi import FastAPI, Request, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.templating import _TemplateResponse
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

posts: list[dict] = [
    {
        "id": 1,
        "author": "aaa",
        "title": "aaa",
        "content": "aaa",
        "date_posted": "April 20,2025"
    },
    {
        "id": 2,
        "author": "bbb",
        "title": "bbb",
        "content": "bbb",
        "date_posted": "April 10,2025"
    }
]


@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
def home(request: Request) -> _TemplateResponse:
    return templates.TemplateResponse(request,
                                      "home.html",
                                      {"posts": posts,
                                       "title": "Home"})


@app.get("/posts/{post_id}", include_in_schema=False)
def post_page(request: Request, post_id: int) -> _TemplateResponse:
    for post in posts:
        if post.get("id") == post_id:
            title = post["title"][:50]
            return templates.TemplateResponse(request,
                                              "post.html",
                                              {"post": post, "title": title
                                               })
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


@app.get("/api/posts")
def get_posts() -> list[dict]:
    return posts

@app.exception_handler(StarletteHTTPException)
def generate_exception_handler(request: Request, exc: StarletteHTTPException):
    message = (
        exc.detail
        if exc.detail
        else "An unexpected exception occurred."
    )
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": message}
        )
    return templates.TemplateResponse(
        request,
        "error.html",
        {"status_code": exc.status_code,
         "title" : exc.status_code,
         "message": message},
        status_code=exc.status_code
        )

@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code= status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": exc.errors()}
        )
    return templates.TemplateResponse(
        request,
        "error.html",
        {"status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
         "title" : status.HTTP_422_UNPROCESSABLE_CONTENT,
         "message" : "Invalid request. Please check your input and try again."},
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT
    )