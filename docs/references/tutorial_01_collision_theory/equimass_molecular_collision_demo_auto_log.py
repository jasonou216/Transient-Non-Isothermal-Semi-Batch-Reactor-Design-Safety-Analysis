"""
Interactive molecular-collision demonstration

Two molecular species (A and B) move in a 2-D box and undergo:
- elastic molecule-molecule collisions
- elastic wall collisions

Interactive controls:
- Temperature (K)
- Number of A molecules
- Number of B molecules
- Pause/Resume
- Randomize

This is a qualitative kinetic-theory visualization. Position and time units
are arbitrary, but speeds scale as sqrt(T/m), so higher temperature produces
faster molecules and the heavier species moves more slowly at the same T.

Requirements:
    numpy
    matplotlib
"""

import csv
from datetime import datetime
from pathlib import Path

import numpy as np
from collections import deque
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Slider, Button

BOX_W = 10.0
BOX_H = 6.0
RADIUS = 0.11

MASS_A = 1.0
MASS_B = 1.0

T_REF = 300.0
BASE_SPEED = 1.0
DT = 0.012
INTERVAL_MS = 20
ROLLING_WINDOW = 3.0  # simulation-time units
LOG_INTERVAL = 0.5  # automatic CSV logging interval

rng = np.random.default_rng(7)

# Each execution of the program writes to its own CSV file.
SCRIPT_DIR = (
    Path(__file__).resolve().parent
    if "__file__" in globals()
    else Path.cwd()
)
SESSION_TAG = datetime.now().strftime("%Y%m%d_%H%M%S")
DATA_FILE = SCRIPT_DIR / f"collision_demo_data_{SESSION_TAG}.csv"

CSV_FIELDS = [
    "run_id", "elapsed_time", "time_since_condition_change",
    "temperature_K", "kinetic_temperature_K", "N_A", "N_B",
    "rolling_window",
    "AA_total_collisions", "AA_cumulative_rate", "AA_rolling_collisions", "AA_rolling_rate",
    "AB_total_collisions", "AB_cumulative_rate", "AB_rolling_collisions", "AB_rolling_rate",
    "BB_total_collisions", "BB_cumulative_rate", "BB_rolling_collisions", "BB_rolling_rate",
]

# Create the CSV immediately when the simulation starts.
with DATA_FILE.open("w", newline="", encoding="utf-8") as f:
    csv.DictWriter(f, fieldnames=CSV_FIELDS).writeheader()



