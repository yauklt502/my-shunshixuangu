"""主板昨日涨停、竞价涨停取反选股（基准 + 连板优化）。"""

from .rules import optimized_select, sequential_select
from .trajectory import score_trajectory

__all__ = ["sequential_select", "optimized_select", "score_trajectory"]
