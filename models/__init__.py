from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncSession
from shortuuid import uuid

from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime, func, String

from settings import settings

# 创建异步数据库引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    # 将输出所有执行SQL的日志（默认是关闭的）
    echo=False,
    # 连接池大小（默认是5个）
    pool_size=10,
    # 允许连接池最大的连接数（默认是10个）
    max_overflow=20,
    # 获得连接超时时间（默认是30s）
    pool_timeout=10,
    # 连接回收时间（默认是-1，代表永不回收）
    pool_recycle=3600,
    # 连接前是否预检查（默认为False）
    pool_pre_ping=True,
)

# ——————————————————————————————————————————————————————————————————————————————————
# 这段代码是在造一个「异步数据库会话工厂」，名字是 AsyncSessionFactory。
# 以后你要访问数据库时，不是自己去 new 一个连接，
# 而是通过这个工厂拿一个「会话」（Session），在会话里执行查询、增删改。
# ————————————————————————————————————————————————————————————————————————————————————————

# 创建异步会话工厂
AsyncSessionFactory = sessionmaker(
    # Engine或者其子类对象（这里是AsyncEngine）
    # 决定了连接哪个数据库
    bind=engine,
    # Session类的代替（默认是Session类）
    # 创建异步会话，不是同步会话
    class_=AsyncSession,
    # 是否在查找之前执行flush操作（默认是True）
    # 在真正去数据库查之前，先把当前会话里已改、
    # 未提交的改动「刷」一下，避免你刚 add 了一条记录，紧接着 query 却查不到
    autoflush=True,
    # 是否在执行commit操作后Session就过期（默认是True）
    # 提交之后，当前会话里的对象还能继续读属性，不会因为 commit 就立刻失效。
    expire_on_commit=False
)

# 创建 Declarative Base
# 定义命名约定的Base类
class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    })


class BaseModel(Base):
    # __abstract__ = True 表示这个类是一个抽象类，不会被直接实例化，只能被继承
    __abstract__ = True

    id: Mapped[str] = mapped_column(String(100), primary_key=True, default=lambda: uuid())
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

from . import user
from . import candidate
from . import interview
from . import position