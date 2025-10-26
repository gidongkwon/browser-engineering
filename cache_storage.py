import os
import time

def encode_key(key: str):
    return key.replace("/", "%2F")

class CacheStorage:
    cache_dir = ".cache"
    expire_posfix = "-expire"
    def save(self, key: str, data: bytes, age_seconds: int):
        encoded_key = encode_key(key)

        content_path = f"{self.cache_dir}/{encoded_key}"
        expire_path = f"{self.cache_dir}/{encoded_key}{self.expire_posfix}"
        
        if not os.path.isdir(self.cache_dir):
            os.mkdir(self.cache_dir)
        with open(content_path, "wb") as content_file:
            content_file.write(data)
        with open(expire_path, "w") as expire_file:
            expire_file.write(str(int(time.time()) + age_seconds))
            
    def load(self, key: str):
        encoded_key = encode_key(key)

        content_path = f"{self.cache_dir}/{encoded_key}"
        expire_path = f"{self.cache_dir}/{encoded_key}{self.expire_posfix}"

        if not os.path.exists(content_path) or not os.path.exists(expire_path):
            return None
        with open(expire_path, "r") as expire_file:
            expiration = int(expire_file.readline())
            if time.time() > expiration:
                os.remove(content_path)
                os.remove(expire_path)
                return None
        with open(content_path, "rb") as file:
            return file.read()
        
cache_storage = CacheStorage()