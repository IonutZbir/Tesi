import datetime
from utils.db import db


class Device:
    def __init__(self, pk: str, device_name: str, main_device: bool = True, logged: bool = True):
        if not pk or not isinstance(pk, str):
            raise ValueError("Public key must be a non-empty string")
        if not device_name or not isinstance(device_name, str):
            raise ValueError("Device name must be a non-empty string")
        self.pk = pk
        self.device_name = device_name
        self.main_device = main_device
        self.logged = logged

    def to_dict(self):
        return {
            "pk": self.pk,
            "device_name": self.device_name,
            "main_device": self.main_device,
            "logged": self.logged,
        }


class User:
    collection = db["users"]

    def __init__(self, _id: str):
        self._id = _id
        self.devices = []
        self.created_at = datetime.datetime.now().isoformat()

    def add_device(self, dev: Device):
        self.devices.append(dev.to_dict())

    def to_dict(self):
        return {
            "_id": self._id,
            "devices": self.devices,
            "created_at": self.created_at,
        }

    def insert_user(self):
        self.collection.insert_one(self.to_dict())

    def update_user_with_device(self, pk: str, device_name: str):
        device = Device(pk, device_name, main_device=False, logged=True)
        self.add_device(device)
        self.collection.update_one(
            {"_id": self._id},
            {"$set": {"devices": self.devices}}
        )

    def update_user_loggedout(self, device_name: str):
        self.collection.update_one(
            {"_id": self._id , "devices.device_name": device_name},
            {"$set": {"devices.$.logged": False}}
        )

    def update_user_login(self, device_name: str):
        self.collection.update_one(
            {"_id": self._id, "devices.device_name": device_name},
            {"$set": {"devices.$.logged": True}}
        )

    @classmethod
    def from_dict(cls, data: dict):
        user = cls(data["_id"])
        user.devices = data.get("devices", [])
        user.created_at = data.get("created_at", datetime.datetime.now().isoformat())
        return user

    @classmethod
    def find_user_by_id(cls, id: str) -> "User | None":
        data = cls.collection.find_one({"_id": id})
        return cls.from_dict(data) if data else None
