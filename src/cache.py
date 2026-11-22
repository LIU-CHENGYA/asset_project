from fastapi import Request
from fastapi_cache import FastAPICache

'''
用來幫快取貼上「名字標籤」的工具，為了防止「A 使用者看到 B 使用者的個人隱私資料」而存在的
在自動生成 Redis Key 時，強迫把「目前登入的使用者 ID」也一起塞進 Key 的名字裡！
'''


def user_specific_key_builder(func, namespace: str = "", request: Request = None, response=None,args=(), kwargs=None,):
    kwargs = kwargs or {}

    # 找出目前登入者
    current_user = next(
        (
            value
            for value in kwargs.values()
            if hasattr(value, "employee_id")
            and hasattr(value, "role")
        ),
        None,
    )

    user_id = (
        current_user.employee_id
        if current_user
        else "anonymous"
    )

    # URL path 可以區分不同 asset_id 等路徑參數
    path = request.url.path if request else ""
    query = request.url.query if request else ""

    return (
        f"{namespace}:"
        f"{func.__name__}:"
        f"user_{user_id}:"
        f"{path}:{query}"
    )