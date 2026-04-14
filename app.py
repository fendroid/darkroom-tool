#!/usr/bin/env python3
"""
Darkroom Chemical Mixer Calculator
Thermodynamic temperature mixing calculator for analog film developers.
"""

import argparse
import sys
from fractions import Fraction


def parse_ratio(ratio_str: str) -> tuple[float, float]:
    """
    Parse a dilution ratio string (e.g. '1+9', '1+14', '2+8').
    Returns a (chemical_part, water_part) tuple.
    """
    ratio_str = ratio_str.strip().replace(" ", "")
    if "+" in ratio_str:
        parts = ratio_str.split("+")
        if len(parts) != 2:
            raise ValueError(f"Invalid dilution ratio: '{ratio_str}'. Format: e.g. 1+9")
        chem_part = float(Fraction(parts[0]))
        water_part = float(Fraction(parts[1]))
        return chem_part, water_part
    elif ":" in ratio_str:
        parts = ratio_str.split(":")
        if len(parts) != 2:
            raise ValueError(f"Invalid dilution ratio: '{ratio_str}'. Format: e.g. 1:9")
        chem_part = float(Fraction(parts[0]))
        water_part = float(Fraction(parts[1]))
        return chem_part, water_part
    else:
        raise ValueError(f"Invalid dilution ratio: '{ratio_str}'. Use '+' or ':' as separator.")


def calculate_mix(
    t_cold: float,
    t_warm: float,
    t_chem: float,
    t_target: float,
    ratio_str: str,
    total_volume: float,
) -> dict:
    """
    Calculate the required volumes of each component.

    Thermodynamic heat balance equation (assuming equal specific heat capacity):
        m_cold * T_cold + m_warm * T_warm + m_chem * T_chem = m_total * T_target

    Constraints:
        m_cold + m_warm + m_chem = m_total
        m_chem / m_total = chem_part / (chem_part + water_part)

    Chemical volume is fixed by the dilution ratio:
        m_chem = total_volume * chem_part / (chem_part + water_part)

    The remaining water (m_water = total_volume - m_chem) is split between cold and warm:
        m_cold + m_warm = m_water
        m_cold * T_cold + m_warm * T_warm + m_chem * T_chem = total_volume * T_target

    Solving for m_cold:
        m_cold * T_cold + (m_water - m_cold) * T_warm = total_volume * T_target - m_chem * T_chem
        m_cold * (T_cold - T_warm) = total_volume * T_target - m_chem * T_chem - m_water * T_warm
        m_cold = (total_volume * T_target - m_chem * T_chem - m_water * T_warm) / (T_cold - T_warm)
    """
    chem_part, water_part = parse_ratio(ratio_str)
    total_parts = chem_part + water_part

    m_chem = total_volume * chem_part / total_parts
    m_water = total_volume - m_chem  # total cold + warm water

    # Solve heat balance
    # m_cold * T_cold + (m_water - m_cold) * T_warm + m_chem * T_chem = total_volume * T_target
    # m_cold * (T_cold - T_warm) = total_volume * T_target - m_chem * T_chem - m_water * T_warm

    numerator = total_volume * t_target - m_chem * t_chem - m_water * t_warm
    denominator = t_cold - t_warm

    if abs(denominator) < 1e-9:
        # Cold and warm water are the same temperature
        if abs(t_cold - t_target) < 1e-3:
            # All temperatures match — any split works
            m_cold = m_water / 2
            m_warm = m_water / 2
        else:
            raise ValueError(
                f"Cold and warm water are both {t_cold}°C, "
                f"but target temperature is {t_target}°C. No solution possible."
            )
    else:
        m_cold = numerator / denominator
        m_warm = m_water - m_cold

    # Sanity checks
    warnings = []
    if m_cold < -0.5:
        warnings.append(
            f"⚠️  Cold water volume is negative ({m_cold:.1f} ml). "
            "Lower the warm water temperature, or the target temperature is out of range."
        )
    if m_warm < -0.5:
        warnings.append(
            f"⚠️  Warm water volume is negative ({m_warm:.1f} ml). "
            "Raise the warm water temperature, or the target temperature is out of range."
        )

    # Verification: actual mixture temperature
    if total_volume > 0:
        t_actual = (m_cold * t_cold + m_warm * t_warm + m_chem * t_chem) / total_volume
    else:
        t_actual = t_target

    return {
        "m_cold": round(m_cold, 1),
        "m_warm": round(m_warm, 1),
        "m_chem": round(m_chem, 1),
        "total": round(total_volume, 1),
        "t_actual": round(t_actual, 2),
        "t_target": t_target,
        "ratio_str": ratio_str,
        "chem_part": chem_part,
        "water_part": water_part,
        "warnings": warnings,
    }


