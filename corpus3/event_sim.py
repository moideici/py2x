import heapq
import random
from dataclasses import dataclass, field


@dataclass(order=True)
class Event:
    time: float
    seq: int
    kind: str = field(compare=False)
    customer: int = field(compare=False)


class Bank:
    def __init__(self, tellers: int, seed: int) -> None:
        self.rng = random.Random(seed)
        self.free_at = [0.0] * tellers
        self.queue: list[Event] = []
        self.seq = 0
        self.waits: list[float] = []
        self.log: list[str] = []

    def schedule(self, t: float, kind: str, customer: int) -> None:
        self.seq += 1
        heapq.heappush(self.queue, Event(t, self.seq, kind, customer))

    def run(self, customers: int) -> None:
        t = 0.0
        for c in range(customers):
            t += self.rng.expovariate(1.0)
            self.schedule(t, "arrive", c)
        while self.queue:
            ev = heapq.heappop(self.queue)
            if ev.kind == "arrive":
                best = min(range(len(self.free_at)), key=lambda i: self.free_at[i])
                start = max(ev.time, self.free_at[best])
                service = self.rng.uniform(0.5, 2.0)
                self.free_at[best] = start + service
                self.waits.append(start - ev.time)
                self.schedule(start + service, "leave", ev.customer)
            else:
                self.log.append(f"{ev.time:7.3f} customer {ev.customer} leaves")


def summarize(waits: list[float]) -> str:
    n = len(waits)
    mean = sum(waits) / n
    worst = max(waits)
    served_fast = sum(1 for w in waits if w < 0.01)
    return f"n={n} mean={mean:.4f} worst={worst:.4f} instant={served_fast}"


def main() -> None:
    bank = Bank(2, 2024)
    bank.run(12)
    print(summarize(bank.waits))
    for line in bank.log[:5]:
        print(line)
    print(bank.log[-1], len(bank.log))
    other = Bank(1, 7)
    other.run(6)
    print(summarize(other.waits), round(max(other.free_at), 3))
    print(Event(1.0, 1, "a", 1) < Event(1.0, 2, "b", 0), Event(0.5, 9, "z", 3) < Event(1.0, 1, "a", 1))


if __name__ == "__main__":
    main()
