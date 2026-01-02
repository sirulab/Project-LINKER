from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import HTMLResponse
from typing import List, Any, Optional
from sqlalchemy.orm import Session
from uuid import uuid4, UUID
from datetime import datetime

def create_full_stack_router(
    path_name: str,        # 例如 "clients"
    model: Any,           # SQLAlchemy Model
    schema_base: Any,     # Pydantic Schema (讀取用)
    schema_create: Any,   # Pydantic Schema (創建/更新用)
    get_db_func: Any,     # 資料庫連接 Dependency
    templates: Any        # Jinja2Templates 實例
):

    # --- 內部輔助函式：資料預處理 ---
    # [修正] 這裡增加了對 Float, Integer, Null 以及 Date 的強健轉換
    def _process_model_data(data: dict) -> dict:
        if hasattr(model, "__table__"):
            for col in model.__table__.columns:
                col_name = col.name
                
                # 只處理存在於 data 中的欄位
                if col_name in data:
                    val = data[col_name]
                    
                    # 1. 處理空字串 (HTML Form 傳送空值時為 "")
                    # 如果該欄位在資料庫允許 NULL (nullable)，則將 "" 轉為 None
                    if isinstance(val, str) and val.strip() == "":
                        if col.nullable:
                            data[col_name] = None
                            continue
                    
                    # 2. 型別轉換 (針對字串值)
                    if isinstance(val, str):
                        type_str = str(col.type).lower()
                        
                        # 數值處理 (Float/Numeric/Real) -> 解決 total_amount='30' 錯誤
                        if "float" in type_str or "numeric" in type_str or "real" in type_str:
                            try:
                                data[col_name] = float(val)
                            except ValueError:
                                pass # 無法轉換時保留原值，讓 Pydantic 或 DB 報錯
                        
                        # 整數處理 (Integer)
                        elif "integer" in type_str:
                            try:
                                data[col_name] = int(val)
                            except ValueError:
                                pass
                        
                        # 日期時間處理 -> 解決 valid_until='2026-01-21' 錯誤
                        elif "datetime" in type_str or "date" in type_str:
                            try:
                                # 修正 ISO 格式 (HTML datetime-local 有時會缺秒數或時區)
                                if val.endswith("Z"):
                                    val = val[:-1] + "+00:00"
                                data[col_name] = datetime.fromisoformat(val)
                            except (ValueError, AttributeError):
                                pass
                        
                        # 布林值處理 (HTML Checkbox 傳送 'on', 'true', '1')
                        elif "boolean" in type_str:
                            data[col_name] = val.lower() in ("true", "1", "on", "yes")

        # 移除關聯屬性 (避免寫入 DB 時出錯)
        if hasattr(model, "__sqlmodel_relationships__"):
            for rel_name in model.__sqlmodel_relationships__:
                if rel_name in data:
                    del data[rel_name]
        return data

    # ==================================================================
    # 1. API Router (RESTful)
    # ==================================================================
    api = APIRouter(prefix=f"/api/v1/{path_name}", tags=[f"{path_name.capitalize()} API"])

    @api.get("/", response_model=List[schema_base])
    def get_all_endpoint(db: Session = Depends(get_db_func)):
        return db.query(model).all()

    @api.get("/{item_id}", response_model=schema_base)
    def get_one_endpoint(item_id: UUID, db: Session = Depends(get_db_func)):
        item = db.query(model).filter(model.id == str(item_id)).first()
        if not item:
            raise HTTPException(status_code=404, detail="Not found")
        return item

    @api.post("/", response_model=schema_base, status_code=201)
    def create_endpoint(obj_in: schema_create, db: Session = Depends(get_db_func)):
        try:
            data = obj_in.model_dump(exclude_unset=True)
            if "id" not in data:
                data["id"] = str(uuid4())
            
            # [關鍵] 在寫入 DB 前進行轉換
            clean_data = _process_model_data(data)
            
            db_obj = model(**clean_data)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except Exception:
            db.rollback()
            raise HTTPException(status_code=400, detail="Create failed")

    @api.put("/{item_id}", response_model=schema_base)
    def update_endpoint(item_id: UUID, obj_in: schema_create, db: Session = Depends(get_db_func)):
        db_obj = get_one_endpoint(item_id, db)
        
        try:
            data = obj_in.model_dump(exclude_unset=True)
            
            # [關鍵] 在更新 DB 前進行轉換
            clean_data = _process_model_data(data)

            for key, value in clean_data.items():
                if key == "id": continue
                setattr(db_obj, key, value)
            
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except Exception:
            db.rollback()
            raise HTTPException(status_code=400, detail="Update failed")

    @api.delete("/{item_id}", status_code=204)
    def delete_endpoint(item_id: UUID, db: Session = Depends(get_db_func)):
        db_obj = get_one_endpoint(item_id, db)
        try:
            db.delete(db_obj)
            db.commit()
            return Response(status_code=204)
        except Exception:
            db.rollback()
            raise HTTPException(status_code=400, detail="Delete failed")

    # ==================================================================
    # 2. Web Router (UI)
    # ==================================================================
    web = APIRouter(prefix=f"/ui/{path_name}", tags=[f"{path_name.capitalize()} Web"])

    @web.get("/", response_class=HTMLResponse)
    async def web_list_page(request: Request, db: Session = Depends(get_db_func)):
        items = get_all_endpoint(db)
        return templates.TemplateResponse(
            f"{path_name}/{path_name}.html", 
            {"request": request, f"{path_name}": items, "active_page": path_name}
        )

    @web.get("/new-row", response_class=HTMLResponse)
    async def web_get_new_row(request: Request):
        return templates.TemplateResponse(
            f"{path_name}/{path_name}_edit.html", 
            {"request": request, f"{path_name[:-1]}": {}} 
        )

    @web.post("/", response_class=HTMLResponse)
    async def web_create_action(request: Request, db: Session = Depends(get_db_func)):
        form_data = await request.form()
        try:
            # [修正] 先清理資料 (轉型) 再建立 Pydantic 物件，避免序列化警告與型別錯誤
            clean_data = _process_model_data(dict(form_data))
            obj_in = schema_create(**clean_data)
            new_item = create_endpoint(obj_in, db)
            
            return templates.TemplateResponse(
                f"{path_name}/{path_name}_row.html", 
                {"request": request, f"{path_name[:-1]}": new_item}
            )
        except HTTPException:
            return Response(status_code=400)

    @web.get("/{item_id}", response_class=HTMLResponse)
    async def web_edit_page(request: Request, item_id: UUID, db: Session = Depends(get_db_func)):
        try:
            item = get_one_endpoint(item_id, db)
            is_cancelled = request.query_params.get("cancelled")
            
            template_name = f"{path_name}/{path_name}_edit.html" if (request.headers.get("HX-Request") and not is_cancelled) else f"{path_name}/{path_name}_row.html"
            
            return templates.TemplateResponse(
                template_name, 
                {"request": request, f"{path_name[:-1]}": item}
            )
        except HTTPException:
            return Response(status_code=404)

    # [NEW] 支援 /ui/projects/{id}/details 路由，回傳專案詳情頁面 (quotes.html)
    @web.get("/{item_id}/details", response_class=HTMLResponse)
    async def web_detail_view(request: Request, item_id: UUID, db: Session = Depends(get_db_func)):
        try:
            item = get_one_endpoint(item_id, db)
            
            # 如果是 projects 路由，導向 quotes.html
            target_template = "quotes/quotes.html" if path_name == "projects" else f"{path_name}/{path_name}_detail.html"
            
            return templates.TemplateResponse(
                target_template,
                {"request": request, f"{path_name[:-1]}": item} # 回傳變數例如 "project": item
            )
        except HTTPException:
            return Response(status_code=404)

    @web.put("/{item_id}", response_class=HTMLResponse)
    async def web_update_action(request: Request, item_id: UUID, db: Session = Depends(get_db_func)):
        form_data = await request.form()
        try:
            # [修正] 先清理資料 (轉型) 再建立 Pydantic 物件，避免序列化警告與型別錯誤
            clean_data = _process_model_data(dict(form_data))
            obj_in = schema_create(**clean_data)
            updated_item = update_endpoint(item_id, obj_in, db)
            
            return templates.TemplateResponse(
                f"{path_name}/{path_name}_row.html", 
                {"request": request, f"{path_name[:-1]}": updated_item}
            )
        except HTTPException:
            return Response(status_code=400)

    @web.delete("/{item_id}")
    async def web_delete_action(item_id: UUID, db: Session = Depends(get_db_func)):
        try:
            delete_endpoint(item_id, db)
            return Response(status_code=200)
        except HTTPException:
            return Response(status_code=400)

    return api, web