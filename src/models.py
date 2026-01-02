from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel
from datetime import datetime
import uuid

# 用於生成 UUID 字串
def generate_uuid():
    return str(uuid.uuid4())

# 手畫關聯圖、或eraser.io
# 1. companys

class Company(SQLModel, table=True):
    __tablename__ = "companys"
    
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    name: str = Field(index=True)
    tax_id: Optional[str] = Field(default=None, index=True) 
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    
    projects: List["Project"] = Relationship(back_populates="company")
    contacts: List["ContactPerson"] = Relationship(back_populates="company")


# 2. contact_persons

class ContactPerson(SQLModel, table=True):
    __tablename__ = "contact_persons"

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    birthday: Optional[str] = None 
    
    project_id: Optional[str] = Field(default=None, foreign_key="projects.id")
    company_id: Optional[str] = Field(default=None, foreign_key="companys.id")
    
    project: Optional["Project"] = Relationship(back_populates="contacts") # Python 的讀取順序 (NameError)，Optional["   "]
    company: Optional["Company"] = Relationship(back_populates="contacts")


# 3. projects

class Project(SQLModel, table=True):
    __tablename__ = "projects"

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    status: str = Field(default="active") 
    start_date: datetime = Field(default_factory=datetime.now)
    
    company_id: Optional[str] = Field(default=None, foreign_key="companys.id")
    
    company: Optional["Company"] = Relationship(back_populates="projects")
    quotes: List["Quote"] = Relationship(back_populates="project")
    contacts: List["ContactPerson"] = Relationship(back_populates="project")


# 4. quotes

class Quote(SQLModel, table=True):
    __tablename__ = "quotes"

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    quote_number: str = Field(index=True) 
    status: str = Field(default="draft") 
    total_amount: float = Field(default=0.0)
    valid_until: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)

    project_id: str = Field(foreign_key="projects.id")

    project: Optional["Project"] = Relationship(back_populates="quotes")
    quoteitems: List["QuoteItem"] = Relationship(back_populates="quote")
    receipts: List["Receipt"] = Relationship(back_populates="quote")


# 5. quoteitems

class QuoteItem(SQLModel, table=True):
    __tablename__ = "quoteitems"

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    name: str
    description: Optional[str] = None
    quantity: float = Field(default=1.0)
    unit_price: float = Field(default=0.0)
    
    quote_id: str = Field(foreign_key="quotes.id")

    quote: Optional["Quote"] = Relationship(back_populates="quoteitems")
    timesheets: List["Timesheet"] = Relationship(back_populates="quoteitems")


# 6. receipts

class Receipt(SQLModel, table=True):
    __tablename__ = "receipts"

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    receipt_number: str
    amount: float
    payment_date: datetime = Field(default_factory=datetime.now)
    note: Optional[str] = None

    quote_id: str = Field(foreign_key="quotes.id")

    quote: Optional["Quote"] = Relationship(back_populates="receipts")


# 7. employees

class Employee(SQLModel, table=True):
    __tablename__ = "employees"

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    name: str = Field(index=True)
    email: Optional[str] = Field(default=None, index=True)
    role: Optional[str] = Field(default="staff")
    hourly_rate: float = Field(default=0.0)
    is_active: bool = Field(default=True)
    
    timesheets: List["Timesheet"] = Relationship(back_populates="employee")


# 8. timesheets

class Timesheet(SQLModel, table=True):
    __tablename__ = "timesheets"

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    hours_logged: float
    date_logged: datetime = Field(default_factory=datetime.now)
    description: Optional[str] = None

    employee_id: str = Field(foreign_key="employees.id")
    quoteitem_id: Optional[str] = Field(default=None, foreign_key="quoteitems.id")
    
    employee: Optional["Employee"] = Relationship(back_populates="timesheets")
    quoteitems: Optional["QuoteItem"] = Relationship(back_populates="timesheets") 