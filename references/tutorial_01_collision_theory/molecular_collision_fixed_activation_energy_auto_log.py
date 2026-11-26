"""
Molecular collision and reaction demonstration with cumulative and rolling counters
===================================================================================

Reaction:
    A + B -> C

An A-B collision reacts only when its relative collision energy exceeds the
fixed activation-energy threshold.

Interactive controls:
    * Temperature (K)
    * Initial number of A molecules
    * Initial number of B molecules
    * Pause / Resume
    * Randomize / Reset

The activation energy is fixed in the code.

Displayed statistics:
    * cumulative A-A, A-B, and B-B collision counts
    * cumulative average collision rates
    * rolling collision counts over the most recent time window
    * rolling collision rates
    * cumulative successful reactions
    * rolling successful reactions
    * cumulative and rolling reaction rates

This is a qualitative 2-D classroom visualization rather than a molecular
dynamics simulation with real physical length/time scales.

Requirements:
    numpy
    matplotlib
"""

from collections import deque

import csv
from datetime import datetime
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Slider, Button

# ---------------------------------------------------------------------
# Fixed simulation parameters
# ---------------------------------------------------------------------
BOX_W = 10.0
BOX_H = 6.0
RADIUS = 0.11

MASS_A = 1.0
MASS_B = 2.5
MASS_C = MASS_A + MASS_B

T_REF = 300.0
BASE_SPEED = 1.0

# Fixed activation energy
ACTIVATION_ENERGY = 5.0  # kJ/mol

R_KJ = 8.314462618e-3  # kJ/(mol K)
ENERGY_SCALE = R_KJ * T_REF / BASE_SPEED**2

DT = 0.010
INTERVAL_MS = 25

# Rolling-window length in simulation-time units.
ROLLING_WINDOW = 3.0
LOG_INTERVAL = 0.5  # automatic CSV logging interval

rng = np.random.default_rng(7)

# Each execution of the program writes to its own CSV file.
SCRIPT_DIR = (
    Path(__file__).resolve().parent
    if "__file__" in globals()
    else Path.cwd()
)
SESSION_TAG = datetime.now().strftime("%Y%m%d_%H%M%S")
DATA_FILE = SCRIPT_DIR / f"fixed_Ea_reaction_data_{SESSION_TAG}.csv"

CSV_FIELDS = [
    "run_id", "elapsed_time", "time_since_condition_change",
    "temperature_K", "activation_energy_kJ_per_mol",
    "N_A", "N_B", "N_C", "rolling_window",
    "AA_total_collisions", "AA_cumulative_rate", "AA_rolling_collisions", "AA_rolling_rate",
    "AB_total_collisions", "AB_cumulative_rate", "AB_rolling_collisions", "AB_rolling_rate",
    "BB_total_collisions", "BB_cumulative_rate", "BB_rolling_collisions", "BB_rolling_rate",
    "total_successful_collisions", "cumulative_C_production_rate",
    "rolling_successful_collisions", "rolling_C_production_rate",
    "cumulative_successful_fraction", "rolling_successful_fraction",
]

# Create the CSV immediately when the simulation starts.
with DATA_FILE.open("w", newline="", encoding="utf-8") as f:
    csv.DictWriter(f, fieldnames=CSV_FIELDS).writeheader()



