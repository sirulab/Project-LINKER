from fastapi import FastAPI, Request, Depends
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
    EmployeeTimesheet,
    Employee
)

from database import SessionLocal, engine
from unified_factory import create_full_stack_router

# 建立資料表
SQLModel.metadata.create_all(bind=engine)

app = FastAPI()

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
    model=EmployeeTimesheet,
    schema_base=EmployeeTimesheet,
    schema_create=EmployeeTimesheet,
    get_db_func=get_db,
    templates=templates
)
app.include_router(timesheet_api)
app.include_router(timesheet_web)