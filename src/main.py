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

# 檢查器實例，允許 admin 和 staff
require_admin_or_manager = RoleChecker(["admin", "staff"])

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
# 註冊API + Web
# =================================================================

# 1. companys 
# 因為unified_factory,使用規則變化companys,不使用不規則變化companies

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

# 在 API 路由中加上 Depends
@router.post("/companys/create", dependencies=[Depends(require_admin_or_manager)])
def create_company_endpoint():
    return {"message": "公司建立成功！"}


# 有登入(不在乎角色) -> get_current_user
@router.get("/companys")
def get_companys_endpoint(current_user: User = Depends(get_current_user)):
    return {"message": f"歡迎，{current_user.email}，這裡是公司列表"}

@router.get("/companys")
def view_companys_page(
    request: Request, 
    current_user: User = Depends(get_current_user) # 取得當前登入者
):
    # 顯示公司列表頁面
    companys = [] 

    # 將 current_user 傳給 Jinja 模板
    return templates.TemplateResponse(
        "companys/companys.html", 
        {
            "request": request, 
            "current_user": current_user, # 關鍵：把 user 傳到前端
            "companys": companys
        }
    )

# 刪除 API (RoleChecker)
require_admin = RoleChecker(["admin"])

@router.delete("/companys/{company_id}", dependencies=[Depends(require_admin)])
def delete_company(company_id: str):
    # 只有 admin 可以執行，staff 收到 403 錯誤
    return {"message": "刪除成功"}

# 全域的 HTTPException
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    # 檢查這個請求是不是由 HTMX 發出的
    is_htmx = request.headers.get("hx-request") == "true"
    
    # 如果是 HTMX 發出的請求，且狀態碼是 403 (權限不足)
    if is_htmx and exc.status_code == 403:
        # 回傳一段帶有 Bootstrap 樣式，且包含關閉按鈕的 HTML 警告區塊
        error_html = f"""
        <div class="alert alert-danger alert-dismissible fade show shadow-sm" role="alert">
            <i class="fas fa-exclamation-triangle me-2"></i>
            <strong>操作失敗：</strong> {exc.detail}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
        """
        # 注意：原本的 status_code (403) 原封不動地傳回去 -> HTMX 的 response-targets 擴充套件 才知道
        return HTMLResponse(content=error_html, status_code=exc.status_code)
        
    # 如果是 HTMX 但狀態碼是 401 (未登入)
    if is_htmx and exc.status_code == 401:
        headers = {"HX-Redirect": "/login"}
        return HTMLResponse(content="", status_code=exc.status_code, headers=headers)

    # 其他情況 (例如普通的瀏覽器請求，或是 404 等錯誤)，則退回原本的 JSON 處理方式
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})