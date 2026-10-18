from typing import Any, List, Sequence

from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.templating import _TemplateResponse
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from models import Post
from schemas import PostCreate, PostResponse, UserCreate, UserResponse

from typing import Annotated
from sqlalchemy import select
from sqlalchemy.orm import Session
import models
from database import Base, engine, get_db

Base.metadata.create_all(bind=engine)


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")
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

# TEMPLATES
@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
def home(request: Request, db: Annotated[Session, Depends(get_db)]) -> _TemplateResponse:
    result = db.execute(
        select(models.Post)
    )
    posts = result.scalars().all()

    return templates.TemplateResponse(request,
                                      "home.html",
                                      {"posts": posts,
                                       "title": "Home"})

@app.get("/posts/{post_id}", include_in_schema=False)
def post_page(request: Request, post_id: int, db: Annotated[Session, Depends(get_db)]) -> _TemplateResponse:
    result = db.execute(
        select(models.Post).where(models.Post.id == post_id),
    )
    post = result.scalars().first()
    if post:
        title = post.title[:50]
        return templates.TemplateResponse(request,
                                            "post.html",
                                            {"post": post, "title": title}
                                            )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts")
def user_posts_page(request: Request,user_id: int,db: Annotated[Session, Depends(get_db)]):
    result = db.execute(
        select(models.User).where(models.User.id == user_id)
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    result = db.execute(
        select(models.Post).where(models.Post.user_id == user.id)
    )
    posts = result.scalars().all()
    return templates.TemplateResponse(request,
                                      "user_posts.html",
                                      {"posts": posts,"user": user, "title":f"{user.username}'s Posts"})

# API CALLS
@app.post(
    "/api/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(user: UserCreate, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(
        select(models.User).where(models.User.username == user.username),
    )
    existing_user = result.scalar().first
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists",
        )

    result = db.execute(
        select(models.User).where(models.User.email == user.email),
    )
    existing_user = result.scalar().first
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        )
    new_user = models.User(
        username=user.username,
        email=user.email,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

@app.get("/api/users/{user_id}", response_model=PostResponse)
def get_user(user_id: int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(
        select(models.User).where(models.User.id == user_id),
    )
    user = result.scalar().first()

    if user:
        return user
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found",
    )

@app.get("api/users/{user_id}/posts", response_model=List[PostResponse])
def get_user_posts(user_id: int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(
        select(models.User).where(models.User.id == user_id),
    )
    user = result.scalar().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    result = db.execute(
        select(models.Post).where(models.Post.user_id == user.id),
    )
    posts = result.scalars().all()
    return posts

@app.get("/api/posts", response_model = list[PostResponse])
def get_posts(db: Annotated[Session, Depends(get_db)]):
    results = db.execute(
        select(models.Post)
    )
    posts = results.scalars().all()
    return posts

@app.post("api/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(post: PostCreate, db: Annotated[Session, Depends(get_db)]):
    results = db.execute(
        select(models.User).where(models.User.id == post.user_id),
    )
    user = results.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    new_post = models.Post(
        title=post.title,
        content=post.content,
        user_id=user.id,
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post


@app.get("/api/posts/{post_id}",response_model=PostResponse)
def get_post(post_id: int, db: Annotated[Session, Depends(get_db)]):
    results = db.execute(
        select(models.Post).where(models.Post.id == post_id),
    )
    post = results.scalars().first()

    if post:
        return post
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


# EXCEPTIONS HANDLESR
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