class MolecularBox:
    def __init__(self, nA=20, nB=20, temperature=300.0):
        self.nA = int(nA)
        self.nB = int(nB)
        self.temperature = float(temperature)
        self.elapsed = 0.0
        self.collision_counts = {"A-A": 0, "A-B": 0, "B-B": 0}
        self.collision_history = {
            "A-A": deque(),
            "A-B": deque(),
            "B-B": deque(),
        }
        self.condition_change_time = 0.0
        self.run_id = 0
        self.next_log_time = LOG_INTERVAL
        self.initialize_particles()

    @property
    def n(self):
        return self.nA + self.nB

    def initialize_particles(self):
        self.species = np.array(["A"] * self.nA + ["B"] * self.nB, dtype="U1")
        self.mass = np.where(self.species == "A", MASS_A, MASS_B).astype(float)
        self.position = np.zeros((self.n, 2), dtype=float)

        # Place particles without initial overlaps.
        for i in range(self.n):
            placed = False
            for _ in range(10000):
                candidate = np.array([
                    rng.uniform(RADIUS, BOX_W - RADIUS),
                    rng.uniform(RADIUS, BOX_H - RADIUS),
                ])

                if i == 0:
                    placed = True
                else:
                    d = np.linalg.norm(self.position[:i] - candidate, axis=1)
                    placed = np.all(d > 2.2 * RADIUS)

                if placed:
                    self.position[i] = candidate
                    break

            if not placed:
                raise RuntimeError(
                    "Could not place all particles without overlap. "
                    "Reduce the molecule count."
                )

        # Maxwell-like 2-D velocity components.  sigma ∝ sqrt(T/m).
        sigma = BASE_SPEED * np.sqrt(self.temperature / T_REF) / np.sqrt(self.mass)
        self.velocity = rng.normal(0.0, 1.0, size=(self.n, 2)) * sigma[:, None]

        # Remove net center-of-mass drift.
        total_momentum = np.sum(self.mass[:, None] * self.velocity, axis=0)
        self.velocity -= total_momentum / np.sum(self.mass)

        self.elapsed = 0.0
        self.collision_counts = {"A-A": 0, "A-B": 0, "B-B": 0}
        self.collision_history = {
            "A-A": deque(),
            "A-B": deque(),
            "B-B": deque(),
        }
        self.condition_change_time = 0.0
        self.run_id += 1
        self.next_log_time = LOG_INTERVAL

    def set_temperature(self, new_temperature):
        new_temperature = float(new_temperature)
        if new_temperature <= 0:
            return
        factor = np.sqrt(new_temperature / self.temperature)
        self.velocity *= factor
        self.temperature = new_temperature

        # A recorded rolling window should contain data from only one
        # temperature condition.
        self.condition_change_time = self.elapsed

    def kinetic_temperature(self):
        if self.n == 0:
            return 0.0
        ke = 0.5 * self.mass * np.sum(self.velocity**2, axis=1)
        return T_REF * np.mean(ke) / (BASE_SPEED**2)

    def wall_collisions(self):
        hit = self.position[:, 0] < RADIUS
        self.position[hit, 0] = RADIUS
        self.velocity[hit, 0] = np.abs(self.velocity[hit, 0])

        hit = self.position[:, 0] > BOX_W - RADIUS
        self.position[hit, 0] = BOX_W - RADIUS
        self.velocity[hit, 0] = -np.abs(self.velocity[hit, 0])

        hit = self.position[:, 1] < RADIUS
        self.position[hit, 1] = RADIUS
        self.velocity[hit, 1] = np.abs(self.velocity[hit, 1])

        hit = self.position[:, 1] > BOX_H - RADIUS
        self.position[hit, 1] = BOX_H - RADIUS
        self.velocity[hit, 1] = -np.abs(self.velocity[hit, 1])

    def molecule_collisions(self):
        contact = 2.0 * RADIUS

        for i in range(self.n - 1):
            for j in range(i + 1, self.n):
                dr = self.position[j] - self.position[i]
                dist2 = np.dot(dr, dr)

                if dist2 >= contact**2 or dist2 == 0.0:
                    continue

                dist = np.sqrt(dist2)
                normal = dr / dist

                # Positive means the pair is approaching along normal i -> j.
                relative_normal_speed = np.dot(
                    self.velocity[i] - self.velocity[j], normal
                )

                if relative_normal_speed > 0.0:
                    impulse = (
                        2.0 * relative_normal_speed
                        / (1.0 / self.mass[i] + 1.0 / self.mass[j])
                    )

                    self.velocity[i] -= (impulse / self.mass[i]) * normal
                    self.velocity[j] += (impulse / self.mass[j]) * normal

                    pair = "".join(sorted([self.species[i], self.species[j]]))
                    if pair == "AA":
                        pair_name = "A-A"
                    elif pair == "AB":
                        pair_name = "A-B"
                    else:
                        pair_name = "B-B"

                    self.collision_counts[pair_name] += 1
                    self.collision_history[pair_name].append(self.elapsed)

                # Separate overlapping particles after collision detection.
                overlap = contact - dist
                if overlap > 0:
                    total_mass = self.mass[i] + self.mass[j]
                    self.position[i] -= (
                        normal * overlap * self.mass[j] / total_mass
                    )
                    self.position[j] += (
                        normal * overlap * self.mass[i] / total_mass
                    )

    def _prune_collision_history(self):
        """Keep only collision events inside the rolling time window."""
        cutoff = self.elapsed - ROLLING_WINDOW

        for history in self.collision_history.values():
            while history and history[0] < cutoff:
                history.popleft()

    def rolling_collision_count(self, pair):
        """Number of collisions of a given pair in the current rolling window."""
        self._prune_collision_history()
        return len(self.collision_history[pair])

    def rolling_collision_rate(self, pair):
        """
        Collision frequency over the recent rolling window.

        During the first ROLLING_WINDOW time units, divide by the elapsed
        time so the displayed rate is not artificially suppressed.
        """
        self._prune_collision_history()

        effective_window = min(self.elapsed, ROLLING_WINDOW)
        if effective_window <= 0.0:
            return 0.0

        return len(self.collision_history[pair]) / effective_window

    def cumulative_collision_rate(self, pair):
        """Average collision frequency from the start/reset of the run."""
        if self.elapsed <= 0.0:
            return 0.0

        return self.collision_counts[pair] / self.elapsed

    def write_log_row(self):
        """Append the current state to the CSV file."""
        pairs = ("A-A", "A-B", "B-B")
        cumulative_rates = {p: self.cumulative_collision_rate(p) for p in pairs}
        rolling_counts = {p: self.rolling_collision_count(p) for p in pairs}
        rolling_rates = {p: self.rolling_collision_rate(p) for p in pairs}

        row = {
            "run_id": self.run_id,
            "elapsed_time": self.elapsed,
            "time_since_condition_change": self.elapsed - self.condition_change_time,
            "temperature_K": self.temperature,
            "kinetic_temperature_K": self.kinetic_temperature(),
            "N_A": self.nA,
            "N_B": self.nB,
            "rolling_window": ROLLING_WINDOW,
            "AA_total_collisions": self.collision_counts["A-A"],
            "AA_cumulative_rate": cumulative_rates["A-A"],
            "AA_rolling_collisions": rolling_counts["A-A"],
            "AA_rolling_rate": rolling_rates["A-A"],
            "AB_total_collisions": self.collision_counts["A-B"],
            "AB_cumulative_rate": cumulative_rates["A-B"],
            "AB_rolling_collisions": rolling_counts["A-B"],
            "AB_rolling_rate": rolling_rates["A-B"],
            "BB_total_collisions": self.collision_counts["B-B"],
            "BB_cumulative_rate": cumulative_rates["B-B"],
            "BB_rolling_collisions": rolling_counts["B-B"],
            "BB_rolling_rate": rolling_rates["B-B"],
        }
        with DATA_FILE.open("a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=CSV_FIELDS).writerow(row)

    def auto_log_if_due(self):
        """Automatically append data every LOG_INTERVAL simulation-time units."""
        while self.elapsed + 1e-12 >= self.next_log_time:
            self.write_log_row()
            self.next_log_time += LOG_INTERVAL

    def step(self):
        self.position += self.velocity * DT
        self.wall_collisions()
        self.molecule_collisions()
        self.wall_collisions()
        self.elapsed += DT
        self.auto_log_if_due()


system = MolecularBox(nA=20, nB=20, temperature=300.0)
paused = False

fig = plt.figure(figsize=(13.5, 7.2))

# Main molecular simulation box on the left.
ax = fig.add_axes([0.06, 0.29, 0.64, 0.63])

# Dedicated statistics panel outside the simulation box.
ax_stats = fig.add_axes([0.735, 0.34, 0.235, 0.52])
ax_stats.axis("off")

ax.set_xlim(0, BOX_W)
ax.set_ylim(0, BOX_H)
ax.set_aspect("equal", adjustable="box")
ax.set_xlabel("x position (arbitrary units)")
ax.set_ylabel("y position (arbitrary units)")
ax.set_title("Molecular collisions in a 2-D box")

scatter_A = ax.scatter([], [], s=85, label=f"Molecule A (mass = {MASS_A:g})")
scatter_B = ax.scatter(
    [], [], s=85, marker="s", label=f"Molecule B (mass = {MASS_B:g})"
)
ax.legend(loc="upper right")

# Basic system information remains outside the box as well.
system_text = ax_stats.text(
    0.0,
    1.0,
    "",
    transform=ax_stats.transAxes,
    va="top",
    ha="left",
    fontsize=10,
)

stats_text = ax_stats.text(
    0.0,
    0.72,
    "",
    transform=ax_stats.transAxes,
    va="top",
    ha="left",
    family="monospace",
    fontsize=9.5,
)

record_status = ax_stats.text(
    0.0,
    0.03,
    f"Auto logging every {LOG_INTERVAL:.1f} time units\nCSV: {DATA_FILE.name}",
    transform=ax_stats.transAxes,
    va="bottom",
    ha="left",
    fontsize=8.5,
)

ax_temp = plt.axes([0.14, 0.17, 0.52, 0.035])
ax_nA = plt.axes([0.14, 0.115, 0.52, 0.035])
ax_nB = plt.axes([0.14, 0.060, 0.52, 0.035])

slider_temp = Slider(ax_temp, "Temperature (K)", 100, 1000, valinit=300, valstep=10)
slider_nA = Slider(ax_nA, "Number A", 1, 60, valinit=20, valstep=1)
slider_nB = Slider(ax_nB, "Number B", 1, 60, valinit=20, valstep=1)

ax_pause = plt.axes([0.78, 0.135, 0.14, 0.05])
button_pause = Button(ax_pause, "Pause")

ax_reset = plt.axes([0.78, 0.065, 0.14, 0.05])
button_reset = Button(ax_reset, "Randomize")


def update_particle_counts(_value=None):
    system.nA = int(slider_nA.val)
    system.nB = int(slider_nB.val)
    system.temperature = float(slider_temp.val)
    system.initialize_particles()


def update_temperature(value):
    system.set_temperature(float(value))


def toggle_pause(_event):
    global paused
    paused = not paused
    button_pause.label.set_text("Resume" if paused else "Pause")


def randomize(_event):
    system.temperature = float(slider_temp.val)
    system.nA = int(slider_nA.val)
    system.nB = int(slider_nB.val)
    system.initialize_particles()


slider_temp.on_changed(update_temperature)
slider_nA.on_changed(update_particle_counts)
slider_nB.on_changed(update_particle_counts)
button_pause.on_clicked(toggle_pause)
button_reset.on_clicked(randomize)


def animate(_frame):
    if not paused:
        # Two smaller physical steps per displayed frame improve collision capture.
        for _ in range(2):
            system.step()

    mask_A = system.species == "A"
    mask_B = system.species == "B"

    scatter_A.set_offsets(system.position[mask_A])
    scatter_B.set_offsets(system.position[mask_B])

    pairs = ("A-A", "A-B", "B-B")

    cumulative_rates = {
        pair: system.cumulative_collision_rate(pair)
        for pair in pairs
    }
    rolling_counts = {
        pair: system.rolling_collision_count(pair)
        for pair in pairs
    }
    rolling_rates = {
        pair: system.rolling_collision_rate(pair)
        for pair in pairs
    }

    system_text.set_text(
        f"Temperature setting: {system.temperature:.0f} K\n"
        f"Kinetic estimate: {system.kinetic_temperature():.0f} K\n"
        f"N(A) = {system.nA}    N(B) = {system.nB}\n"
        f"Elapsed simulation time: {system.elapsed:.1f}"
    )

    stats_text.set_text(
        "COLLISION STATISTICS\n"
        "────────────────────────────────\n"
        "Pair   Total   Avg rate   "
        f"Last {ROLLING_WINDOW:.0f}   Roll rate\n"
        "────────────────────────────────\n"
        f"A-A   {system.collision_counts['A-A']:5d}"
        f"   {cumulative_rates['A-A']:7.2f}"
        f"     {rolling_counts['A-A']:5d}"
        f"      {rolling_rates['A-A']:7.2f}\n"
        f"A-B   {system.collision_counts['A-B']:5d}"
        f"   {cumulative_rates['A-B']:7.2f}"
        f"     {rolling_counts['A-B']:5d}"
        f"      {rolling_rates['A-B']:7.2f}\n"
        f"B-B   {system.collision_counts['B-B']:5d}"
        f"   {cumulative_rates['B-B']:7.2f}"
        f"     {rolling_counts['B-B']:5d}"
        f"      {rolling_rates['B-B']:7.2f}\n\n"
        "Total    = cumulative collisions\n"
        "Avg rate = total / elapsed time\n"
        f"Last {ROLLING_WINDOW:.0f}   = collisions in recent window\n"
        "Roll rate = recent collisions / window"
    )

    return scatter_A, scatter_B, system_text, stats_text


ani = FuncAnimation(
    fig,
    animate,
    interval=INTERVAL_MS,
    blit=False,
    cache_frame_data=False,
)

plt.show()
