class VMError(Exception):
    pass


class StackUnderflow(VMError):
    def __init__(self, op: str, depth: int) -> None:
        super().__init__(f"{op} needs more operands (stack depth {depth})")
        self.op = op


class VM:
    def __init__(self) -> None:
        self.stack: list[int] = []
        self.vars: dict[str, int] = {}
        self.output: list[str] = []
        self.steps = 0

    def pop(self, op: str) -> int:
        if not self.stack:
            raise StackUnderflow(op, 0)
        return self.stack.pop()

    def run(self, program: list[str]) -> None:
        pc = 0
        while pc < len(program):
            self.steps += 1
            if self.steps > 1000:
                raise VMError("step limit")
            parts = program[pc].split()
            op = parts[0]
            pc += 1
            if op == "push":
                self.stack.append(int(parts[1]))
            elif op == "add":
                b, a = self.pop(op), self.pop(op)
                self.stack.append(a + b)
            elif op == "mul":
                b, a = self.pop(op), self.pop(op)
                self.stack.append(a * b)
            elif op == "sub":
                b, a = self.pop(op), self.pop(op)
                self.stack.append(a - b)
            elif op == "dup":
                v = self.pop(op)
                self.stack.append(v)
                self.stack.append(v)
            elif op == "store":
                self.vars[parts[1]] = self.pop(op)
            elif op == "load":
                self.stack.append(self.vars[parts[1]])
            elif op == "print":
                self.output.append(str(self.pop(op)))
            elif op == "jnz":
                if self.pop(op) != 0:
                    pc = int(parts[1])
            elif op == "jmp":
                pc = int(parts[1])
            else:
                raise VMError("bad opcode " + op)


def run_program(program: list[str]) -> str:
    vm = VM()
    try:
        vm.run(program)
    except StackUnderflow as e:
        return f"underflow in {e.op}: {e}"
    except KeyError as e:
        return f"unknown variable {e}"
    except VMError as e:
        return f"vm error: {e}"
    return ",".join(vm.output) + f" ({vm.steps} steps)"


def main() -> None:
    countdown = ["push 5", "store n", "load n", "print", "load n", "push 1", "sub", "dup", "store n", "jnz 2"]
    print(run_program(countdown))
    print(run_program(["push 2", "push 3", "add", "push 4", "mul", "print"]))
    print(run_program(["push 1", "add"]))
    print(run_program(["load x"]))
    print(run_program(["jmp 0"]))
    print(run_program(["nop"]))


if __name__ == "__main__":
    main()
