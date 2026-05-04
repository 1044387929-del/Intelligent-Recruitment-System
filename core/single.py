from threading import Lock
# 注：type是Python中的一个元类，具体作用是
class SingletonMeta(type):
    _instances = {}
    # 这是一个锁，用于保证线程安全
    # 具体来说，它是一个互斥锁，用于保证只有一个线程能够进入临界区
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]
