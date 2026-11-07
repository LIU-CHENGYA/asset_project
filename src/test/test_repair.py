from fastapi.testclient import TestClient

from ..main import app
from ..models.repair import RepairRequestDB,RepairRequestStatus
from ..models.asset import AssetDB,Status
from datetime import date
client = TestClient(app)


##----------- 一般員工 ---------
## 員工正常提出申請單
def test_create_repair_requests_success(session,client,employee_token):
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
        status=Status.IN_USE,
        custodian_id=123,  # 關鍵：指定保管人是這位員工！
        )
    session.add(my_asset)
    session.commit()
    session.refresh(my_asset)  # 讓它取得自動產生的 asset_id (例如會是 1)

    request_data = {
        "asset_id":my_asset.asset_id,
        "fault_description":"broken"
    }
    response = client.post("/repair-requests/",json=request_data,headers={"Authorization":f"Bearer {employee_token}"})
    assert response.status_code == 200

## 員工想提出申請單，但是該資產不存在
def test_create_repair_requests_asset_not_found(client,employee_token):
    request_data = {
        "asset_id":1234,
        "fault_description":"broken"
    }
    response = client.post("/repair-requests/",json=request_data,headers={"Authorization":f"Bearer {employee_token}"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Asset not found"


## 員工想提出申請單，但是該資產不屬於他
def test_create_repair_requests_not_own_asset(session,client,employee_token):
    some_asset = AssetDB(
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
        status=Status.IN_USE,
        custodian_id=999,  # 關鍵：指定保管人不是這位員工！
        )
    session.add(some_asset)
    session.commit()
    session.refresh(some_asset)  # 讓它取得自動產生的 asset_id (例如會是 1)

    request_data = {
        "asset_id":some_asset.asset_id,
        "fault_description":"broken"
    }
    response = client.post("/repair-requests/",json=request_data,headers={"Authorization":f"Bearer {employee_token}"})
    assert response.status_code == 403
    assert response.json()["detail"] == "You can only submit repair requests for your own assets"


## 員工想提出申請單，但是該資產不是in-use
def test_create_repair_requests_asset_not_in_use(session,client,employee_token):
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
        custodian_id=123,  
        )
    session.add(my_asset)
    session.commit()
    session.refresh(my_asset)  # 讓它取得自動產生的 asset_id (例如會是 1)

    request_data = {
        "asset_id":my_asset.asset_id,
        "fault_description":"broken"
    }
    response = client.post("/repair-requests/",json=request_data,headers={"Authorization":f"Bearer {employee_token}"})
    assert response.status_code == 400
    assert response.json()["detail"] == "only asset in-used can  repair request"

## ------- 
## 員工正常修改尚未審核的申請單
def test_update_request_success(session,client,employee_token):
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
        custodian_id=123,  
        )
    session.add(my_asset)
    session.commit()
    session.refresh(my_asset)  # 讓它取得自動產生的 asset_id (例如會是 1)
    
    my_require = RepairRequestDB(
        asset_id = my_asset.asset_id,
        requester_id = 123,
        fault_description="broken",
        status=RepairRequestStatus.UNDER_REVIEW
    )
    session.add(my_require)
    session.commit()
    session.refresh(my_require)  

    update_request_data = {
        "status":"cancelled",
        "fault_description":"don't need"
    }
    response = client.patch(f"/repair-requests/{my_require.request_id}",json=update_request_data,headers={"Authorization": f"Bearer {employee_token}"})
    assert response.status_code == 200

