class DataCache:
    _instance = None
    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = DataCache()
        return cls._instance
    
    def flush(self):
        pass

class FileList(list):
    pass
