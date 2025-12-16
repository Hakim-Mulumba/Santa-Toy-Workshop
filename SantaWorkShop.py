import asyncio
import json
import random
import math
from typing import List, Dict, Tuple
import matplotlib.pyplot as plt

# ==================================================
# EXCEPTIONS
# ==================================================

class InvalidOrderError(Exception):
    """Raised when an order is invalid."""

# ==================================================
# DATA CLASSES
# ==================================================

class Toy:
    """Represents a toy in the catalogue."""

    def __init__(self, name: str, category: str, build_time: int, stock: int):
        self.name = name
        self.category = category
        self.build_time = build_time
        self.stock = stock

    def reserve(self) -> bool:
        if self.stock > 0:
            self.stock -= 1
            return True
        return False

class Order:
    """Represents a toy order."""

    def __init__(self, child: str, toy: str, priority: int, address: str, message: str = ""):
        if not 1 <= priority <= 5:
            raise InvalidOrderError("Priority must be between 1 and 5.")
        self.child = child
        self.toy = toy
        self.priority = priority
        self.address = address
        self.message = message

class Elf:
    """Represents an elf worker."""

    def __init__(self, name: str, skills: set, capacity: int):
        self.name = name
        self.skills = skills
        self.capacity = capacity
        self.assigned_toys: List[Toy] = []

    def can_build(self, toy: Toy) -> bool:
        return toy.category in self.skills and self.capacity >= toy.build_time

    def assign(self, toy: Toy) -> bool:
        if self.can_build(toy):
            self.assigned_toys.append(toy)
            self.capacity -= toy.build_time
            return True
        return False

    async def build_toys(self):
        """Build toys sequentially with parallel elves."""
        current_time = 0
        for toy in self.assigned_toys:
            print(f"[{self.name}] Start building {toy.name} at t={current_time:.1f} min")
            build_duration = toy.build_time / 10  # scaled down
            await asyncio.sleep(build_duration)
            current_time += build_duration
            print(f"[{self.name}] Finished {toy.name} at t={current_time:.1f} min")

# ==================================================
# WORKSHOP CONTROLLER
# ==================================================

