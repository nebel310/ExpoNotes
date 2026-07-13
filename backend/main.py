import uvicorn

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from database import create_tables
from database import delete_tables
from router.auth import router as auth_router
from router.files import router as file_router
from minio.client import s3_client




@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    await delete_tables()
    print('База очищена')
    
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
        ("/auth/me", "get"): [{"Bearer": []}],
        ("/auth/me", "patch"): [{"Bearer": []}],
        ("/auth/logout", "post"): [{"Bearer": []}],
        ("/auth/users", "get"): [{"Bearer": []}],
        ("/files/", "post"): [{"Bearer": []}],
        ("/files/{file_id}", "get"): [{"Bearer": []}],
        ("/files/{file_id}/info", "get"): [{"Bearer": []}],
        ("/files/{file_id}", "delete"): [{"Bearer": []}],
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
    allow_origins=["http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




app.include_router(auth_router)
app.include_router(file_router)



if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        reload=True,
        port=3001,
        # host="0.0.0.0"
    )