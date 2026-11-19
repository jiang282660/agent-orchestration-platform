"""RunState：共享运行状态。

节点间通过读写 state 传递数据，全程记录变更历史，可回溯、可复现。
M1 先提供基础实现，M3 工作流引擎会在此基础上做 reads/writes 绑定。
"""

import copy


class RunState:
    def __init__(self, initial: dict | None = None):
        self._data: dict = dict(initial or {})
        self._history: list[tuple[str, dict]] = []  # (action, payload)

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value):
        self._data[key] = value
        self._history.append(("set", {key: copy.deepcopy(value)}))
        return self

    def read(self, keys: list[str]) -> dict:
        return {k: self._data[k] for k in keys if k in self._data}

    def write(self, updates: dict):
        for k, v in updates.items():
            self._data[k] = v
        self._history.append(("write", copy.deepcopy(updates)))
        return self

    def snapshot(self) -> dict:
        return copy.deepcopy(self._data)

    def history(self) -> list[tuple[str, dict]]:
        return list(self._history)

    def to_dict(self) -> dict:
        return {"data": self.snapshot(), "history": self.history()}