class MolecularReactionBox:
    def __init__(self, nA=25, nB=25, temperature=300.0):
        self.initial_nA = int(nA)
        self.initial_nB = int(nB)
        self.temperature = float(temperature)

        self.elapsed = 0.0
        self.reaction_flashes = []
        self.run_id = 0
        self.next_log_time = LOG_INTERVAL

        self.reset_statistics()
        self.initialize_particles()

    @property
    def n(self):
        return len(self.species)

    def count(self, label):
        return int(np.sum(self.species == label))

    # -----------------------------------------------------------------
    # Statistics
    # -----------------------------------------------------------------
    def reset_statistics(self):
        """Reset all cumulative and rolling counters."""
        self.elapsed = 0.0

        self.collision_counts = {
            "A-A": 0,
            "A-B": 0,
            "B-B": 0,
        }

        self.collision_history = {
            "A-A": deque(),
            "A-B": deque(),
            "B-B": deque(),
        }

        self.reaction_count = 0
        self.reaction_history = deque()
        self.condition_change_time = 0.0

    def record_collision(self, pair):
        """Record one collision in cumulative and rolling statistics."""
        if pair in self.collision_counts:
            self.collision_counts[pair] += 1
            self.collision_history[pair].append(self.elapsed)

    def record_reaction(self):
        """Record one successful A+B->C reaction."""
        self.reaction_count += 1
        self.reaction_history.append(self.elapsed)

    def _prune_history(self):
        """Discard events older than the rolling window."""
        cutoff = self.elapsed - ROLLING_WINDOW

        for history in self.collision_history.values():
            while history and history[0] < cutoff:
                history.popleft()

        while self.reaction_history and self.reaction_history[0] < cutoff:
            self.reaction_history.popleft()

    def cumulative_collision_rate(self, pair):
        if self.elapsed <= 0.0:
            return 0.0
        return self.collision_counts[pair] / self.elapsed

    def rolling_collision_count(self, pair):
        self._prune_history()
        return len(self.collision_history[pair])

    def rolling_collision_rate(self, pair):
        self._prune_history()

        # During startup, use the actual elapsed time rather than the full
        # rolling window so the rate is not artificially depressed.
        window = min(self.elapsed, ROLLING_WINDOW)

        if window <= 0.0:
            return 0.0

        return len(self.collision_history[pair]) / window

    def cumulative_reaction_rate(self):
        if self.elapsed <= 0.0:
            return 0.0
        return self.reaction_count / self.elapsed

    def rolling_reaction_count(self):
        self._prune_history()
        return len(self.reaction_history)

    def rolling_reaction_rate(self):
        self._prune_history()
        window = min(self.elapsed, ROLLING_WINDOW)

        if window <= 0.0:
            return 0.0

        return len(self.reaction_history) / window

    # -----------------------------------------------------------------
    # Particle initialization and thermodynamics
    # -----------------------------------------------------------------
    def initialize_particles(self):
        """Create a fresh A/B mixture with no initial particle overlap."""
        self.species = np.array(
            ["A"] * self.initial_nA + ["B"] * self.initial_nB,
            dtype="U1",
        )

        self.mass = np.where(
            self.species == "A",
            MASS_A,
            MASS_B,
        ).astype(float)

        self.position = np.zeros((self.n, 2), dtype=float)

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
                    distance = np.linalg.norm(
                        self.position[:i] - candidate,
                        axis=1,
                    )
                    placed = np.all(distance > 2.2 * RADIUS)

                if placed:
                    self.position[i] = candidate
                    break

            if not placed:
                raise RuntimeError(
                    "Could not place all particles without overlap. "
                    "Reduce the molecule count."
                )

        self.assign_thermal_velocities()

        # IMPORTANT: clear both cumulative and rolling histories together.
        self.reset_statistics()
        self.reaction_flashes = []
        self.run_id += 1
        self.next_log_time = LOG_INTERVAL

    def assign_thermal_velocities(self):
        """
        Sample 2-D Maxwell-like velocity components.

        Characteristic molecular speed scales as sqrt(T/m).
        """
        sigma = (
            BASE_SPEED
            * np.sqrt(self.temperature / T_REF)
            / np.sqrt(self.mass)
        )

        self.velocity = (
            rng.normal(size=(self.n, 2))
            * sigma[:, None]
        )

        # Remove center-of-mass drift.
        total_mass = np.sum(self.mass)

        if total_mass > 0:
            total_momentum = np.sum(
                self.mass[:, None] * self.velocity,
                axis=0,
            )
            self.velocity -= total_momentum / total_mass

    def set_temperature(self, new_temperature):
        """
        Rescale current velocities when temperature changes.

        The cumulative/rolling counters are NOT reset when temperature
        changes. This lets students observe how the rolling rate responds
        while the cumulative rate retains the history of the run.
        """
        new_temperature = float(new_temperature)

        if new_temperature <= 0:
            return

        factor = np.sqrt(new_temperature / self.temperature)
        self.velocity *= factor
        self.temperature = new_temperature
        self.condition_change_time = self.elapsed

    # -----------------------------------------------------------------
    # Collision physics
    # -----------------------------------------------------------------
    def wall_collisions(self):
        """Elastic wall collisions."""
        if self.n == 0:
            return

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

    def relative_collision_energy(self, i, j):
        """
        Relative translational collision energy in kJ/mol.

        E_rel = 1/2 * mu * |v_i - v_j|^2
        """
        dv = self.velocity[i] - self.velocity[j]

        reduced_mass = (
            self.mass[i] * self.mass[j]
            / (self.mass[i] + self.mass[j])
        )

        e_model = 0.5 * reduced_mass * np.dot(dv, dv)

        return e_model * ENERGY_SCALE

    @staticmethod
    def pair_name(s_i, s_j):
        """Return a normalized pair name for A-A, A-B, or B-B."""
        if s_i == "A" and s_j == "A":
            return "A-A"
        if {s_i, s_j} == {"A", "B"}:
            return "A-B"
        if s_i == "B" and s_j == "B":
            return "B-B"

        # Collisions involving product C are simulated physically but are
        # intentionally not included in the requested A-A/A-B/B-B counters.
        return None

    def molecule_collisions_and_reactions(self):
        """
        Handle elastic collisions and A+B->C reactions.

        A-B:
            E_rel >= ACTIVATION_ENERGY -> reaction
            otherwise                 -> elastic collision

        A-A, B-B, and collisions involving C are elastic.
        """
        if self.n < 2:
            return

        reacted = set()
        products = []

        for i in range(self.n - 1):
            if i in reacted:
                continue

            for j in range(i + 1, self.n):
                if j in reacted:
                    continue

                dr = self.position[j] - self.position[i]
                dist2 = np.dot(dr, dr)
                contact = 2.0 * RADIUS

                if dist2 <= 0.0 or dist2 >= contact**2:
                    continue

                dist = np.sqrt(dist2)
                normal = dr / dist

                relative_normal_speed = np.dot(
                    self.velocity[i] - self.velocity[j],
                    normal,
                )

                # If particles are already separating, correct overlap but
                # do not count another collision.
                if relative_normal_speed <= 0.0:
                    overlap = contact - dist

                    if overlap > 0:
                        self.position[i] -= 0.5 * overlap * normal
                        self.position[j] += 0.5 * overlap * normal

                    continue

                s_i = self.species[i]
                s_j = self.species[j]

                pair = self.pair_name(s_i, s_j)

                if pair is not None:
                    self.record_collision(pair)

                # ---------------------------------------------------------
                # Reactive A-B collision
                # ---------------------------------------------------------
                if pair == "A-B":
                    e_rel = self.relative_collision_energy(i, j)

                    if e_rel >= ACTIVATION_ENERGY:
                        m_i = self.mass[i]
                        m_j = self.mass[j]
                        m_total = m_i + m_j

                        product_position = (
                            m_i * self.position[i]
                            + m_j * self.position[j]
                        ) / m_total

                        # Conserves linear momentum.
                        product_velocity = (
                            m_i * self.velocity[i]
                            + m_j * self.velocity[j]
                        ) / m_total

                        products.append(
                            (
                                product_position.copy(),
                                product_velocity.copy(),
                            )
                        )

                        reacted.add(i)
                        reacted.add(j)

                        self.record_reaction()

                        self.reaction_flashes.append([
                            product_position[0],
                            product_position[1],
                            0.20,
                        ])

                        continue

                # ---------------------------------------------------------
                # Elastic collision
                # ---------------------------------------------------------
                impulse = (
                    2.0 * relative_normal_speed
                    / (
                        1.0 / self.mass[i]
                        + 1.0 / self.mass[j]
                    )
                )

                self.velocity[i] -= (
                    impulse / self.mass[i]
                ) * normal

                self.velocity[j] += (
                    impulse / self.mass[j]
                ) * normal

                overlap = contact - dist

                if overlap > 0:
                    total_mass = self.mass[i] + self.mass[j]

                    self.position[i] -= (
                        normal
                        * overlap
                        * self.mass[j]
                        / total_mass
                    )

                    self.position[j] += (
                        normal
                        * overlap
                        * self.mass[i]
                        / total_mass
                    )

        # Remove reacted A/B particles and add C products.
        if reacted:
            keep = np.ones(self.n, dtype=bool)
            keep[list(reacted)] = False

            self.species = self.species[keep]
            self.mass = self.mass[keep]
            self.position = self.position[keep]
            self.velocity = self.velocity[keep]

            for product_position, product_velocity in products:
                self.species = np.append(self.species, "C")
                self.mass = np.append(self.mass, MASS_C)

                self.position = np.vstack([
                    self.position,
                    product_position,
                ])

                self.velocity = np.vstack([
                    self.velocity,
                    product_velocity,
                ])

    def write_log_row(self):
        """Append the current reaction/collision state to the session CSV."""
        pairs = ("A-A", "A-B", "B-B")
        cumulative_rates = {p: self.cumulative_collision_rate(p) for p in pairs}
        rolling_counts = {p: self.rolling_collision_count(p) for p in pairs}
        rolling_rates = {p: self.rolling_collision_rate(p) for p in pairs}

        rolling_reactions = self.rolling_reaction_count()
        cumulative_reaction_rate = self.cumulative_reaction_rate()
        rolling_reaction_rate = self.rolling_reaction_rate()

        total_ab = self.collision_counts["A-B"]
        rolling_ab = rolling_counts["A-B"]
        cumulative_fraction = self.reaction_count / total_ab if total_ab else 0.0
        rolling_fraction = rolling_reactions / rolling_ab if rolling_ab else 0.0

        row = {
            "run_id": self.run_id,
            "elapsed_time": self.elapsed,
            "time_since_condition_change": self.elapsed - self.condition_change_time,
            "temperature_K": self.temperature,
            "activation_energy_kJ_per_mol": ACTIVATION_ENERGY,
            "N_A": self.count("A"),
            "N_B": self.count("B"),
            "N_C": self.count("C"),
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
            "total_successful_collisions": self.reaction_count,
            "cumulative_C_production_rate": cumulative_reaction_rate,
            "rolling_successful_collisions": rolling_reactions,
            "rolling_C_production_rate": rolling_reaction_rate,
            "cumulative_successful_fraction": cumulative_fraction,
            "rolling_successful_fraction": rolling_fraction,
        }
        with DATA_FILE.open("a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=CSV_FIELDS).writerow(row)

    def auto_log_if_due(self):
        """Automatically append data every LOG_INTERVAL simulation-time units."""
        while self.elapsed + 1e-12 >= self.next_log_time:
            self.write_log_row()
            self.next_log_time += LOG_INTERVAL

    def update_flashes(self):
        new_flashes = []

        for x, y, life in self.reaction_flashes:
            life -= DT

            if life > 0:
                new_flashes.append([x, y, life])

        self.reaction_flashes = new_flashes

    def step(self):
        if self.n > 0:
            self.position += self.velocity * DT
            self.wall_collisions()
            self.molecule_collisions_and_reactions()
            self.wall_collisions()

        self.update_flashes()
        self.elapsed += DT
        self.auto_log_if_due()


# ---------------------------------------------------------------------
# Create system
# ---------------------------------------------------------------------
system = MolecularReactionBox(
    nA=25,
    nB=25,
    temperature=300.0,
)

paused = False


# ---------------------------------------------------------------------
# Figure layout
# ---------------------------------------------------------------------
fig = plt.figure(figsize=(14.0, 7.4))

# Main molecular simulation.
ax = fig.add_axes([0.055, 0.29, 0.62, 0.63])

# Dedicated statistics panel OUTSIDE the simulation box.
ax_stats = fig.add_axes([0.705, 0.30, 0.27, 0.58])
ax_stats.axis("off")

ax.set_xlim(0, BOX_W)
ax.set_ylim(0, BOX_H)
ax.set_aspect("equal", adjustable="box")
ax.set_xlabel("x position (arbitrary units)")
ax.set_ylabel("y position (arbitrary units)")
ax.set_title("Collision theory demonstration: A + B -> C")

scatter_A = ax.scatter(
    [],
    [],
    s=90,
    c="tab:blue",
    marker="o",
    label=f"A (mass = {MASS_A:g})",
)

scatter_B = ax.scatter(
    [],
    [],
    s=90,
    c="tab:orange",
    marker="s",
    label=f"B (mass = {MASS_B:g})",
)

scatter_C = ax.scatter(
    [],
    [],
    s=130,
    c="tab:green",
    marker="D",
    label=f"C (mass = {MASS_C:g})",
)

reaction_flash = ax.scatter(
    [],
    [],
    s=240,
    c="red",
    marker="*",
    label="Reactive collision",
)

ax.legend(
    loc="upper right",
    framealpha=0.9,
)

system_text = ax_stats.text(
    0.0,
    1.0,
    "",
    transform=ax_stats.transAxes,
    va="top",
    ha="left",
    fontsize=10,
)

collision_text = ax_stats.text(
    0.0,
    0.66,
    "",
    transform=ax_stats.transAxes,
    va="top",
    ha="left",
    family="monospace",
    fontsize=9.1,
)

reaction_text = ax_stats.text(
    0.0,
    0.25,
    "",
    transform=ax_stats.transAxes,
    va="top",
    ha="left",
    family="monospace",
    fontsize=9.2,
)


record_status = ax_stats.text(
    0.0,
    0.015,
    f"Auto logging every {LOG_INTERVAL:.1f} time units\nCSV: {DATA_FILE.name}",
    transform=ax_stats.transAxes,
    va="bottom",
    ha="left",
    fontsize=8.2,
)


# ---------------------------------------------------------------------
# Sliders: only T, N_A, and N_B
# ---------------------------------------------------------------------
ax_temp = plt.axes([0.14, 0.165, 0.50, 0.032])
ax_nA = plt.axes([0.14, 0.110, 0.50, 0.032])
ax_nB = plt.axes([0.14, 0.055, 0.50, 0.032])

slider_temp = Slider(
    ax_temp,
    "Temperature (K)",
    100,
    1000,
    valinit=300,
    valstep=10,
)

slider_nA = Slider(
    ax_nA,
    "Initial number A",
    1,
    60,
    valinit=25,
    valstep=1,
)

slider_nB = Slider(
    ax_nB,
    "Initial number B",
    1,
    60,
    valinit=25,
    valstep=1,
)


# ---------------------------------------------------------------------
# Buttons
# ---------------------------------------------------------------------
ax_pause = plt.axes([0.76, 0.13, 0.15, 0.055])
button_pause = Button(
    ax_pause,
    "Pause",
)

ax_reset = plt.axes([0.76, 0.055, 0.15, 0.055])
button_reset = Button(
    ax_reset,
    "Randomize / Reset",
)


# ---------------------------------------------------------------------
# Interactive callbacks
# ---------------------------------------------------------------------
def reset_system(_event=None):
    system.initial_nA = int(slider_nA.val)
    system.initial_nB = int(slider_nB.val)
    system.temperature = float(slider_temp.val)

    system.initialize_particles()


def update_temperature(value):
    system.set_temperature(float(value))


def update_particle_counts(_value):
    # Changing the initial number of molecules starts a fresh experiment.
    reset_system()


def toggle_pause(_event):
    global paused

    paused = not paused

    button_pause.label.set_text(
        "Resume" if paused else "Pause"
    )


slider_temp.on_changed(update_temperature)
slider_nA.on_changed(update_particle_counts)
slider_nB.on_changed(update_particle_counts)

button_pause.on_clicked(toggle_pause)
button_reset.on_clicked(reset_system)


# ---------------------------------------------------------------------
# Plot helpers
# ---------------------------------------------------------------------
def set_offsets_safely(scatter, points):
    if len(points) == 0:
        scatter.set_offsets(np.empty((0, 2)))
    else:
        scatter.set_offsets(points)


# ---------------------------------------------------------------------
# Animation
# ---------------------------------------------------------------------
def animate(_frame):
    if not paused:
        # Two smaller physical steps per visible frame reduce missed collisions.
        for _ in range(2):
            system.step()

    mask_A = system.species == "A"
    mask_B = system.species == "B"
    mask_C = system.species == "C"

    set_offsets_safely(
        scatter_A,
        system.position[mask_A],
    )

    set_offsets_safely(
        scatter_B,
        system.position[mask_B],
    )

    set_offsets_safely(
        scatter_C,
        system.position[mask_C],
    )

    if system.reaction_flashes:
        flash_xy = np.array([
            [f[0], f[1]]
            for f in system.reaction_flashes
        ])
    else:
        flash_xy = np.empty((0, 2))

    set_offsets_safely(
        reaction_flash,
        flash_xy,
    )

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

    rolling_reactions = system.rolling_reaction_count()

    cumulative_reaction_rate = system.cumulative_reaction_rate()
    rolling_reaction_rate = system.rolling_reaction_rate()

    if system.collision_counts["A-B"] > 0:
        cumulative_reactive_fraction = (
            100.0
            * system.reaction_count
            / system.collision_counts["A-B"]
        )
    else:
        cumulative_reactive_fraction = 0.0

    if rolling_counts["A-B"] > 0:
        rolling_reactive_fraction = (
            100.0
            * rolling_reactions
            / rolling_counts["A-B"]
        )
    else:
        rolling_reactive_fraction = 0.0

    arrhenius_factor = np.exp(
        -ACTIVATION_ENERGY
        / (R_KJ * system.temperature)
    )

    system_text.set_text(
        f"Temperature: {system.temperature:.0f} K\n"
        f"Fixed Ea: {ACTIVATION_ENERGY:.2f} kJ/mol\n"
        f"A = {system.count('A')}    "
        f"B = {system.count('B')}    "
        f"C = {system.count('C')}\n"
        f"Elapsed simulation time: {system.elapsed:.1f}\n"
        f"exp(-Ea/RT): {arrhenius_factor:.3f}"
    )

    collision_text.set_text(
        "COLLISION STATISTICS\n"
        "────────────────────────────────────\n"
        "Pair   Total   Avg rate   "
        f"Last {ROLLING_WINDOW:.0f}   Roll rate\n"
        "────────────────────────────────────\n"
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
        "Avg rate  = total / elapsed time\n"
        "Roll rate = recent count / window"
    )

    reaction_text.set_text(
        "REACTION STATISTICS\n"
        "────────────────────────────────────\n"
        f"Total reactions:        {system.reaction_count:5d}\n"
        f"Average reaction rate:  {cumulative_reaction_rate:7.2f}\n"
        f"Reactions in last {ROLLING_WINDOW:.0f}:   {rolling_reactions:5d}\n"
        f"Rolling reaction rate:  {rolling_reaction_rate:7.2f}\n"
        f"Cumulative reactive AB: {cumulative_reactive_fraction:6.1f}%\n"
        f"Rolling reactive AB:    {rolling_reactive_fraction:6.1f}%"
    )

    return (
        scatter_A,
        scatter_B,
        scatter_C,
        reaction_flash,
        system_text,
        collision_text,
        reaction_text,
    )


ani = FuncAnimation(
    fig,
    animate,
    interval=INTERVAL_MS,
    blit=False,
    cache_frame_data=False,
)

plt.show()
