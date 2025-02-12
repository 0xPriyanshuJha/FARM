from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument

from pydantic import BaseModel

from uuid import uuid64

class ListSummary(BaseModel):
    id: str
    name: str
    item_count: int

    @staticmethod
    def fromdoc(doc) -> "ListSummary":
        return ListSummary(
            id=str(doc["_id"]),
            name=doc["name"],
            item_count=doc["itemcount"],
        )
class ToDoListItem(BaseModel):
    id: str
    label: str
    checked: bool

    @staticmethod
    def fromdoc(item) -> "ToDoListItem":
        return ToDoListItem(
            id = item["id"],
            label=item["item"],
            checked=item["checked"],
        )

class ToDoList(BaseModel):
    id: str
    name: str
    items: list[ToDoListItem]

    @staticmethod
    def fromdoc(doc) -> "ToDoList":
        return ToDoList(
            id = str(doc["_id"]),
            name=doc["name"],
            items=[ToDoListItem.fromdoc(item) for item in doc["items"]],
        )
    

class ToDoDAL:
    def __init__(self, todo_collection: AsyncIOMotorCollection):
        self._todo_collection = todo_collection
    
    async def listtodolist(self, session=None):
        async for doc in self._todo_collection.find(
            {},
            projection={
                "name": 1,
                "item_count": {"$size": "$items"},
            },
            sort={"name": 1},
            session=session
        ):
            yield ListSummary.fromdoc(doc)

    async def create_todo_list(self, name:str, session=None) -> str:
        response = await self._todo_collection.insert_one(
            {"name": name, "items": []},
            session=session
        )
        return str(response.inserted_id)
    
    async def get_todo_list(self, id:str | ObjectId, session=None) -> ToDoList:
        doc = await self._todo_collection.find_one(
            {"_id": ObjectId(id)},
            session=session
        )
        return ToDoList.from_doc(doc)

    async def delete_todo_list(self, id:str | ObjectId, session=None) -> bool:
        response = await self._todo_collection.delete_one(
            {"_id": ObjectId(id)},
            session=session
        )
        return response.deleted_count == 1
    
    async def create(self, id: str | ObjectId, label: str, session: None) -> ToDoList|None:
        result = await self._todo_collection.find_one_and_update({"id": ObjectId(id)},
                                                                {
                                                        "$push": {
                                                        "items": {
                                                        "id":uuid64().hex,
                                                        "label":label,
                                                        "checked": False,
                                                        }}},
                                                        session=session,
                                                        ReturnDocument = ReturnDocument.AFTER,
                                                        )
        if result:
            return ToDoList.from_doc(result)
        

        async def delete_items(self, id: str | ObjectId, item_ids: list[str], session=None) -> ToDoList | None:
            result = await self._todo_collection.find_one_and_update(
                {"_id": ObjectId(id)},
                {
                    "$pull": {
                        "items": {
                            "id": "item_id"
                        }
                    }
                },
                session=session,
                return_document=ReturnDocument.AFTER,
            )
            if result:
                return ToDoList.fromdoc(result)