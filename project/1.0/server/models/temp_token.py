from datetime import datetime, timedelta
from utils.db import db


class TempToken:
    db = db

    def __init__(self, token, pk, device_name):
        self._id = token
        self.pk = pk
        self.device_name = device_name
        self.created_at = datetime.now()
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
        temp_token_dict = self.to_dict()
        temp_tokens_collection.insert_one(temp_token_dict)


    @staticmethod
    def find_pk_by_id(self, token: str) -> dict | None:
        """
        Trova la coppia token - pk dato il token MongoDB per l'id.

        Args:
            id (str): token del dispositivo.

        Returns:
            dict | None: dizionario con i dati oppure None se non esiste.
        """
        temp_tokens_collection = db["temp_tokens"]
        return temp_tokens_collection.find_one({"_id": token})
        
