from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import HTMLResponse
from typing import List, Any, Optional
from sqlalchemy.orm import Session
from uuid import uuid4, UUID
from datetime import datetime

from auth import get_current_user, RoleChecker
from models import User

def create_full_stack_router(
    path_name: str,        # 例如 "companys"
    model: Any,           # SQLAlchemy Model
    schema_base: Any,     # Pydantic Schema (讀取用)
    schema_create: Any,   # Pydantic Schema (創建/更新用)
    get_db_func: Any,     # 資料庫連接 Dependency
    templates: Any,       # Jinja2Templates 實例
    # 【新增】以下三個參數用來接收權限設定，預設為 None 代表不限制
    create_roles: Optional[List[str]] = None,
    update_roles: Optional[List[str]] = None,
    delete_roles: Optional[List[str]] = None
):
    # --- 內部輔助函式：資料預處理 ---
    def _process_model_data(data: dict) -> dict:
        if hasattr(model, "__table__"):
            for col in model.__table__.columns:
                col_name = col.name
                if col_name in data:
                    val = data[col_name]
                    if isinstance(val, str) and val.strip() == "":
                        if col.nullable:
                            data[col_name] = None
                            continue
                    
                    if isinstance(val, str):
                        type_str = str(col.type).lower()
                        if "float" in type_str or "numeric" in type_str or "real" in type_str:
                            try: data[col_name] = float(val)
                            except ValueError: pass 
                        elif "integer" in type_str:
                            try: data[col_name] = int(val)
                            except ValueError: pass
                        elif "datetime" in type_str or "date" in type_str:
                            try:
                                if val.endswith("Z"):
                                    val = val[:-1] + "+00:00"
                                data[col_name] = datetime.fromisoformat(val)
                            except (ValueError, AttributeError): pass
                        elif "boolean" in type_str:
                            data[col_name] = val.lower() in ("true", "1", "on", "yes")

        if hasattr(model, "__sqlmodel_relationships__"):
            for rel_name in model.__sqlmodel_relationships__:
                if rel_name in data:
                    del data[rel_name]
        return data

    # ==================================================================
    # 建立動態權限 Dependency
    # ==================================================================
    deps_create = [Depends(RoleChecker(create_roles))] if create_roles else []
    deps_update = [Depends(RoleChecker(update_roles))] if update_roles else []
    deps_delete = [Depends(RoleChecker(delete_roles))] if delete_roles else []

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
        if not item: raise HTTPException(status_code=404, detail="Not found")
        return item

    @api.post("/", response_model=schema_base, status_code=201, dependencies=deps_create)
    def create_endpoint(obj_in: schema_create, db: Session = Depends(get_db_func)):
        try:
            data = obj_in.model_dump(exclude_unset=True)
            if "id" not in data: data["id"] = str(uuid4())
            clean_data = _process_model_data(data)
            db_obj = model(**clean_data)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except Exception:
            db.rollback()
            raise HTTPException(status_code=400, detail="Create failed")

    @api.put("/{item_id}", response_model=schema_base, dependencies=deps_update)
    def update_endpoint(item_id: UUID, obj_in: schema_create, db: Session = Depends(get_db_func)):
        db_obj = get_one_endpoint(item_id, db)
        try:
            data = obj_in.model_dump(exclude_unset=True)
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

    @api.delete("/{item_id}", status_code=204, dependencies=deps_delete)
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
    # 2. Web Router (UI) - 【全部 GET 路由注入 current_user】
    # ==================================================================
    web = APIRouter(prefix=f"/ui/{path_name}", tags=[f"{path_name.capitalize()} Web"])

    @web.get("/", response_class=HTMLResponse)
    async def web_list_page(
        request: Request, 
        db: Session = Depends(get_db_func),
        current_user: User = Depends(get_current_user) # 【新增】取得登入者
    ):
        items = get_all_endpoint(db)
        return templates.TemplateResponse(
            f"{path_name}/{path_name}.html", 
            {
                "request": request, 
                f"{path_name}": items, 
                "active_page": path_name,
                "current_user": current_user # 【新增】傳給前端
            }
        )

    @web.get("/new-row", response_class=HTMLResponse)
    async def web_get_new_row(
        request: Request,
        current_user: User = Depends(get_current_user) # 【新增】
    ):
        return templates.TemplateResponse(
            f"{path_name}/{path_name}_edit.html", 
            {
                "request": request, 
                f"{path_name[:-1]}": {},
                "current_user": current_user # 【新增】
            } 
        )

    @web.post("/", response_class=HTMLResponse, dependencies=deps_create)
    async def web_create_action(
        request: Request, 
        db: Session = Depends(get_db_func),
        current_user: User = Depends(get_current_user)
    ):
        form_data = await request.form()
        try:
            clean_data = _process_model_data(dict(form_data))
            obj_in = schema_create(**clean_data)
            new_item = create_endpoint(obj_in, db)
            return templates.TemplateResponse(
                f"{path_name}/{path_name}_row.html", 
                {"request": request, f"{path_name[:-1]}": new_item, "current_user": current_user}
            )
        except HTTPException:
            return Response(status_code=400)

    @web.get("/{item_id}", response_class=HTMLResponse)
    async def web_edit_page(
        request: Request, 
        item_id: UUID, 
        db: Session = Depends(get_db_func),
        current_user: User = Depends(get_current_user) # 【新增】
    ):
        try:
            item = get_one_endpoint(item_id, db)
            is_cancelled = request.query_params.get("cancelled")
            template_name = f"{path_name}/{path_name}_edit.html" if (request.headers.get("HX-Request") and not is_cancelled) else f"{path_name}/{path_name}_row.html"
            return templates.TemplateResponse(
                template_name, 
                {"request": request, f"{path_name[:-1]}": item, "current_user": current_user}
            )
        except HTTPException:
            return Response(status_code=404)

    @web.get("/{item_id}/details", response_class=HTMLResponse)
    async def web_detail_view(
        request: Request, 
        item_id: UUID, 
        db: Session = Depends(get_db_func),
        current_user: User = Depends(get_current_user) # 【新增】
    ):
        try:
            item = get_one_endpoint(item_id, db)
            target_template = "quotes/quotes.html" if path_name == "projects" else f"{path_name}/{path_name}_detail.html"
            return templates.TemplateResponse(
                target_template,
                {"request": request, f"{path_name[:-1]}": item, "current_user": current_user}
            )
        except HTTPException:
            return Response(status_code=404)

    @web.put("/{item_id}", response_class=HTMLResponse, dependencies=deps_update)
    async def web_update_action(
        request: Request, 
        item_id: UUID, 
        db: Session = Depends(get_db_func),
        current_user: User = Depends(get_current_user)
    ):
        form_data = await request.form()
        try:
            clean_data = _process_model_data(dict(form_data))
            obj_in = schema_create(**clean_data)
            updated_item = update_endpoint(item_id, obj_in, db)
            return templates.TemplateResponse(
                f"{path_name}/{path_name}_row.html", 
                {"request": request, f"{path_name[:-1]}": updated_item, "current_user": current_user}
            )
        except HTTPException:
            return Response(status_code=400)

    @web.delete("/{item_id}", dependencies=deps_delete)
    async def web_delete_action(item_id: UUID, db: Session = Depends(get_db_func)):
        try:
            delete_endpoint(item_id, db)
            return Response(status_code=200)
        except HTTPException:
            return Response(status_code=400)

    return api, web