from datetime import datetime, timedelta
from utils.db import db


class TempToken:
    def __init__(self, token, pk, device_name):
        self._id = token
        self.pk = pk
        self.device_name = device_name
        self.created_at = datetime.datetime.now()
        self.expiry = self.created_at + timedelta(minutes=10)

    def to_dict(self):
        return {
            "_id": self._id,
            "pk": self.pk,
            "device_name": self.device_name,
            "created_at": self.created_at.isoformat(),
            "expiry": self.expiry.isoformat(),
        }

    def insert_temp_token(self):
        """
        Inserisce la coppia token - pk nel db
        """
        temp_tokens_collection = db["temp_tokens"]
        temp_tokens_collection.insert_one(self.to_dict())

    @property
    def is_expired(self):
        return datetime.datetime.now() > self.expiry

    @staticmethod
    def delete_one(id: str):
        temp_tokens_collection = db["temp_tokens"]
        temp_tokens_collection.delete_one({"_id": id})

    @classmethod
    def from_dict(cls, data: dict):
        created_at = datetime.fromisoformat(data.get("created_at")) if isinstance(data.get("created_at"), str) else data.get("created_at")
        expiry = datetime.fromisoformat(data.get("expiry")) if isinstance(data.get("expiry"), str) else data.get("expiry")
        return cls(
            token=data["_id"],
            pk=data["pk"],
            device_name=data["device_name"],
            created_at=created_at,
            expiry=expiry
        )

    @classmethod
    def find_pk_by_id(cls, token: str) -> "TempToken | None":
        """
        Trova la coppia token - pk dato il token MongoDB per l'id.
        """
        temp_tokens_collection = db["temp_tokens"]
        data = temp_tokens_collection.find_one({"_id": token})
        return cls.from_dict(data) if data else None