def format_result(result: dict) -> str:
    lines = []
    lines.append("\n" + "═" * 40)
    lines.append("  RESULT")
    lines.append("═" * 40)
    lines.append(f"  Cold water:   {result['m_cold']:>8.1f} ml")
    lines.append(f"  Warm water:   {result['m_warm']:>8.1f} ml")
    lines.append(f"  Chemical:     {result['m_chem']:>8.1f} ml")
    lines.append("  " + "─" * 28)
    lines.append(f"  Total:        {result['total']:>8.1f} ml")
    lines.append(f"  Mix temp:    {result['t_actual']:>8.2f} °C  (target: {result['t_target']}°C)")
    if result["warnings"]:
        lines.append("")
        for w in result["warnings"]:
            lines.append(f"  {w}")
    lines.append("═" * 40 + "\n")
    return "\n".join(lines)


def interactive_cli():
    """Interactive CLI mode — prompts for each input one by one."""
    print("\n╔══════════════════════════════════════╗")
    print("║   Darkroom Chemical Mixer Calculator ║")
    print("╚══════════════════════════════════════╝\n")

    def get_float(prompt, unit="°C"):
        while True:
            try:
                val = input(f"  {prompt} [{unit}]: ").strip()
                return float(val.replace(",", "."))
            except ValueError:
                print("  ❌ Invalid number. Please try again.")

    def get_ratio():
        while True:
            val = input("  Dilution ratio (e.g. 1+9, 1+14): ").strip()
            try:
                parse_ratio(val)
                return val
            except ValueError as e:
                print(f"  ❌ {e}")

    t_cold   = get_float("Cold water temperature")
    t_warm   = get_float("Warm water temperature")
    t_chem   = get_float("Chemical concentrate temperature")
    t_target = get_float("Target temperature")
    ratio    = get_ratio()
    total    = get_float("Desired total volume", "ml")

    try:
        result = calculate_mix(t_cold, t_warm, t_chem, t_target, ratio, total)
        print(format_result(result))
    except ValueError as e:
        print(f"\n  ❌ Error: {e}\n")
        sys.exit(1)


def cli_args():
    """Non-interactive CLI mode — all inputs passed as arguments."""
    parser = argparse.ArgumentParser(
        description="Darkroom chemical mixer — thermodynamic temperature calculator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python app.py --cold 4 --warm 22 --chem 22 --target 20 --ratio 1+9 --volume 300
  python app.py -c 4 -w 22 -k 22 -t 20 -r 1+14 -v 500
        """,
    )
    parser.add_argument("--cold",   "-c", type=float, required=True, help="Cold water temperature (°C)")
    parser.add_argument("--warm",   "-w", type=float, required=True, help="Warm water temperature (°C)")
    parser.add_argument("--chem",   "-k", type=float, required=True, help="Chemical concentrate temperature (°C)")
    parser.add_argument("--target", "-t", type=float, required=True, help="Target temperature (°C)")
    parser.add_argument("--ratio",  "-r", type=str,   required=True, help="Dilution ratio (e.g. 1+9)")
    parser.add_argument("--volume", "-v", type=float, required=True, help="Desired total volume (ml)")

    args = parser.parse_args()

    try:
        result = calculate_mix(
            args.cold, args.warm, args.chem, args.target, args.ratio, args.volume
        )
        print(format_result(result))
    except ValueError as e:
        print(f"\n❌ Error: {e}\n")
        sys.exit(1)


# ─── Flask web server ─────────────────────────────────────────────────────────

def create_app():
    from flask import Flask, request, jsonify, send_from_directory

    app = Flask(__name__, static_folder="static")

    @app.route("/")
    def index():
        return send_from_directory("static", "index.html")
    
    @app.route("/timer.html")
    def timer():
        return send_from_directory("static", "timer.html")

    @app.route("/api/calculate", methods=["POST"])
    def calculate():
        data = request.get_json()
        try:
            result = calculate_mix(
                t_cold=float(data["t_cold"]),
                t_warm=float(data["t_warm"]),
                t_chem=float(data["t_chem"]),
                t_target=float(data["t_target"]),
                ratio_str=str(data["ratio"]),
                total_volume=float(data["total_volume"]),
            )
            return jsonify({"ok": True, "result": result})
        except (KeyError, TypeError) as e:
            return jsonify({"ok": False, "error": f"Missing or invalid field: {e}"}), 400
        except ValueError as e:
            return jsonify({"ok": False, "error": str(e)}), 422

    return app


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Arguments provided: non-interactive mode
        cli_args()
    else:
        # No arguments: interactive mode
        interactive_cli()

