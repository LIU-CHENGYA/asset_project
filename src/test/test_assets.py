from fastapi.testclient import TestClient

from ..main import app
from ..routers import assets
from ..models.asset import AssetDB,Status
from datetime import date
client = TestClient(app)

## Asset	正常新增、查詢不存在的 Asset
## Asset	Employee 不能修改 Asset


### 員工可以查看自己特定的資產
def test_get_my_asset_success(client,session,employee_token):
    my_asset = AssetDB(
        name="My Laptop",
        category="IT",
        brand="Dell",
        model="XPS",
        specifications="16G",
        supplier="Dell",
        purchase_date=date(2026, 1, 1),
        purchase_price=30000.0,
        warranty_expiry=date(2028, 1, 1),
        department="IT",
        custodian_id=123,  # 關鍵：指定保管人是這位員工！
        )
    session.add(my_asset)
    session.commit()
    session.refresh(my_asset)  # 讓它取得自動產生的 asset_id (例如會是 1)

    response = client.get(f"/assets/my/{my_asset.asset_id}",headers={"Authorization":f"Bearer {employee_token}"})
    assert response.status_code == 200
    assert response.json()["name"] == "My Laptop"

### 員工找不到資產或不屬於自己的資產
def test_get_my_asset_not_found(client,employee_token):
    response = client.get("/assets/my/999",headers={"Authorization":f"Bearer {employee_token}"})
    assert response.status_code == 404
    assert response.json()["detail"] =="can't find this asset"

#-------------------------------------------------#

### 主管可以正常新增資產
def test_manager_create_asset(client,manager_token,sample_asset_data):
    response = client.post("/assets/",json=sample_asset_data,headers={"Authorization":f"Bearer {manager_token}"})
    assert response.status_code == 200
    assert response.json()["status"] == "available"

### 主管想要新增資產，但指定了不存在的員工做為資產保管者
def test_manager_create_asset_wrong_custodian(client,manager_token):
    asset_data = {
        "name":"My Laptop",
        "category":"IT",
        "brand":"Dell",
        "model":"XPS",
        "specifications":"16G",
        "supplier":"Dell",
        "purchase_date":"2026-01-01",
        "purchase_price":30000.0,
        "warranty_expiry":"2028-01-01",
        "department":"IT",
        "custodian_id":999,}  
    
    response = client.post("/assets/",json=asset_data,headers={"Authorization":f"Bearer {manager_token}"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Custodian not found"

### 主管想要新增資產，但指定了資產管理員做為資產保管者
def test_manager_create_asset_wrong_custodian_assign(client,manager_token,session):
    asset_data = {
        "name":"My Laptop",
        "category":"IT",
        "brand":"Dell",
        "model":"XPS",
        "specifications":"16G",
        "supplier":"Dell",
        "purchase_date":"2026-01-01",
        "purchase_price":30000.0,
        "warranty_expiry":"2028-01-01",
        "department":"IT",
        "custodian_id":202} 
    response = client.post("/assets/",json=asset_data,headers={"Authorization":f"Bearer {manager_token}"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Custodian must be an employee"

#-------------------------------------------------#

### 主管可以正常修改資產
def test_manager_patch_asset_success(client,manager_token,session):
    my_asset = AssetDB(
        name="My Laptop",
        category="IT",
        brand="Dell",
        model="XPS",
        specifications="16G",
        supplier="Dell",
        purchase_date=date(2026, 1, 1),
        purchase_price=30000.0,
        warranty_expiry=date(2028, 1, 1),
        department="IT",
        )
    session.add(my_asset)
    session.commit()
    session.refresh(my_asset)  # 讓它取得自動產生的 asset_id (例如會是 1)


    asset_data = {
        "name":"New pc",
        "category":"HR",
        } 
    response = client.patch(f"/assets/{my_asset.asset_id}",json=asset_data,headers={"Authorization":f"Bearer {manager_token}"})
    assert response.status_code == 200
    assert response.json()["name"] == "New pc"

### 主管想要修改資產，找不到資產的情境
def test_manager_patch_noy_found_asset(client,manager_token):
    asset_data = {
        "name":"New pc",
        "category":"HR",
        "custodian_id":123
        } 
    response = client.patch("/assets/999",json=asset_data,headers={"Authorization":f"Bearer {manager_token}"})
    assert response.status_code == 404
    assert response.json()["detail"] =="Asset not found"


### 主管想要修改資產， 但取得空的更新內容
def test_manager_patch_noy_found_update(client,manager_token,session):
    my_asset = AssetDB(
        name="My Laptop",
        category="IT",
        brand="Dell",
        model="XPS",
        specifications="16G",
        supplier="Dell",
        purchase_date=date(2026, 1, 1),
        purchase_price=30000.0,
        warranty_expiry=date(2028, 1, 1),
        department="IT",
        status=Status.RETIRED,
        custodian_id=23
        )
    session.add(my_asset)
    session.commit()
    session.refresh(my_asset)  # 讓它取得自動產生的 asset_id (例如會是 1)


    asset_data = {} 
    response = client.patch(f"/assets/{my_asset.asset_id}",json=asset_data,headers={"Authorization":f"Bearer {manager_token}"})
    assert response.status_code == 400
    assert response.json()["detail"] =="No fields provided for update"

### 主管想要修改資產，但去變更了退役或維修中的資產保管人
def test_manager_patch_asset_wrong(client,manager_token,session):
    my_asset = AssetDB(
        name="My Laptop",
        category="IT",
        brand="Dell",
        model="XPS",
        specifications="16G",
        supplier="Dell",
        purchase_date=date(2026, 1, 1),
        purchase_price=30000.0,
        warranty_expiry=date(2028, 1, 1),
        department="IT",
        status=Status.RETIRED,
        custodian_id=23
        )
    session.add(my_asset)
    session.commit()
    session.refresh(my_asset)  # 讓它取得自動產生的 asset_id (例如會是 1)


    asset_data = {
        "name":"New pc",
        "category":"HR",
        "custodian_id":123
        } 
    response = client.patch(f"/assets/{my_asset.asset_id}",json=asset_data,headers={"Authorization":f"Bearer {manager_token}"})
    assert response.status_code == 409
    assert response.json()["detail"] =="Cannot change custodian in the current asset status"

### 主管想要修改資產，試圖把非 custodian_id 的欄位清空成 null
def test_manager_patch_cannot_null_other_fields(client,manager_token,session):
    my_asset = AssetDB(
        name="My Laptop",
        category="IT",
        brand="Dell",
        model="XPS",
        specifications="16G",
        supplier="Dell",
        purchase_date=date(2026, 1, 1),
        purchase_price=30000.0,
        warranty_expiry=date(2028, 1, 1),
        department="IT",
        status=Status.RETIRED,
        custodian_id=23
        )
    session.add(my_asset)
    session.commit()
    session.refresh(my_asset)  # 讓它取得自動產生的 asset_id (例如會是 1)


    asset_data = {
        "name":None,
        } 
    response = client.patch(f"/assets/{my_asset.asset_id}",json=asset_data,headers={"Authorization":f"Bearer {manager_token}"})
    assert response.status_code == 422
    assert "cannot be null" in response.json()["detail"]