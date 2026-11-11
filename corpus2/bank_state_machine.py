from typing import Optional

IDLE = 0
RUNNING = 1
PAUSED = 2
STOPPED = 3

NAMES = {IDLE: "idle", RUNNING: "running", PAUSED: "paused", STOPPED: "stopped"}
TRANSITIONS = {
    (IDLE, "start"): RUNNING,
    (RUNNING, "pause"): PAUSED,
    (PAUSED, "resume"): RUNNING,
    (RUNNING, "stop"): STOPPED,
    (PAUSED, "stop"): STOPPED,
}


class Machine:
    def __init__(self, name: str) -> None:
        self.name = name
        self.state = IDLE
        self.history: list[int] = [IDLE]
        self.listeners: list[str] = []

    def fire(self, event: str) -> bool:
        nxt = TRANSITIONS.get((self.state, event))
        if nxt is None:
            return False
        self.state = nxt
        self.history.append(nxt)
        return True

    def describe(self) -> str:
        trail = " -> ".join(NAMES[s] for s in self.history)
        return f"{self.name}: {NAMES[self.state]} [{trail}]"


def run_events(name: str, events: list[str]) -> tuple[str, int]:
    m = Machine(name)
    rejected = 0
    for ev in events:
        if not m.fire(ev):
            rejected += 1
    return m.describe(), rejected


def first_stopped(machines: list[Machine]) -> Optional[Machine]:
    for m in machines:
        if m.state == STOPPED:
            return m
    return None


def main() -> None:
    print(run_events("job1", ["start", "pause", "resume", "stop"]))
    print(run_events("job2", ["pause", "start", "start", "stop", "resume"]))
    ms = [Machine("a"), Machine("b"), Machine("c")]
    ms[1].fire("start")
    ms[2].fire("start")
    ms[2].fire("stop")
    s = first_stopped(ms)
    print(s.name if s is not None else "none", first_stopped(ms[:2]) is None)
    counts: dict[int, int] = {}
    for m in ms:
        counts[m.state] = counts.get(m.state, 0) + 1
    print(sorted(counts.items()))


if __name__ == "__main__":
    main()
