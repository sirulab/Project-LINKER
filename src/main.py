from fastapi import FastAPI, Request, Depends, APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import SQLModel
from sqlalchemy.orm import Session
import jwt

# 核心模組引入
from models import (
    Company, Project, ContactPerson, Quote, 
    QuoteItem, Receipt, Timesheet, Employee, User
)
from database import SessionLocal, engine
from unified_factory import create_full_stack_router
from auth import (
    router as auth_router, 
    RoleChecker, 
    get_current_user, 
    get_password_hash,
    create_access_token,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

# 1. 啟動時建立資料表
SQLModel.metadata.create_all(bind=engine)

# 2. 初始化測試資料 (Database Seeding)
def init_dummy_data():
    db = SessionLocal()
    try:
        test_email = "admin@linker.com"
        existing_user = db.query(User).filter(User.email == test_email).first()
        
        if not existing_user:
            print("🚀 初次啟動：正在建立試用管理員帳號...")
            # 建立 User
            hashed_pw = get_password_hash("admin123")
            new_user = User(email=test_email, hashed_password=hashed_pw, role="admin")
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            # 建立 Employee
            new_employee = Employee(name="試用管理員", user_id=new_user.id, role="admin")
            db.add(new_employee)
            db.commit()
            print("✅ 完成：試用者帳號 admin@linker.com / admin123")
    finally:
        db.close()

init_dummy_data()

# 3. App 與 模板設定
app = FastAPI(title="Project LINKER")
app.include_router(auth_router)
templates = Jinja2Templates(directory="templates")

# 資料庫依賴
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =================================================================
# 核心路由：/ (根目錄) 與 /tester (傳送門)
# =================================================================

@app.get("/", response_class=HTMLResponse)
async def root(request: Request, db: Session = Depends(get_db)):
    """根目錄：根據登錄狀態顯示 Dashboard 或 Welcome 頁面"""
    token = request.cookies.get("access_token")
    user = None
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            user = db.query(User).filter(User.id == user_id).first()
        except:
            user = None

    if user:
        # 已登入：顯示儀表板
        return templates.TemplateResponse("index.html", {
            "request": request,
            "current_user": user,
            "active_page": "home",
            "project_count": "12",
            "pending_quotes": "5",
            "employee_count": "8"
        })
    else:
        # 未登入：顯示專案介紹頁
        return templates.TemplateResponse("welcome.html", {"request": request})

@app.get("/tester")
def tester_login(db: Session = Depends(get_db)):
    """面試官傳送門：自動登錄 admin@linker.com"""
    test_email = "admin@linker.com"
    user = db.query(User).filter(User.email == test_email).first()
    
    # 確保 admin 帳號存在
    if not user:
        hashed_pw = get_password_hash("admin123")
        user = User(email=test_email, hashed_password=hashed_pw, role="admin")
        db.add(user)
        db.commit()
        db.refresh(user)

    # 生成 Token
    access_token = create_access_token(data={"sub": user.id, "role": user.role})

    # 寫入 Cookie 並跳轉至首頁 Dashboard
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    return response

# =================================================================
# 註冊各模組 (工廠模式)
# =================================================================

# 定義通用權限：Admin 與 Staff 可增改，僅 Admin 可刪
common_perms = {
    "create_roles": ["admin", "staff"],
    "update_roles": ["admin", "staff"],
    "delete_roles": ["admin"]
}

# 1. companys
c_api, c_web = create_full_stack_router(path_name="companys", model=Company, schema_base=Company, schema_create=Company, get_db_func=get_db, templates=templates, **common_perms)
app.include_router(c_api)
app.include_router(c_web)

# 2. projects
p_api, p_web = create_full_stack_router(path_name="projects", model=Project, schema_base=Project, schema_create=Project, get_db_func=get_db, templates=templates, **common_perms)
app.include_router(p_api)
app.include_router(p_web)

# 3. contact_persons
cp_api, cp_web = create_full_stack_router(path_name="contact_persons", model=ContactPerson, schema_base=ContactPerson, schema_create=ContactPerson, get_db_func=get_db, templates=templates, **common_perms)
app.include_router(cp_api)
app.include_router(cp_web)

# 4. quotes
q_api, q_web = create_full_stack_router(path_name="quotes", model=Quote, schema_base=Quote, schema_create=Quote, get_db_func=get_db, templates=templates, **common_perms)
app.include_router(q_api)
app.include_router(q_web)

# 5. quoteitems
qi_api, qi_web = create_full_stack_router(path_name="quoteitems", model=QuoteItem, schema_base=QuoteItem, schema_create=QuoteItem, get_db_func=get_db, templates=templates, **common_perms)
app.include_router(qi_api)
app.include_router(qi_web)

# 6. receipts
r_api, r_web = create_full_stack_router(path_name="receipts", model=Receipt, schema_base=Receipt, schema_create=Receipt, get_db_func=get_db, templates=templates, **common_perms)
app.include_router(r_api)
app.include_router(r_web)

# 7. employees (全 admin 權限)
e_api, e_web = create_full_stack_router(path_name="employees", model=Employee, schema_base=Employee, schema_create=Employee, get_db_func=get_db, templates=templates, create_roles=["admin"], update_roles=["admin"], delete_roles=["admin"])
app.include_router(e_api)
app.include_router(e_web)

# 8. timesheets
t_api, t_web = create_full_stack_router(path_name="timesheets", model=Timesheet, schema_base=Timesheet, schema_create=Timesheet, get_db_func=get_db, templates=templates, **common_perms)
app.include_router(t_api)
app.include_router(t_web)

# =================================================================
# 全域 HTTPException 處理 (HTMX 與 瀏覽器跳轉)
# =================================================================
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    is_htmx = request.headers.get("hx-request") == "true"
    
    # 處理 403 權限不足
    if exc.status_code == 403:
        if is_htmx:
            error_html = f"""
            <div class="alert alert-danger alert-dismissible fade show shadow-sm" role="alert">
                <i class="fas fa-exclamation-triangle me-2"></i>
                <strong>操作失敗：</strong> {exc.detail}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
            """
            return HTMLResponse(content=error_html, status_code=403)
        return templates.TemplateResponse("errors/403.html", {"request": request}, status_code=403)

    # 處理 401 未登錄
    if exc.status_code == 401:
        if is_htmx:
            return HTMLResponse(content="", status_code=401, headers={"HX-Redirect": "/"})
        return RedirectResponse(url="/", status_code=303)

    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})