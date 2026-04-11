# Alembic 空迁移与 PostgreSQL `public` 权限：一次排错记录

**日期：** 2026-04-11  
**背景：** FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL（本地 `hr_db`，应用用户 `hr_user`）。

---

## 现象

执行：

```bash
alembic revision --autogenerate -m "init model"
```

生成的版本文件里 `upgrade()` / `downgrade()` 只有 `pass`，没有任何 `op.create_table`。

后来补全配置后再跑 `--autogenerate`，又出现：

```text
psycopg.errors.InsufficientPrivilege: 对模式 public 权限不够
LINE 2: CREATE TABLE alembic_version (
```

---

## 误区（可先排除）

1. **不是**「`hr_user` 看不见表所以对比为空」：用 SQLAlchemy 反射 `public` 时，库里可以是 0 张表，而 ORM 的 `Base.metadata` 里已有 9 张表——按理 autogenerate 应生成大量建表语句，而不是整段空逻辑。

2. **`pg_database.datacl` 为空**：只表示数据库对象上没有显式 ACL 条目，不等于业务用户没有任何权限；连库、模式级权限要单独查。

3. **`\du hr_user` 属性列为空**：通常只是说明不是超级用户、没有 `CREATEDB` 等**角色级**标记，**不能**据此判断能否在 `public` 里建表。

---

## 根因一：`alembic/env.py` 不完整

`env.py` 里若只设置了 `sqlalchemy.url` 和 `target_metadata = Base.metadata`，却**没有**：

- `run_migrations_offline()` / `run_migrations_online()`
- 以及最终调用 `context.run_migrations()`

则 autogenerate **不会在正确的迁移上下文里**带着 `target_metadata` 去对比数据库，结果就会反复得到「空迁移」。

**处理：** 按 Alembic 官方模板补全上述函数，并在模块末尾根据 `context.is_offline_mode()` 调用对应入口。

---

## 根因二：`hr_user` 对模式 `public` 没有 `CREATE`

补全 `env.py` 后，Alembic 在线运行时会先确保存在 **`alembic_version` 表**，即在 `public` 下执行 `CREATE TABLE`。若当前用户对 `public` 没有 `CREATE` 权限（PostgreSQL 15+ 收紧默认权限时很常见），就会报「对模式 public 权限不够」。

**验证：**

```sql
SELECT has_schema_privilege('hr_user', 'public', 'CREATE');
-- 若为 f，则无法由该用户建表（含 alembic_version）
```

**处理（由超级用户或库所有者执行，在目标库下）：**

```sql
\c hr_db
GRANT CONNECT ON DATABASE hr_db TO hr_user;   -- 若尚未能连库再补
GRANT USAGE, CREATE ON SCHEMA public TO hr_user;
```

授权后再执行 `alembic revision --autogenerate` 或 `alembic upgrade head`。

---

## 小结

| 现象 | 更可能的原因 |
|------|----------------|
| autogenerate 生成空 `upgrade()` | `env.py` 未调用 `run_migrations_*` / `context.run_migrations()` |
| 报错无法创建 `alembic_version` | 迁移所用用户对 `public` 缺少 `CREATE`（及必要的 `USAGE`/`CONNECT`） |

**经验：** 先保证迁移环境脚本完整，再用 `has_schema_privilege` 等针对**库 / 模式 / 表**逐项核对权限；角色属性（`\du`）与对象级授权（`GRANT`）是两回事。

---

## 参考命令备忘

```bash
# 不连库、仅生成空版本（不对比数据库）
alembic revision -m "init model"

# 连库对比模型与数据库结构（需 DB 权限与完整 env）
alembic revision --autogenerate -m "init model"

alembic upgrade head
```

（本文记录本次项目中的实际排错过程，便于日后查阅。）