class Workshop:
    """Main workshop system."""

    def __init__(self):
        self.toys: Dict[str, Toy] = {}
        self.orders: List[Order] = []
        self.elves: List[Elf] = []

    # --------------------------
    # Setup Methods
    # --------------------------

    def add_toy(self, toy: Toy):
        self.toys[toy.name] = toy

    def add_elf(self, elf: Elf):
        self.elves.append(elf)

    def add_order(self, order: Order):
        if order.toy not in self.toys:
            raise InvalidOrderError(f"Toy '{order.toy}' not found.")
        self.orders.append(order)

    def remove_toy(self, toy_name: str):
        """Remove a toy from the catalogue."""
        if toy_name in self.toys:
            del self.toys[toy_name]
        else:
            raise InvalidOrderError(f"Toy '{toy_name}' not found.")

    def cancel_order(self, index: int):
        """Cancel an order by index."""
        if 0 <= index < len(self.orders):
            self.orders.pop(index)
        else:
            raise InvalidOrderError(f"Order index {index} out of range.")

    # --------------------------
    # Persistence
    # --------------------------

    def save_state(self, path: str):
        state = {
            "toys": {name: vars(toy) for name, toy in self.toys.items()},
            "orders": [vars(o) for o in self.orders],
            "elves": [
                {"name": e.name, "skills": list(e.skills), "capacity": e.capacity} for e in self.elves
            ]
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=4)

    def load_state(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
        self.toys = {name: Toy(**data) for name, data in state["toys"].items()}
        self.orders = [Order(**o) for o in state["orders"]]
        self.elves = [Elf(o["name"], set(o["skills"]), o["capacity"]) for o in state["elves"]]

    # --------------------------
    # Core Logic
    # --------------------------

    def estimate_build_time(self) -> int:
        return sum(self.toys[o.toy].build_time for o in self.orders)

    def reserve_orders(self):
        for order in self.orders:
            toy = self.toys[order.toy]
            status = "RESERVED" if toy.reserve() else "BACKORDER"
            print(f"{order.child} ordered {order.toy}: {status}")

    def top_priority_orders(self, n: int = 3) -> List[Order]:
        return sorted(self.orders, key=lambda o: o.priority, reverse=True)[:n]

    # --------------------------
    # Elf Scheduling
    # --------------------------

    def assign_elves(self) -> List[Order]:
        """Assign orders to elves efficiently; return unassigned orders."""
        sorted_orders = sorted(
            self.orders,
            key=lambda o: (-o.priority, self.toys[o.toy].build_time)
        )
        unassigned = []

        for order in sorted_orders:
            toy = self.toys[order.toy]
            eligible_elves = [elf for elf in self.elves if elf.can_build(toy)]
            if eligible_elves:
                best_elf = min(eligible_elves, key=lambda e: e.capacity - toy.build_time)
                best_elf.assign(toy)
            else:
                unassigned.append(order)
        return unassigned

    async def run_elf_simulation(self):
        """Run all elves building their toys concurrently."""
        await asyncio.gather(*(elf.build_toys() for elf in self.elves))

    # --------------------------
    # Delivery Routing & Visualization
    # --------------------------

    def generate_coordinates(self) -> Dict[str, Tuple[int, int]]:
        return {o.address: (random.randint(0, 100), random.randint(0, 100)) for o in self.orders}

    def nearest_neighbour_route(self, coords: Dict[str, Tuple[int, int]]) -> Tuple[List[str], float]:
        addresses = list(coords.keys())
        start = addresses[0]
        route = [start]
        unvisited = set(addresses[1:])
        total_distance = 0.0
        current = start

        while unvisited:
            next_stop = min(unvisited, key=lambda x: math.dist(coords[current], coords[x]))
            total_distance += math.dist(coords[current], coords[next_stop])
            route.append(next_stop)
            unvisited.remove(next_stop)
            current = next_stop
        return route, total_distance

    def visualize_elves(self):
        names = [e.name for e in self.elves]
        used = [sum(t.build_time for t in e.assigned_toys) for e in self.elves]
        remaining = [e.capacity for e in self.elves]

        plt.bar(names, used, label='Used Time')
        plt.bar(names, remaining, bottom=used, label='Remaining Capacity')
        plt.ylabel("Minutes")
        plt.title("Elf Utilisation")
        plt.legend()
        plt.show()

    def visualize_route(self, coords: Dict[str, Tuple[int, int]], route: List[str]):
        x = [coords[addr][0] for addr in route]
        y = [coords[addr][1] for addr in route]
        plt.plot(x, y, marker='o')
        for i, addr in enumerate(route):
            plt.text(x[i]+1, y[i]+1, addr, fontsize=8)
        plt.title("Delivery Route")
        plt.xlabel("X coordinate")
        plt.ylabel("Y coordinate")
        plt.show()

    def visualize_gantt(self):
        """Gantt chart for elf toy builds (scaled simulation)."""
        fig, ax = plt.subplots()
        for idx, elf in enumerate(self.elves):
            start = 0
            for toy in elf.assigned_toys:
                duration = toy.build_time / 10
                ax.barh(idx, duration, left=start, height=0.4)
                ax.text(start + duration/2, idx, toy.name, ha='center', va='center', color='white')
                start += duration
        ax.set_yticks(range(len(self.elves)))
        ax.set_yticklabels([e.name for e in self.elves])
        ax.set_xlabel("Time (simulated minutes)")
        ax.set_title("Elf Toy Build Gantt Chart")
        plt.show()

# ==================================================
# RUN WORKSHOP
# ==================================================

def main():
    workshop = Workshop()

    # Add toys
    workshop.add_toy(Toy("Teddy Bear", "Soft", 30, 12))
    workshop.add_toy(Toy("Robot", "Electronics", 50, 6))
    workshop.add_toy(Toy("Lego Set", "Blocks", 40, 10))
    workshop.add_toy(Toy("Sled", "Outdoor", 90, 2))

    # Add elves
    workshop.add_elf(Elf("Buddy", {"Soft", "Blocks"}, 120))
    workshop.add_elf(Elf("Jingle", {"Electronics"}, 100))
    workshop.add_elf(Elf("Sparkle", {"Outdoor", "Blocks"}, 150))

    # Add orders
    workshop.add_order(Order("Ava", "Robot", 5, "10 Snow Rd"))
    workshop.add_order(Order("Noah", "Lego Set", 3, "5 North Star Ave"))
    workshop.add_order(Order("Mia", "Teddy Bear", 4, "1 Holly Ln"))

    # Reserve stock
    print("\n=== Stock Reservation ===")
    workshop.reserve_orders()

    # Elf assignment
    print("\n=== Elf Assignment ===")
    unassigned = workshop.assign_elves()
    for e in workshop.elves:
        print(f"{e.name}: {[t.name for t in e.assigned_toys]}")
    if unassigned:
        print("Unassigned Orders:", [o.toy for o in unassigned])

    # Async elf simulation
    print("\n=== Elf Building Simulation ===")
    asyncio.run(workshop.run_elf_simulation())

    # Visualize elves
    workshop.visualize_elves()

    # Gantt chart
    workshop.visualize_gantt()

    # Delivery routing
    coords = workshop.generate_coordinates()
    route, distance = workshop.nearest_neighbour_route(coords)
    print("\n=== Delivery Route ===")
    print(" -> ".join(route))
    print(f"Total Distance: {distance:.2f}")
    workshop.visualize_route(coords, route)

    # Save workshop state
    workshop.save_state("workshop_state.json")
    print("\nWorkshop state saved to workshop_state.json")


if __name__ == "__main__":
    main()
