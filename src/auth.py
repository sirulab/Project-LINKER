# src/auth.py
import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Form, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import SessionLocal
from models import User, Employee

SECRET_KEY = "your-super-secret-key"  # TODO: 改成亂數，並存放 .env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # Token 預設有效時間一天

# 建立密碼加密器 (使用 bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

templates = Jinja2Templates(directory="src/templates")

def get_password_hash(password: str) -> str:
    # 進行雜湊加密
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # 驗證密碼
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    # 生成 JWT Token
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# 資料庫與使用者 Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(request: Request, db: Session = Depends(get_db)):
    # 從 Cookie 取得 JWT 並驗證，回傳當前 User 物件
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
    
    # 從資料庫中找出該名 User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="找不到此使用者")
    
    return user


# 註冊、登入與登出路由
router = APIRouter(tags=["Authentication"])

@router.post("/register")
def register(
    email: str = Form(...), 
    password: str = Form(...), 
    name: str = Form(...), # 建立員工的姓名
    db: Session = Depends(get_db)
):
    # 註冊新使用者，並同時建立員工
    # 1. 檢查 Email 是否已存在
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="此 Email 已經被註冊過了")

    # 2. 建立 User 紀錄
    hashed_pw = get_password_hash(password)
    new_user = User(email=email, hashed_password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # 3. 建立對應的 Employee 紀錄
    new_employee = Employee(name=name, user_id=new_user.id)
    db.add(new_employee)
    db.commit()

    # 註冊成功後，導向登入頁面 (303 狀態碼適合表單 POST 後的轉址)
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/login")
def login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # 使用者登入，成功，發放 JWT Cookie
    # 1. 尋找使用者並驗證密碼
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Email 或密碼錯誤")

    # 2. 生成 JWT Token
    access_token = create_access_token(data={"sub": user.id, "role": user.role})

    # 3. 設定 HTTP-Only Cookie，並導向首頁
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,   # TODO: 防止前端 JS 讀取，防範 XSS
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"   # 防範 CSRF
    )
    return response


@router.post("/logout")
def logout():
    # 登出 + 清除 Cookie
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response

# 前端畫面

@router.get("/login")
def login_page(request: Request):
    # 顯示登入頁面
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/register")
def register_page(request: Request):
    # 顯示註冊頁面
    return templates.TemplateResponse("register.html", {"request": request})

# RBAC 角色權限檢查器
class RoleChecker:
    def __init__(self, allowed_roles: list):
        # 允許
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)):
        # user 參數會自動呼叫 get_current_user -> 取得當前使用者
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="您的權限不足，無法執行此操作"
            )
        return user