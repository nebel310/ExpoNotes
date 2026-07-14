import uvicorn

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from database import create_tables
from database import delete_tables
from router.auth import router as auth_router
from router.files import router as file_router
from router.boards import router as board_router
from router.board_members import router as board_member_router
from router.columns import board_columns_router, column_router
from router.cards import columns_cards_router, cards_router
from router.comments import card_comments_router, comments_router
from router.audit_log import router as audit_log_router
from router.search import router as search_router
from minio.client import s3_client




@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    # await delete_tables()
    # print('База очищена')
    
    await create_tables()
    print('База готова к работе')
    
    try:
        await s3_client.ensure_bucket()
        print(f'Бакет {s3_client.bucket_name} создан')
    except Exception as e:
        print(f'Ошибка при запуске MINIO {str(e)}')
    
    yield
    
    print('Выключение')



def custom_openapi():
    """Кастомная OpenAPI схема с настройками безопасности."""
    if app.openapi_schema:
        return app.openapi_schema
        
    openapi_schema = get_openapi(
        title="ExpoNotes - API клона Trello",
        version="1.0.0",
        description="""RESTful API для управления канбан-доской
    
**Разработчик:** Григорьев Владислав Алексеевич \n
**Контакты:** 
- Телеграм: @vlados7529
- Телефон: +7 (916) 054 44-35  
- GitHub: github.com/nebel310
- Email: vladislav75290@gmail.com

*Этот бэкенд был создан в рамкам летней практики от ВК*""",
        routes=app.routes,
    )
    
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    
    secured_paths = {
        # Auth
        ("/auth/me", "get"): [{"Bearer": []}],
        ("/auth/me", "patch"): [{"Bearer": []}],
        ("/auth/logout", "post"): [{"Bearer": []}],
        ("/auth/users", "get"): [{"Bearer": []}],
        # Files
        ("/files/", "post"): [{"Bearer": []}],
        ("/files/{file_id}", "get"): [{"Bearer": []}],
        ("/files/{file_id}/info", "get"): [{"Bearer": []}],
        ("/files/{file_id}", "delete"): [{"Bearer": []}],
        # Boards
        ("/boards/", "post"): [{"Bearer": []}],
        ("/boards/", "get"): [{"Bearer": []}],
        ("/boards/{board_id}", "get"): [{"Bearer": []}],
        ("/boards/{board_id}", "patch"): [{"Bearer": []}],
        ("/boards/{board_id}", "delete"): [{"Bearer": []}],
        # Board Members
        ("/boards/{board_id}/members/", "post"): [{"Bearer": []}],
        ("/boards/{board_id}/members/", "get"): [{"Bearer": []}],
        ("/boards/{board_id}/members/{member_id}", "patch"): [{"Bearer": []}],
        ("/boards/{board_id}/members/{member_id}", "delete"): [{"Bearer": []}],
        # Columns (board context)
        ("/boards/{board_id}/columns/", "post"): [{"Bearer": []}],
        ("/boards/{board_id}/columns/", "get"): [{"Bearer": []}],
        # Columns (direct)
        ("/columns/{column_id}", "get"): [{"Bearer": []}],
        ("/columns/{column_id}", "patch"): [{"Bearer": []}],
        ("/columns/{column_id}", "delete"): [{"Bearer": []}],
        # Cards (column context)
        ("/columns/{column_id}/cards/", "post"): [{"Bearer": []}],
        ("/columns/{column_id}/cards/", "get"): [{"Bearer": []}],
        # Cards (direct)
        ("/cards/{card_id}", "get"): [{"Bearer": []}],
        ("/cards/{card_id}", "patch"): [{"Bearer": []}],
        ("/cards/{card_id}", "delete"): [{"Bearer": []}],
        ("/cards/{card_id}/move", "post"): [{"Bearer": []}],
        # Comments (card context)
        ("/cards/{card_id}/comments/", "post"): [{"Bearer": []}],
        ("/cards/{card_id}/comments/", "get"): [{"Bearer": []}],
        # Comments (direct)
        ("/comments/{comment_id}", "get"): [{"Bearer": []}],
        ("/comments/{comment_id}", "patch"): [{"Bearer": []}],
        ("/comments/{comment_id}", "delete"): [{"Bearer": []}],
        # Search
        ("/search/cards", "get"): [{"Bearer": []}],
        # Audit
        ("/audit-log/", "get"): [{"Bearer": []}],
        ("/audit-log/{log_id}", "get"): [{"Bearer": []}],
    }
    
    for (path, method), security in secured_paths.items():
        if path in openapi_schema["paths"] and method in openapi_schema["paths"][path]:
            openapi_schema["paths"][path][method]["security"] = security
    
    app.openapi_schema = openapi_schema
    
    return app.openapi_schema



app = FastAPI(lifespan=lifespan)
app.openapi = custom_openapi



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



app.include_router(auth_router)
app.include_router(file_router)
app.include_router(board_router)
app.include_router(board_member_router)
app.include_router(board_columns_router)
app.include_router(column_router)
app.include_router(columns_cards_router)
app.include_router(cards_router)
app.include_router(card_comments_router)
app.include_router(comments_router)
app.include_router(audit_log_router)
app.include_router(search_router)



if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        reload=True,
        port=3001,
        # host="0.0.0.0"
    )