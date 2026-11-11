import ctypes
class E(ctypes.Structure):
    _fields_ = [("key", ctypes.c_void_p), ("hash", ctypes.c_ssize_t)]
class SetObj(ctypes.Structure):
    _fields_ = [("rc", ctypes.c_ssize_t), ("tp", ctypes.c_void_p), ("fill", ctypes.c_ssize_t), ("used", ctypes.c_ssize_t),
                ("mask", ctypes.c_ssize_t), ("table", ctypes.POINTER(E)), ("hash", ctypes.c_ssize_t), ("finger", ctypes.c_ssize_t)]
def dump(s):
    o = SetObj.from_address(id(s))
    t = [(o.table[i].key, o.table[i].hash) for i in range(o.mask + 1)]
    return o.fill, o.used, o.mask, ["_" if k is None else ("D" if h == -1 else h) for k, h in t]
if __name__ == "__main__":
    a = set()
    log = [('add', 50), ('add', 59), ('add', 32), ('disc', 63), ('add', 0), ('add', 0), ('disc', 262144), ('disc', 60), ('disc', 59), ('disc', 0), ('add', 56)]
    for op, v in log:
        a.add(v) if op == 'add' else a.discard(v)
        print(op, v, dump(a))
