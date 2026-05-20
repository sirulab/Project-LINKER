Project-LINKER 是一個輕量級的一站式工作管理系統。
借鑑了荷比盧中小企業市佔第一的 Teamleader 的核心概念，此專案旨在提供專業服務類公司一個無縫的業務轉換流程：
從建立客戶 (Company)、開立報價單 (Quote)、轉換為專案 (Project)，到最終追蹤員工的實際工時 (Timesheet)。

### 部屬網址 (Live Demo)
目前系統已部屬。打開瀏覽器前往：https://linker.sirulab.com

### 核心功能 (Core Features)

* **CRM 基礎管理**：維護客戶公司 (`Company`) 與聯絡人 (`Contact Person`) 資訊。
* **報價系統**：建立報價單 (`Quote`) 並管理報價細項 (`Quote Item`)。
* **專案追蹤**：將業務需求轉化為專案 (`Project`) 進行交付管理。
* **工時日誌**：員工 (`Employee`) 可針對特定專案填寫工時表 (`Timesheet`)，協助公司計算實際成本與剩餘預算。

### 技術棧 (Tech Stack)

* **後端**：Python 3.13+, FastAPI
* **資料庫 ORM**：SQLModel (`database.py` & `models.py`)
* **前端渲染**：Jinja2 Templates (`src/templates/`) + Bootstrap 5 (`src/static/`)
* **資料工廠**：Unified Factory (`unified_factory.py`)

### 資料表模型

本專案採用關聯式資料庫設計，核心實體的關聯如下 (詳見 `docs/diagram-models.png`)：

1. `Company` (1) --- (N) `ContactPerson`
2. `Company` (1) --- (N) `Quote`
3. `Quote` (1) --- (N) `QuoteItem`
4. `Quote` (1) --- (1 或 N) `Project`
5. `Project` (1) --- (N) `Timesheet`
6. `Employee` (1) --- (N) `Timesheet`

### 資料夾結構

```text
Project-LINKER/
├── .github/
│   └── workflows/
│       ├── ci.yml                 
│       └── cd.yml
├── docs/                          # 專案文件 (關聯式資料)
├── src/                           
│   ├── static/
│   ├── templates/
│   ├── auth.py
│   ├── database.py
│   ├── main.py
│   └── models.py
├── tests/                         
│   ├── conftest.py
│   ├── unit/
│   │   └── test_auth_logic.py
│   └── integration/
│       ├── test_auth_endpoints.py
│       └── test_business_flow.py               
├── .env                           
├── .gitignore
├── Dockerfile
├── pytest.ini                     
└── requirements.txt 
```

### 本地端開發設定

請依照以下步驟在本地環境中運行本專案：

### 1. 複製專案與建立虛擬環境

```
git clone https://github.com/sirulab/Project-LINKER.git
cd Project-LINKER
python -m venv venv

# 啟動虛擬環境 (Windows)
venv\Scripts\activate
```

### 2. 安裝依賴套件

```
pip install -r requirements.txt
```

### 3. 啟動伺服器

```
uvicorn src.main:app --reload
```
