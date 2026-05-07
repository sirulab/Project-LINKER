落實 Phase 01 的商業需求，定義 MVP 的底層技術基底與資料結構。配合「AI 加速開發」的策略，在架構設計上將優先考量「清晰度」與「功能解耦」，為快速迭代建立穩固的基礎。

# 1. 技術棧選型 (Tech Stack)

採用伺服器端渲染 (SSR) 以最快速度打造出可用的 MVP：

* **後端框架：** FastAPI (具備高效能、非同步支援與自動化 OpenAPI 文件生成)。
* **資料庫 ORM：** SQLModel
* **資料庫引擎：** SQLite (初期 MVP 快速開發與單機部署)，保留未來無縫轉移至 PostgreSQL 的能力。
* **前端渲染：** Jinja2 Templates + Bootstrap 5 (適合快速打造後台管理與表單填寫介面) + HTMX (進行局部畫面替換)
* **資料驗證：** Pydantic (確保 API 輸入輸出的資料型態正確)。

---

# 2. 系統架構設計：垂直切片架構

### 2.1 架構決策理念 (Architecture Decision Record)

* **捨棄超級工廠 (Drop Unified Factory)：** 
過去為了符合 DRY 原則，常將 CRUD 抽象成共用的 Factory。
但在 AI 輔助開發的工作流中，「清晰 (Clarity)」大於「不重複 (DRY)」。
AI 能極快地生成樣板代碼，因此我們選擇讓代碼具備高度可讀性，而非將邏輯隱藏在複雜的繼承關係中。

* **依功能切片 (Feature-driven)：** 

系統不以技術分層（不分龐大的 `routers`, `services` 資料夾），而是以「業務功能 (Use Case)」作為資料夾劃分。每個功能切片擁有自己的路由、驗證邏輯與資料庫操作。

* **共用模組 (Shared Modules)：** 

只有底層基礎建設（如資料庫連線、全域中介軟體、共用的 SQLAlchemy Models）會被抽離成共用模組。

### 2.2 目錄結構藍圖 (Directory Structure Blueprint)
```text
/Project-LINKER-Turbo
├── .gitignore            
├── requirements.txt      
├── Dockerfile            
├── docker-compose.yml    
├── .env.example          
│
└── src/                  
    ├── main.py           # [系統入口]啟動 FastAPI，註冊所有 Features 的 Routers
    ├── database.py       # 共用：資料庫連線與 Session 管理
    ├── models.py         # 共用：定義 6 個 SQLAlchemy Tables
    │
    ├── static/           # [前端]
    │   ├── css/          # bootstrap.min.css, style.css
    │   └── js/           # bootstrap.bundle.min.js
    │
    ├── templates/        # [前端]
    │   ├── base.html     # 全域共用版型
    │   ├── components/   
    │   └── features/     
    │       ├── manage_projects/  # list.html, edit.html
    │       ├── manage_quotes/
    │       └── submit_timesheet/ # timesheet_form.html
    │
    ├── shared/               # 重複模塊 (DRY)
    │   ├── dependencies.py   # 例如：get_current_user, get_db_session
    │   ├── utils.py          # 例如：日期轉換工具、計算公式
    │   └── schemas.py        # 例如：共用的 ErrorResponse
    |
    └── features/         # [垂直切片]
        ├── manage_employees/
        │   ├── router.py 
        │   └── schemas.py
        │
        ├── manage_companies/
        │   ├── router.py 
        │   └── schemas.py
        │
        ├── manage_projects/
        │   ├── router.py
        │   └── schemas.py
        │
        ├── manage_quotes/
        │   ├── router.py
        │   └── schemas.py
        │
        ├── manage_tasks/
        │   ├── router.py
        │   └── schemas.py
        │
        ├── submit_timesheet/
        │   ├── router.py 
        │   ├── schemas.py
        │   └── queries.py
        │
        └── analyze_burn_rate/
            ├── router.py
            └── services.py
