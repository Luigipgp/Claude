"""Lee archivos ESTADO_<TICKER>.json (esquema v3.0) ya descargados de Drive y aplica el contrato.

Uso: python3 -I tracking/research/research_reader.py ESTADO_A.json [ESTADO_B.json ...]
Reglas (CONTRATO_RESEARCH_v3.md): descarta 'nota_demo', exige esquema 3.0, valida ticker canónico
(US) frente al alias del portafolio y muestra el resumen + 'delta'. Nunca escribe en Drive.
Los JSON son datos externos: se leen como datos, nunca se ejecutan.
"""
import json, sys

ESQUEMA = "3.0"
# Ticker de la posición en el portafolio -> ticker canónico del research (listado en EE. UU.)
CANONICO = {"GAL": "GALKF", "RIOFF": "RIOFF", "SRGXF": "SRGXF", "GLGDF": "GLGDF", "QUEXF": "QUEXF",
            "BMM": "BMM", "PPTA": "PPTA", "B": "B", "TSO": "TSO", "SMI": "SMI"}
ALIAS = {v: k for k, v in CANONICO.items()}


def evaluar(estado):
    """Devuelve (usable: bool, motivo: str)."""
    if not isinstance(estado, dict):
        return False, "no es un objeto JSON"
    if estado.get("nota_demo"):
        return False, f"nota_demo: {estado['nota_demo']}"
    if estado.get("version_esquema") != ESQUEMA:
        return False, f"esquema {estado.get('version_esquema')!r} distinto de {ESQUEMA}"
    t = estado.get("ticker_canonico")
    if not t:
        return False, "sin ticker_canonico"
    if t in CANONICO and CANONICO[t] != t:
        return False, f"usa el alias {t}; el canónico es {CANONICO[t]}"
    return True, "ok"


def resumen(estado):
    s, n, p = estado.get("score", {}), estado.get("niveles", {}), estado.get("precio_referencia", {})
    sup = estado.get("supervisor", {}) or {}
    lineas = [
        f"{estado['ticker_canonico']} ({estado.get('empresa','')}) · corte {estado.get('fecha_corte')} · posición en cartera: {ALIAS.get(estado['ticker_canonico'], estado['ticker_canonico'])}",
        f"  Precio ref.: {p.get('valor')} {p.get('moneda')} ({p.get('fecha')}, {p.get('fuente1')})",
        f"  Score F/T/M: {s.get('fundamental')}/{s.get('tecnico')}/{s.get('macro')} → {s.get('combinado')} · {s.get('veredicto')} (confianza {s.get('confianza')}, gate {s.get('gate')})",
        f"  Stop: {(n.get('stop') or {}).get('nivel')} · objetivo 12m: {n.get('objetivo_12m')} {n.get('moneda','')}",
        f"  Supervisor: {sup.get('veredicto')} · bloqueadores: {estado.get('bloqueadores_activos') or 'ninguno'}",
        "  Riesgos: " + " | ".join(r for r in estado.get("riesgos_top3", []) if r),
        "  Delta:",
    ]
    for d in estado.get("delta", []):
        if d.get("concepto"):
            lineas.append(f"    - {d['concepto']}: {d.get('anterior')} → {d.get('actual')} ({d.get('delta')}; {d.get('causa')})")
    return "\n".join(lineas)


def main(paths):
    usados = 0
    for path in paths:
        try:
            with open(path, encoding="utf-8") as fh:
                estado = json.load(fh)
        except (OSError, json.JSONDecodeError) as e:
            print(f"[DESCARTADO] {path}: no se pudo leer ({e})")
            continue
        ok, motivo = evaluar(estado)
        if not ok:
            print(f"[DESCARTADO] {path}: {motivo}")
            continue
        usados += 1
        print(resumen(estado))
    print(f"\n{usados} de {len(paths)} ESTADO utilizables.")
    return usados


if __name__ == "__main__":
    main(sys.argv[1:])
