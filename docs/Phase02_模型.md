本文件定義了 Project-LINKER-Turbo 專案的核心模型、資料庫實體關聯 (ERD) 以及狀態流轉邏輯。

## 1. 語言字典 (Glossary)

* **Company (客戶公司)**：客戶公司，專案的委託方。
* **Project (專案)**：系統最高層級的執行容器。
* **Quote (報價單)**：針對專案向客戶提出的報價紀錄。
* **Task (任務)**：報價單內的收費項目與執行細項，為員工填寫工時的最小單位。
* **Employee (員工)**：系統內部使用者（顧問、PM）。
* **Timesheet (工時表)**：員工針對特定任務 (Task) 所填寫的實際花費工時。

---

## 2. 角色與權限定義 (RBAC)

系統僅存在兩種核心角色，對應 `Employee.role` 欄位：

1. **`admin` (管理層 / PM)**
   - **權限**：具備全站最高權限。可建立/修改公司、專案、報價單、任務，並能查看所有員工的工時紀錄與專案財務/預算燃燒狀況。
2. **`employee` (顧問 / 執行人員)**
   - **權限**：僅能查看自己被分配到的專案與任務，並進行「填寫工時表」的操作。無法查看報價單總額與他人薪資成本。

---

## 3. 實體與資料關聯 (Entities & ERD)

以下為 SQLModel 的核心結構與關聯定義：

* **Company (客戶公司)**
  - 欄位：`id`, `name`, `tax_id`, `email`, `phone`, `address`
  - 關聯：`1` to `N` `Project`

* **Project (專案)**
  - 欄位：`id`, `name`, `description`, `status`, `start_date`
  - 關聯：`N` to `1` `Company`, `1` to `N` `Quote`

* **Quote (報價單)**
  - 欄位：`id`, `quote_number`, `status`, `total_amount`, `valid_until`, `created_at`
  - 關聯：`N` to `1` `Project`, `1` to `N` `Task`

* **Task (任務)**
  - 欄位：`id`, `name`, `description`, `quantity` (預估時數), `unit_price`, `status`
  - 關聯：`N` to `1` `Quote`, `1` to `N` `Timesheet`

* **Employee (員工)**
  - 欄位：`id`, `name`, `email`, `role` (Enum: `admin`, `employee`), `hourly_rate` (內部成本時薪), `is_active`
  - 關聯：`1` to `N` `Timesheet`

* **Timesheet (工時表)**
  - 欄位：`id`, `hours_logged`, `date_logged`, `description`
  - 關聯：`N` to `1` `Employee`, `N` to `1` `Task`

---

## 4. 狀態機與生命週期 (State Machine & Lifecycle)

為確保資料流轉正確，核心實體具備以下狀態 (Status) 與流轉限制：

### A. 報價單狀態 (Quote.status)
* `draft` (草稿)：建立時的預設狀態，可自由新增/修改/刪除關聯的 Task。
* `sent` (已發送)：報價單已發送給客戶，此時應凍結 Task 的金額與數量修改。
* `accepted` (已接受)：客戶同意報價。**觸發副作用**：該 Quote 下的 Task 正式開放讓 `employee` 填寫 Timesheet。
* `cancelled` (已取消)：專案不執行。

### B. 任務狀態 (Task.status)
* `todo` (待辦)：報價單被接受 (`accepted`) 後的預設狀態。
* `doing` (進行中)：當 `employee` 針對該 Task 提交了第一筆 Timesheet 時，系統應自動將任務轉為 `doing`。
* `done` (已完成)：員工點擊完成：轉為 `done` 時，若該 Task 完全沒有 Timesheet 紀錄，應跳出提示或自動要求填寫。

### C. 專案狀態 (Project.status)
* `active` (進行中)：預設狀態。
* `completed` (已結案)：專案執行完畢。轉為此狀態後，底下所有 Task 應禁止再新增 Timesheet。
* `archived` (已歸檔)：隱藏於日常操作視角，僅供歷史報表查詢。

---

## 5. 核心業務規則與限制 (Business Rules)

1. **工時綁定**：一筆 `Timesheet` 必須且只能綁定一位 `Employee` 與一個 `Task`。
2. **防超支警示 (Burn-rate Warning)**：當某個 Task 底下所有 Timesheet 的 `hours_logged` 總和，超過該 Task 的預估時數（`quantity`）的 80% 時，系統前端的儀表板顯示紅燈警示。
3. **軟刪除與歷史不可變性**：若員工離職，僅能將 `Employee.is_active` 設為 `False`，不可刪除該資料，以確保過去的專案利潤與 Timesheet 計算不受影響。