## 員工想修改但是把狀態設置錯誤
def test_update_request_status_wrong(session,client,employee_token):
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
        custodian_id=123,  
        )
    session.add(my_asset)
    session.commit()
    session.refresh(my_asset)  # 讓它取得自動產生的 asset_id (例如會是 1)
    
    my_require = RepairRequestDB(
        asset_id = my_asset.asset_id,
        requester_id = 123,
        fault_description="broken",
        status=RepairRequestStatus.UNDER_REVIEW
    )
    session.add(my_require)
    session.commit()
    session.refresh(my_require)  

    update_request_data = {
        "status":"approve_and_under_maintenance",
        "fault_description":"yaya"
    }
    response = client.patch(f"/repair-requests/{my_require.request_id}",json=update_request_data,headers={"Authorization": f"Bearer {employee_token}"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Employees can only cancel repair requests"

## 員工想修改但修改內容為空值
def test_update_request_null(session,client,employee_token):
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
        custodian_id=123,  
        )
    session.add(my_asset)
    session.commit()
    session.refresh(my_asset)  # 讓它取得自動產生的 asset_id (例如會是 1)
    
    my_require = RepairRequestDB(
        asset_id = my_asset.asset_id,
        requester_id = 123,
        fault_description="broken",
        status=RepairRequestStatus.UNDER_REVIEW
    )
    session.add(my_require)
    session.commit()
    session.refresh(my_require)  

    update_request_data = {}
    response = client.patch(f"/repair-requests/{my_require.request_id}",json=update_request_data,headers={"Authorization": f"Bearer {employee_token}"})
    assert response.status_code == 400
    assert response.json()["detail"] == "No fields provided for update"


#------------------
## 資產管理主管成功審核申請單
def test_manager_review_request_success(session,client,manager_token):
    employee_asset = AssetDB(
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
        status=Status.IN_USE,
        custodian_id=123,  
        )
    session.add(employee_asset)
    session.commit()
    session.refresh(employee_asset)  # 讓它取得自動產生的 asset_id (例如會是 1)

    employee_require = RepairRequestDB(
        asset_id = employee_asset.asset_id,
        requester_id = 123,
        fault_description="broken",
        status=RepairRequestStatus.UNDER_REVIEW
    )
    session.add(employee_require)
    session.commit()
    session.refresh(employee_require) 

    manager_update = {
        "status":"approve_and_under_maintenance"
    }
    response = client.patch(f"/repair-requests/{employee_require.request_id}/review",json=manager_update,headers={"Authorization": f"Bearer {manager_token}"})
    assert response.status_code == 200

## 資產管理主管想審核申請單，但傳入空的更新內容
def test_manager_review_request_null(session,client,manager_token):
    employee_asset = AssetDB(
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
        status=Status.IN_USE,
        custodian_id=123,  
        )
    session.add(employee_asset)
    session.commit()
    session.refresh(employee_asset)  # 讓它取得自動產生的 asset_id (例如會是 1)

    employee_require = RepairRequestDB(
        asset_id = employee_asset.asset_id,
        requester_id = 123,
        fault_description="broken",
        status=RepairRequestStatus.UNDER_REVIEW
    )
    session.add(employee_require)
    session.commit()
    session.refresh(employee_require) 

    manager_update = {
    }
    response = client.patch(f"/repair-requests/{employee_require.request_id}/review",json=manager_update,headers={"Authorization": f"Bearer {manager_token}"})
    assert response.status_code == 400
    assert response.json()["detail"] == "No fields provided for update"

## 資產管理主管想審核申請單，但待審核的工單只可以被核准或拒絕
def test_manager_review_request_status_wrong(session,client,manager_token):
    employee_asset = AssetDB(
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
        status=Status.IN_USE,
        custodian_id=123,  
        )
    session.add(employee_asset)
    session.commit()
    session.refresh(employee_asset)  # 讓它取得自動產生的 asset_id (例如會是 1)

    employee_require = RepairRequestDB(
        asset_id = employee_asset.asset_id,
        requester_id = 123,
        fault_description="broken",
        status=RepairRequestStatus.UNDER_REVIEW
    )
    session.add(employee_require)
    session.commit()
    session.refresh(employee_require) 

    manager_update = {
        "status":"completed"
    }
    response = client.patch(f"/repair-requests/{employee_require.request_id}/review",json=manager_update,headers={"Authorization": f"Bearer {manager_token}"})
    assert response.status_code == 400
    assert response.json()["detail"] == "A pending request can only be approved or rejected"

## 資產管理主管想審核申請單，已拒絕的工單只能補充維修說明
def test_manager_review_request_reject_wrong(session,client,manager_token):
    employee_asset = AssetDB(
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
        status=Status.UNDER_MAINTENANCE,
        custodian_id=123,  
        )
    session.add(employee_asset)
    session.commit()
    session.refresh(employee_asset)  # 讓它取得自動產生的 asset_id (例如會是 1)

    employee_require = RepairRequestDB(
        asset_id = employee_asset.asset_id,
        requester_id = 123,
        fault_description="broken",
        status=RepairRequestStatus.REJECTED
    )
    session.add(employee_require)
    session.commit()
    session.refresh(employee_require) 

    manager_update = {
        "repair_cost":123
    }
    response = client.patch(f"/repair-requests/{employee_require.request_id}/review",json=manager_update,headers={"Authorization": f"Bearer {manager_token}"})
    assert response.status_code == 400
    assert response.json()["detail"] == "A rejected request can only update repair_solution"

## 資產管理主管想審核申請單，已完成或已完成的工單不能再修改
def test_manager_review_request_finish_wrong(session,client,manager_token):
    employee_asset = AssetDB(
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
        status=Status.UNDER_MAINTENANCE,
        custodian_id=123,  
        )
    session.add(employee_asset)
    session.commit()
    session.refresh(employee_asset)  # 讓它取得自動產生的 asset_id (例如會是 1)

    employee_require = RepairRequestDB(
        asset_id = employee_asset.asset_id,
        requester_id = 123,
        fault_description="broken",
        status=RepairRequestStatus.COMPLETED
    )
    session.add(employee_require)
    session.commit()
    session.refresh(employee_require) 

    manager_update = {
        "repair_cost":123
    }
    response = client.patch(f"/repair-requests/{employee_require.request_id}/review",json=manager_update,headers={"Authorization": f"Bearer {manager_token}"})
    assert response.status_code == 400
    assert response.json()["detail"] == "This request cannot be updated in its current status"
