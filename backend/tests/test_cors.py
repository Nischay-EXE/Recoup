from app.main import app

def test_cors_allows_delete():
    middleware = next(m for m in app.user_middleware if getattr(m.cls, "__name__", "") == "CORSMiddleware")
    methods = middleware.kwargs["allow_methods"]
    assert "DELETE" in methods
