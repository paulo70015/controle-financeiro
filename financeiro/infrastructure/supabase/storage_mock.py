"""
Mock para storage3 - não usamos funcionalidade de storage
"""

class StorageClientMock:
    def __init__(self, *args, **kwargs):
        pass
    
    def from_(self, bucket):
        return self
    
    def upload(self, *args, **kwargs):
        raise NotImplementedError("Storage não implementado")
    
    def download(self, *args, **kwargs):
        raise NotImplementedError("Storage não implementado")
