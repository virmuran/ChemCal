# ChemCal/modules/history_db.py
"""计算历史记录 SQLite 数据库管理"""
import sqlite3
import json
import os
from datetime import datetime
from PySide6.QtCore import QObject, Signal


class HistoryDB(QObject):
    """历史记录数据库，支持单例和刷新信号"""
    record_added = Signal()     # 保存新记录后发送此信号
    records_changed = Signal()  # 删除/清空等批量变更后发送此信号

    #: 单次查询的硬上限 —— 防止某人攒了十万条记录后把界面拖死
    MAX_ROWS = 100000

    _instance = None
    _initialized = False

    # 计算器ID到中文名称的映射
    CALCULATOR_NAMES = {
        "steam_property_calculator": "水蒸气性质",
        "wet_air_calculator": "湿空气计算",
        "refrigerant_properties_calculator": "制冷剂物性",
        "pure_substance_properties": "纯物质物性查询",
        "solution_density_calculator": "溶液密度计算",
        "solid_solubility_calculator": "固体溶解度",
        "corrosion_data_query": "腐蚀查询",
        "hazardous_chemicals_query": "危险化学品",
        "gas_state_converter": "气体标态转压缩态",
        "eos_calculator": "EOS状态方程",
        "gas_mixture_properties_calculator": "气体混合物(EOS)",
        "vle_activity_coefficient_calculator": "汽液平衡(活度系数)",
        "mixed_liquid_flash_point_calculator": "混合液体闪点",
        "pipe_diameter_calculator": "管径计算",
        "pipe_thickness_calculator": "管道壁厚",
        "pipe_span_calculator": "管道跨距",
        "pipe_spacing_calculator": "管道间距",
        "pipe_compensation_calculator": "管道补偿",
        "pressure_pipe_definition": "压力管道定义",
        "pressure_drop_calculator": "压降计算",
        "compressible_flow_pressure_drop": "可压缩流体压降",
        "pump_power_calculator": "离心泵功率计算",
        "npsha_calculator": "离心泵NPSHa计算",
        "steam_pipe_calculator": "蒸汽管径流量",
        "long_distance_steam_pipe_calculator": "长输蒸汽管道温降计算",
        "heat_exchanger_calculator": "换热器计算",
        "heat_exchanger_area_calculator": "换热器面积",
        "fan_power_calculator": "风机功率计算",
        "insulation_thickness_calculator": "保温厚度计算",
        "vessel_sizing_calculator": "设备尺寸计算",
        "tank_weight_calculator": "罐体重量",
        "basket_filter_design_calculator": "篮式过滤器",
        "safety_valve_calculator": "安全阀计算",
        "relief_area_calculator": "泄压面积计算",
        "fire_hydrant_calculator": "消火栓计算",
        "refrigeration_cycle_calculator": "制冷循环计算",
        # 部分计算器使用短名称作为 calculator_id 的别名
        "wet_air": "湿空气计算",
        "compressible_flow": "可压缩流体压降",
        "relief_area": "泄压面积计算",
        "safety_valve": "安全阀计算",
        "solution_density": "溶液密度计算",
        "insulation_thickness": "保温厚度计算",
        "solid_solubility": "固体溶解度",
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()  # 初始化 QObject
        self._initialized = True

        db_dir = os.path.join(os.path.expanduser("~"), ".ChemCal", "history")
        os.makedirs(db_dir, exist_ok=True)
        self.db_path = os.path.join(db_dir, "calc_history.db")

        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS calculation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                calculator_id TEXT NOT NULL,
                calculator_name TEXT NOT NULL,
                calculator_category TEXT DEFAULT '',
                inputs TEXT NOT NULL DEFAULT '{}',
                outputs TEXT NOT NULL DEFAULT '{}',
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_calculator_id
            ON calculation_history(calculator_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_category
            ON calculation_history(calculator_category)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at
            ON calculation_history(created_at DESC)
        """)
        conn.commit()
        conn.close()

    # ── 查询条件构造 ──────────────────────────────────────────────

    @staticmethod
    def _date_params(date_from=None, date_to=None):
        """把 YYYY-MM-DD 边界转成可与 created_at(ISO 字符串) 直接比较的区间。

        created_at 存的是 ``2026-09-15T10:30:00.123456``，ISO 格式定长且高位在前，
        因此字符串比较即等价于时间比较（也能吃到 created_at 索引）。
        """
        lo = f"{str(date_from)[:10]}T00:00:00" if date_from else None
        hi = f"{str(date_to)[:10]}T23:59:59.999999" if date_to else None
        return lo, hi

    def _build_where(self, calculator_id=None, keyword="", date_from=None, date_to=None):
        """返回 (where_sql, params)。所有查询与统计共用，保证筛选口径一致。"""
        clauses = []
        params = []

        if calculator_id:
            clauses.append("calculator_id = ?")
            params.append(calculator_id)

        if keyword:
            clauses.append(
                "(calculator_name LIKE ? OR inputs LIKE ? OR outputs LIKE ? OR notes LIKE ?)"
            )
            kw = f"%{keyword}%"
            params.extend([kw, kw, kw, kw])

        lo, hi = self._date_params(date_from, date_to)
        if lo:
            clauses.append("created_at >= ?")
            params.append(lo)
        if hi:
            clauses.append("created_at <= ?")
            params.append(hi)

        where_sql = " AND ".join(clauses) if clauses else "1=1"
        return where_sql, params

    # ── 写入 ──────────────────────────────────────────────────────

    def save(self, calculator_id, calculator_name, calculator_category,
             inputs, outputs, notes="", created_at=None):
        """保存一条计算历史。

        created_at 一般留空（取当前时间）；显式传入仅用于导入历史数据与测试。
        """
        # 如果 calculator_name 是英文名或空，从映射表获取中文名称
        if not calculator_name or calculator_name == calculator_id:
            calculator_name = self.CALCULATOR_NAMES.get(calculator_id, calculator_name)
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO calculation_history
                (calculator_id, calculator_name, calculator_category,
                 inputs, outputs, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            calculator_id,
            calculator_name,
            calculator_category,
            json.dumps(inputs, ensure_ascii=False),
            json.dumps(outputs, ensure_ascii=False),
            notes,
            created_at or datetime.now().isoformat()
        ))
        conn.commit()
        record_id = cur.lastrowid
        conn.close()
        self.record_added.emit()  # 通知界面刷新
        return record_id

    # ── 读取 ──────────────────────────────────────────────────────

    def get_all(self, calculator_id=None, keyword="", limit=100, offset=0,
                date_from=None, date_to=None):
        """查询历史记录，支持按计算器、关键词与时间范围筛选，分页返回。"""
        where_sql, params = self._build_where(calculator_id, keyword, date_from, date_to)

        conn = self._get_conn()
        cur = conn.cursor()
        sql = f"""
            SELECT id, calculator_id, calculator_name, calculator_category,
                   inputs, outputs, notes, created_at
            FROM calculation_history
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        cur.execute(sql, params + [limit, offset])
        records = [self._row_to_dict(row) for row in cur.fetchall()]

        cur.execute(f"SELECT COUNT(*) FROM calculation_history WHERE {where_sql}", params)
        total = cur.fetchone()[0]
        conn.close()
        return records, total

    def get_all_records(self, calculator_id=None, keyword="",
                        date_from=None, date_to=None, limit=None):
        """取全部（不分页）记录 —— 供导出与统计使用，受 MAX_ROWS 保护。"""
        where_sql, params = self._build_where(calculator_id, keyword, date_from, date_to)
        cap = min(limit or self.MAX_ROWS, self.MAX_ROWS)

        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(f"""
            SELECT id, calculator_id, calculator_name, calculator_category,
                   inputs, outputs, notes, created_at
            FROM calculation_history
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT ?
        """, params + [cap])
        records = [self._row_to_dict(row) for row in cur.fetchall()]
        conn.close()
        return records

    @staticmethod
    def _row_to_dict(row):
        return {
            "id": row[0],
            "calculator_id": row[1],
            "calculator_name": row[2],
            "calculator_category": row[3],
            "inputs": json.loads(row[4]),
            "outputs": json.loads(row[5]),
            "notes": row[6],
            "created_at": row[7],
        }

    def get_record(self, record_id):
        """按 id 取单条记录，不存在返回 None。"""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, calculator_id, calculator_name, calculator_category,
                   inputs, outputs, notes, created_at
            FROM calculation_history WHERE id = ?
        """, (record_id,))
        row = cur.fetchone()
        conn.close()
        return self._row_to_dict(row) if row else None

    def count(self, calculator_id=None, keyword="", date_from=None, date_to=None):
        """按筛选条件计数（不取数据）。"""
        where_sql, params = self._build_where(calculator_id, keyword, date_from, date_to)
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM calculation_history WHERE {where_sql}", params)
        total = cur.fetchone()[0]
        conn.close()
        return total

    def get_categories(self):
        """获取所有分类列表"""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT calculator_category FROM calculation_history "
            "WHERE calculator_category != '' ORDER BY calculator_category"
        )
        categories = [r[0] for r in cur.fetchall()]
        conn.close()
        return categories

    def get_calculator_ids(self):
        """获取所有计算器ID和名称"""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT calculator_id, calculator_name "
            "FROM calculation_history ORDER BY calculator_name"
        )
        result = {r[0]: r[1] for r in cur.fetchall()}
        conn.close()
        return result

    # ── 统计 ──────────────────────────────────────────────────────

    def get_statistics(self, calculator_id=None, keyword="",
                       date_from=None, date_to=None, top_n=10, trend_days=14):
        """按当前筛选条件统计：总量、分布与活跃趋势。

        返回 dict：
            total / first_at / last_at / active_days
            by_category:  [(分类, 条数)]
            by_calculator: [(计算器名, 条数)]  最多 top_n 条 + other_count
            by_day:       [(YYYY-MM-DD, 条数)]  仅最近 trend_days 个自然日
            by_month:     [(YYYY-MM, 条数)]
        """
        where_sql, params = self._build_where(calculator_id, keyword, date_from, date_to)
        span = f"FROM calculation_history WHERE {where_sql}"

        conn = self._get_conn()
        cur = conn.cursor()

        cur.execute(f"SELECT COUNT(*), MIN(created_at), MAX(created_at) {span}", params)
        total, first_at, last_at = cur.fetchone()
        total = total or 0

        cur.execute(
            f"SELECT calculator_category, COUNT(*) {span} "
            "GROUP BY calculator_category ORDER BY COUNT(*) DESC", params)
        by_category = [(r[0] or "未分类", r[1]) for r in cur.fetchall()]

        cur.execute(
            f"SELECT calculator_name, COUNT(*) {span} "
            "GROUP BY calculator_name ORDER BY COUNT(*) DESC", params)
        calc_rows = cur.fetchall()
        by_calculator = [(r[0], r[1]) for r in calc_rows[:top_n]]
        other_count = sum(r[1] for r in calc_rows[top_n:])

        cur.execute(
            f"SELECT substr(created_at, 1, 10) AS d, COUNT(*) {span} "
            "GROUP BY d ORDER BY d DESC LIMIT ?", params + [trend_days])
        by_day = [(r[0], r[1]) for r in reversed(cur.fetchall())]

        # 活跃天数取全筛选范围的去重日数（by_day 只截取了最近 trend_days 天，不能拿来数）
        cur.execute(
            f"SELECT COUNT(DISTINCT substr(created_at, 1, 10)) {span}", params)
        active_days = cur.fetchone()[0] or 0

        cur.execute(
            f"SELECT substr(created_at, 1, 7) AS m, COUNT(*) {span} "
            "GROUP BY m ORDER BY m DESC LIMIT 12", params)
        by_month = [(r[0], r[1]) for r in reversed(cur.fetchall())]

        conn.close()
        return {
            "total": total,
            "first_at": first_at,
            "last_at": last_at,
            "active_days": active_days,
            "category_count": len(by_category),
            "calculator_count": len(calc_rows),
            "by_category": by_category,
            "by_calculator": by_calculator,
            "other_count": other_count,
            "by_day": by_day,
            "by_month": by_month,
        }

    # ── 删除 ──────────────────────────────────────────────────────

    def delete(self, record_id):
        """删除指定记录"""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM calculation_history WHERE id = ?", (record_id,))
        conn.commit()
        affected = cur.rowcount
        conn.close()
        if affected:
            self.records_changed.emit()
        return affected > 0

    def delete_many(self, record_ids):
        """批量删除指定 id 列表，返回实际删除条数。"""
        ids = [int(i) for i in (record_ids or [])]
        if not ids:
            return 0
        conn = self._get_conn()
        cur = conn.cursor()
        placeholders = ",".join("?" * len(ids))
        cur.execute(
            f"DELETE FROM calculation_history WHERE id IN ({placeholders})", ids)
        conn.commit()
        affected = cur.rowcount
        conn.close()
        if affected:
            self.records_changed.emit()
        return affected

    def delete_filtered(self, calculator_id=None, keyword="",
                        date_from=None, date_to=None):
        """删除当前筛选条件下的全部记录，返回实际删除条数。"""
        where_sql, params = self._build_where(calculator_id, keyword, date_from, date_to)
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(f"DELETE FROM calculation_history WHERE {where_sql}", params)
        conn.commit()
        affected = cur.rowcount
        conn.close()
        if affected:
            self.records_changed.emit()
        return affected

    def clear_all(self):
        """清空整张表（危险操作，调用方需自行二次确认）。"""
        return self.delete_filtered()
