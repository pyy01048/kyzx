import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 测试用独立数据库，避免污染 data/yanxun.db
_TMP = tempfile.mkdtemp(prefix="yanxun-test-")
os.environ.setdefault("YANXUN_DATA", _TMP)
os.environ.setdefault("YANXUN_DB", os.path.join(_TMP, "test.db"))
