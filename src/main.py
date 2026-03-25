from fastapi import FastAPI, Request, Depends, APIRouter, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import SQLModel

from models import (
    Company, 
    Project, 
    ContactPerson,
    Quote, 
    QuoteItem, 
    Receipt, 
    Timesheet,
    Employee,
    User
)

from database import SessionLocal, engine
from unified_factory import create_full_stack_router
from auth import router as auth_router, RoleChecker, get_current_user

# 建立資料表
SQLModel.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(auth_router)

templates = Jinja2Templates(directory="templates")

# 資料庫依賴
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# index.html
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "active_page": "home",
        "project_count": "-", 
        "pending_quotes": "-",
        "employee_count": "-"
    })

# =================================================================
# 註冊API + Web (工廠模式)
# =================================================================

# 1. companys 
company_api, company_web = create_full_stack_router(
    path_name="companys",
    model=Company,
    schema_base=Company,
    schema_create=Company,
    get_db_func=get_db,
    templates=templates
)
app.include_router(company_api)
app.include_router(company_web)

# 2. projects
project_api, project_web = create_full_stack_router(
    path_name="projects",
    model=Project,
    schema_base=Project,
    schema_create=Project,
    get_db_func=get_db,
    templates=templates
)
app.include_router(project_api)
app.include_router(project_web)

# 3. contact_persons
contact_api, contact_web = create_full_stack_router(
    path_name="contact_persons",
    model=ContactPerson,
    schema_base=ContactPerson,
    schema_create=ContactPerson,
    get_db_func=get_db,
    templates=templates
)
app.include_router(contact_api)
app.include_router(contact_web)

# 4. quotes
quote_api, quote_web = create_full_stack_router(
    path_name="quotes",
    model=Quote,
    schema_base=Quote,
    schema_create=Quote,
    get_db_func=get_db,
    templates=templates
)
app.include_router(quote_api)
app.include_router(quote_web)

# 5. quoteitems
quoteitem_api, quoteitem_web = create_full_stack_router(
    path_name="quoteitems",
    model=QuoteItem,
    schema_base=QuoteItem,
    schema_create=QuoteItem,
    get_db_func=get_db,
    templates=templates
)
app.include_router(quoteitem_api)
app.include_router(quoteitem_web)

# 6. receipts
receipt_api, receipt_web = create_full_stack_router(
    path_name="receipts",
    model=Receipt,
    schema_base=Receipt,
    schema_create=Receipt,
    get_db_func=get_db,
    templates=templates
)
app.include_router(receipt_api)
app.include_router(receipt_web)

# 7. employees
employee_api, employee_web = create_full_stack_router(
    path_name="employees",
    model=Employee,
    schema_base=Employee,
    schema_create=Employee,
    get_db_func=get_db,
    templates=templates
)
app.include_router(employee_api)
app.include_router(employee_web)

# 8. timesheets
timesheet_api, timesheet_web = create_full_stack_router(
    path_name="timesheets",
    model=Timesheet,
    schema_base=Timesheet,
    schema_create=Timesheet,
    get_db_func=get_db,
    templates=templates
)
app.include_router(timesheet_api)
app.include_router(timesheet_web)

# =================================================================
# 全域的 HTTPException (攔截 HTMX 權限錯誤)
# =================================================================
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    is_htmx = request.headers.get("hx-request") == "true"
    
    if is_htmx and exc.status_code == 403:
        error_html = f"""
        <div class="alert alert-danger alert-dismissible fade show shadow-sm" role="alert">
            <i class="fas fa-exclamation-triangle me-2"></i>
            <strong>操作失敗：</strong> {exc.detail}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
        """
        return HTMLResponse(content=error_html, status_code=exc.status_code)
        
    if is_htmx and exc.status_code == 401:
        headers = {"HX-Redirect": "/login"}
        return HTMLResponse(content="", status_code=exc.status_code, headers=headers)

    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})