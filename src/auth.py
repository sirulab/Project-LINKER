import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Form, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import SessionLocal
from models import User, Employee

# 安全設定
SECRET_KEY = "your-super-secret-key"  # TODO: 建議改向 .env 讀取隨機字串
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # Token 有效時間設為一天

# 建立密碼加密器 (使用 bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

templates = Jinja2Templates(directory="templates")

# --- 密碼與 Token 工具 ---

def get_password_hash(password: str) -> str:
    """進行密碼雜湊加密"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """驗證明文密碼與雜湊值是否相符"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    """生成 JWT Access Token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# --- 依賴項目 (Dependencies) ---

def get_db():
    """資料庫 Session 依賴"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(request: Request, db: Session = Depends(get_db)):
    """從 Cookie 取得 JWT 並驗證，回傳當前登入的 User 物件"""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="尚未登入")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="無效的憑證")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="憑證無效或已過期")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="找不到此使用者")
    
    return user

# --- 認證路由 (Authentication Routes) ---

router = APIRouter(tags=["Authentication"])

@router.post("/register")
def register(
    email: str = Form(...), 
    password: str = Form(...), 
    name: str = Form(...), # 員工姓名
    db: Session = Depends(get_db)
):
    """註冊新帳號並建立對應員工資料"""
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="此 Email 已經被註冊過了")

    # 建立 User (預設角色為 staff)
    hashed_pw = get_password_hash(password)
    new_user = User(email=email, hashed_password=hashed_pw, role="staff")
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # 同步建立 Employee
    new_employee = Employee(name=name, user_id=new_user.id, role="staff")
    db.add(new_employee)
    db.commit()

    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/login")
def login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """使用者登入並發放 JWT Cookie"""
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Email 或密碼錯誤")

    access_token = create_access_token(data={"sub": user.id, "role": user.role})

    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    return response

@router.post("/logout")
def logout():
    """清除 Cookie 登出系統"""
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response

# --- 快速登入傳送門 (Tester Portal) ---

@router.get("/tester")
def tester_login(db: Session = Depends(get_db)):
    """專供面試官一鍵進入系統的傳送門"""
    test_email = "admin@linker.com"
    user = db.query(User).filter(User.email == test_email).first()
    
    # 如果資料庫沒有測試帳號，自動建立一個 Admin 級別帳號
    if not user:
        hashed_pw = get_password_hash("admin123")
        user = User(email=test_email, hashed_password=hashed_pw, role="admin")
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # 同步建立對應的員工資料
        new_employee = Employee(name="試用管理者", user_id=user.id, role="admin")
        db.add(new_employee)
        db.commit()

    access_token = create_access_token(data={"sub": user.id, "role": user.role})

    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    return response

# --- 頁面渲染 (Page Rendering) ---

@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

# --- 權限檢查器 (RBAC Checker) ---

class RoleChecker:
    """角色權限檢查器"""
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)):
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="您的權限不足，無法執行此操作"
            )
        return user