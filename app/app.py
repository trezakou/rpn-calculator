from fastapi import FastAPI
from app.db.sessions import create_db_and_tables
from app.routers import rpn


def create_app() -> FastAPI:
    app = FastAPI(title="RPN Calculator", docs_url="/")
    app.include_router(rpn.router)

    @app.on_event("startup")
    def on_startup():
        create_db_and_tables()

    # Generic health route to sanity check the API
    @app.get("/health")
    def sanity_check() -> str:
        return "ok"

    return app
