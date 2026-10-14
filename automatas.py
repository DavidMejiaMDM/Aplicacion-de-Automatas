"""Lógica pura del simulador: AFND, subconjuntos, ecuaciones y verificación."""

from __future__ import annotations

from collections import deque
from itertools import product
from typing import Any, Iterable

EPSILON = "ε"
EMPTY = ("empty",)
LAMBDA = ("epsilon",)


def validate_automaton(data: dict[str, Any]) -> dict[str, Any]:
    """Valida y normaliza el formato JSON del autómata."""
    if not isinstance(data, dict):
        raise ValueError("El autómata debe ser un objeto JSON.")
    required = {"states", "alphabet", "initial", "finals", "transitions"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Faltan campos obligatorios: {', '.join(sorted(missing))}.")

    states = data["states"]
    alphabet = data["alphabet"]
    finals = data["finals"]
    transitions = data["transitions"]
    if not isinstance(states, list) or not states or any(not isinstance(x, str) or not x for x in states):
        raise ValueError("'states' debe ser una lista no vacía de nombres de estado.")
    if len(set(states)) != len(states):
        raise ValueError("Los nombres de estado deben ser únicos.")
    if not isinstance(alphabet, list) or any(not isinstance(x, str) or len(x) != 1 for x in alphabet):
        raise ValueError("'alphabet' debe ser una lista de símbolos de un carácter.")
    if len(set(alphabet)) != len(alphabet):
        raise ValueError("Los símbolos del alfabeto deben ser únicos.")
    reserved = {EPSILON, "λ", "∅", "+", "*", "(", ")"}
    if reserved.intersection(alphabet):
        raise ValueError("El alfabeto no puede incluir ε, λ, ∅ ni operadores de expresión regular.")
    if not isinstance(data["initial"], str) or data["initial"] not in states:
        raise ValueError("El estado inicial debe pertenecer a 'states'.")
    if not isinstance(finals, list) or any(x not in states for x in finals):
        raise ValueError("Todos los estados finales deben pertenecer a 'states'.")
    if not isinstance(transitions, list):
        raise ValueError("'transitions' debe ser una lista.")

    clean_transitions = []
    seen = set()
    for index, edge in enumerate(transitions, 1):
        if not isinstance(edge, dict) or not {"from", "symbol", "to"} <= edge.keys():
            raise ValueError(f"La transición {index} requiere from, symbol y to.")
        source, symbol, target = edge["from"], edge["symbol"], edge["to"]
        if source not in states or target not in states:
            raise ValueError(f"La transición {index} menciona un estado inexistente.")
        if symbol not in alphabet and symbol != EPSILON:
            raise ValueError(f"El símbolo {symbol!r} de la transición {index} no está en el alfabeto ni es ε.")
        key = (source, symbol, target)
        if key not in seen:
            clean_transitions.append({"from": source, "symbol": symbol, "to": target})
            seen.add(key)

    return {
        "states": list(states),
        "alphabet": list(alphabet),
        "initial": data["initial"],
        "finals": list(dict.fromkeys(finals)),
        "transitions": clean_transitions,
    }


def outgoing(automaton: dict[str, Any]) -> dict[str, dict[str, set[str]]]:
    table = {state: {} for state in automaton["states"]}
    for edge in automaton["transitions"]:
        table[edge["from"]].setdefault(edge["symbol"], set()).add(edge["to"])
    return table


def epsilon_closure(states: Iterable[str], automaton: dict[str, Any]) -> frozenset[str]:
    """Calcula la clausura-ε de un conjunto de estados."""
    table = outgoing(automaton)
    closure = set(states)
    pending = list(states)
    while pending:
        current = pending.pop()
        for target in table[current].get(EPSILON, set()):
            if target not in closure:
                closure.add(target)
                pending.append(target)
    return frozenset(closure)


def subset_label(states: Iterable[str]) -> str:
    items = sorted(states)
    return "{" + ",".join(items) + "}" if items else "∅"


def subset_construction(data: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Convierte un AFND, opcionalmente con ε, usando construcción por subconjuntos."""
    nfa = validate_automaton(data)
    table = outgoing(nfa)
    start = epsilon_closure({nfa["initial"]}, nfa)
    queue = deque([start])
    discovered = {start}
    steps: list[dict[str, Any]] = []
    transitions = []

    while queue:
        current = queue.popleft()
        for symbol in nfa["alphabet"]:
            moved: set[str] = set()
            for state in current:
                moved.update(table[state].get(symbol, set()))
            destination = epsilon_closure(moved, nfa)
            steps.append({
                "current": current,
                "symbol": symbol,
                "moved": frozenset(moved),
                "destination": destination,
            })
            transitions.append({
                "from": subset_label(current),
                "symbol": symbol,
                "to": subset_label(destination),
            })
            if destination not in discovered:
                discovered.add(destination)
                queue.append(destination)

    ordered_sets = [start]
    ordered_sets.extend(sorted(discovered - {start}, key=lambda s: (len(s), sorted(s))))
    labels = [subset_label(group) for group in ordered_sets]
    dfa = {
        "states": labels,
        "alphabet": list(nfa["alphabet"]),
        "initial": subset_label(start),
        "finals": [subset_label(group) for group in ordered_sets if set(group) & set(nfa["finals"])],
        "transitions": transitions,
    }
    return dfa, steps


def accepts_nfa(data: dict[str, Any], word: str) -> bool:
    nfa = validate_automaton(data)
    table = outgoing(nfa)
    current = epsilon_closure({nfa["initial"]}, nfa)
    for symbol in word:
        if symbol not in nfa["alphabet"]:
            return False
        moved: set[str] = set()
        for state in current:
            moved.update(table[state].get(symbol, set()))
        current = epsilon_closure(moved, nfa)
    return bool(set(current) & set(nfa["finals"]))


def accepts_dfa(data: dict[str, Any], word: str) -> bool:
    dfa = validate_automaton(data)
    table = outgoing(dfa)
    current = dfa["initial"]
    for symbol in word:
        if symbol not in dfa["alphabet"]:
            return False
        destinations = table[current].get(symbol, set())
        if len(destinations) != 1:
            return False
        current = next(iter(destinations))
    return current in dfa["finals"]


# Árboles de expresión: (operador, ...operandos). Son inmutables para poder simplificar y deduplicar.
Regex = tuple[Any, ...]


def literal(symbol: str) -> Regex:
    return LAMBDA if symbol == EPSILON else ("literal", symbol)


def reference(state: str) -> Regex:
    return ("ref", state)


def regex_union(*expressions: Regex) -> Regex:
    terms: list[Regex] = []
    for expression in expressions:
        if expression == EMPTY:
            continue
        if expression[0] == "union":
            terms.extend(expression[1:])
        elif expression not in terms:
            terms.append(expression)
    unique = []
    for term in terms:
        if term not in unique:
            unique.append(term)
    if not unique:
        return EMPTY
    if len(unique) == 1:
        return unique[0]
    return ("union", *unique)


def regex_concat(*expressions: Regex) -> Regex:
    factors: list[Regex] = []
    for expression in expressions:
        if expression == EMPTY:
            return EMPTY
        if expression == LAMBDA:
            continue
        if expression[0] == "concat":
            factors.extend(expression[1:])
        else:
            factors.append(expression)
    if not factors:
        return LAMBDA
    # Mantiene lineales las ecuaciones: una unión concatenada con un prefijo
    # se distribuye para que cada alternativa termine en, como máximo, una X_q.
    alternatives = [expression[1:] if expression[0] == "union" else (expression,) for expression in factors]
    if any(len(options) > 1 for options in alternatives):
        return regex_union(*(regex_concat(*choice) for choice in product(*alternatives)))
    if len(factors) == 1:
        return factors[0]
    return ("concat", *factors)


def regex_star(expression: Regex) -> Regex:
    if expression in (EMPTY, LAMBDA):
        return LAMBDA
    if expression[0] == "star":
        return expression
    return ("star", expression)


def render_regex(expression: Regex, ref_prefix: str = "") -> str:
    """Renderiza una ER; ref_prefix se usa para mostrar X_estado en ecuaciones."""
    kind = expression[0]
    if kind == "empty":
        return "∅"
    if kind == "epsilon":
        return "λ"
    if kind == "literal":
        return expression[1]
    if kind == "ref":
        return f"{ref_prefix}{expression[1]}" if ref_prefix else f"<{expression[1]}>"
    if kind == "star":
        child = expression[1]
        rendered = render_regex(child, ref_prefix)
        if child[0] in {"union", "concat"}:
            rendered = f"({rendered})"
        return rendered + "*"
    if kind == "concat":
        parts = []
        for child in expression[1:]:
            value = render_regex(child, ref_prefix)
            if child[0] == "union":
                value = f"({value})"
            parts.append(value)
        return "".join(parts)
    if kind == "union":
        return "+".join(render_regex(child, ref_prefix) for child in expression[1:])
    raise ValueError(f"Operador de ER desconocido: {kind}")


def equation_expression(data: dict[str, Any]) -> dict[str, Regex]:
    nfa = validate_automaton(data)
    equations: dict[str, Regex] = {state: EMPTY for state in nfa["states"]}
    for edge in nfa["transitions"]:
        term = regex_concat(literal(edge["symbol"]), reference(edge["to"]))
        equations[edge["from"]] = regex_union(equations[edge["from"]], term)
    for final in nfa["finals"]:
        equations[final] = regex_union(equations[final], LAMBDA)
    return equations


def _branches(expression: Regex) -> list[Regex]:
    if expression[0] == "union":
        result: list[Regex] = []
        for child in expression[1:]:
            result.extend(_branches(child))
        return result
    return [] if expression == EMPTY else [expression]


def _split_terminal_reference(term: Regex) -> tuple[Regex, str | None]:
    """Separa un prefijo regular y una referencia terminal, si existe."""
    factors = list(term[1:]) if term[0] == "concat" else [term]
    if factors and factors[-1][0] == "ref":
        state = factors[-1][1]
        prefix = regex_concat(*factors[:-1])
        return prefix, state
    if any(_contains_reference(factor) for factor in factors):
        raise ValueError("No se pudo linealizar una ecuación; revise el autómata.")
    return term, None


def _contains_reference(expression: Regex) -> bool:
    if expression[0] == "ref":
        return True
    return any(_contains_reference(child) for child in expression[1:] if isinstance(child, tuple))


def _replace_reference(expression: Regex, state: str, replacement: Regex) -> Regex:
    if expression[0] == "ref":
        return replacement if expression[1] == state else expression
    if expression[0] == "union":
        return regex_union(*(_replace_reference(child, state, replacement) for child in expression[1:]))
    if expression[0] == "concat":
        return regex_concat(*(_replace_reference(child, state, replacement) for child in expression[1:]))
    if expression[0] == "star":
        return regex_star(_replace_reference(expression[1], state, replacement))
    return expression


def format_equations(equations: dict[str, Regex]) -> list[str]:
    return [f"X_{state} = {render_regex(expr, 'X_')}" for state, expr in equations.items()]


def solve_regular_expression(data: dict[str, Any]) -> dict[str, Any]:
    """Resuelve ecuaciones de estados mediante sustitución y lema de Arden."""
    automaton = validate_automaton(data)
    equations = equation_expression(automaton)
    initial_equations = dict(equations)
    order = [state for state in reversed(automaton["states"]) if state != automaton["initial"]]
    order.append(automaton["initial"])
    trace: list[dict[str, Any]] = []

    for state in order:
        before = dict(equations)
        loop_coefficients: list[Regex] = []
        remainder_terms: list[Regex] = []
        for term in _branches(equations[state]):
            prefix, target = _split_terminal_reference(term)
            if target == state:
                loop_coefficients.append(prefix)
            else:
                remainder_terms.append(term)
        loop = regex_union(*loop_coefficients)
        remainder = regex_union(*remainder_terms)
        solution = regex_concat(regex_star(loop), remainder)

        if loop != EMPTY and remainder != EMPTY:
            rule = "Bucle más salida (lema de Arden: X = A·X + B ⇒ X = A*·B)"
        elif loop != EMPTY and remainder == LAMBDA:
            rule = "Bucle con salida λ (X = A·X + λ ⇒ X = A*)"
        elif loop != EMPTY:
            rule = "Bucle sin ruta de aceptación (A*·∅ = ∅)"
        else:
            terms_count = len(_branches(remainder))
            rule = "Transición simple y sustitución" if terms_count <= 1 else "Varias transiciones y sustitución"

        if state == automaton["initial"]:
            trace.append({
                "state": state,
                "rule": rule,
                "loop": loop,
                "remainder": remainder,
                "solution": solution,
                "before": before,
                "after": {},
                "substitutions": [],
            })
            final_expression = solution
            break

        substitutions = []
        for other_state in list(equations):
            if other_state == state:
                continue
            old = equations[other_state]
            if _contains_reference(old) and any(
                term[0] == "ref" and term[1] == state
                or term[0] == "concat" and any(factor[0] == "ref" and factor[1] == state for factor in term[1:])
                for term in _branches(old)
            ):
                new = _replace_reference(old, state, solution)
                if new != old:
                    substitutions.append({"state": other_state, "before": old, "after": new})
                equations[other_state] = new
        equations.pop(state, None)
        trace.append({
            "state": state,
            "rule": rule,
            "loop": loop,
            "remainder": remainder,
            "solution": solution,
            "before": before,
            "after": dict(equations),
            "substitutions": substitutions,
        })
    else:
        final_expression = EMPTY

    return {
        "initial_equations": initial_equations,
        "trace": trace,
        "expression": final_expression,
        "regular_expression": render_regex(final_expression),
    }


def _regex_nfa(expression: Regex) -> dict[str, Any]:
    transitions: list[dict[str, str]] = []
    counter = 0

    def new_state() -> str:
        nonlocal counter
        state = f"r{counter}"
        counter += 1
        return state

    def build(node: Regex) -> tuple[str, str]:
        kind = node[0]
        start, end = new_state(), new_state()
        if kind == "empty":
            return start, end
        if kind == "epsilon":
            transitions.append({"from": start, "symbol": EPSILON, "to": end})
        elif kind == "literal":
            transitions.append({"from": start, "symbol": node[1], "to": end})
        elif kind == "union":
            for child in node[1:]:
                child_start, child_end = build(child)
                transitions.extend([
                    {"from": start, "symbol": EPSILON, "to": child_start},
                    {"from": child_end, "symbol": EPSILON, "to": end},
                ])
        elif kind == "concat":
            fragments = [build(child) for child in node[1:]]
            if fragments:
                start = fragments[0][0]
                end = fragments[-1][1]
                for (_, previous_end), (next_start, _) in zip(fragments, fragments[1:]):
                    transitions.append({"from": previous_end, "symbol": EPSILON, "to": next_start})
        elif kind == "star":
            child_start, child_end = build(node[1])
            transitions.extend([
                {"from": start, "symbol": EPSILON, "to": end},
                {"from": start, "symbol": EPSILON, "to": child_start},
                {"from": child_end, "symbol": EPSILON, "to": child_start},
                {"from": child_end, "symbol": EPSILON, "to": end},
            ])
        else:
            raise ValueError(f"Operador de ER desconocido: {kind}")
        return start, end

    initial, final = build(expression)
    states = [f"r{i}" for i in range(counter)]
    return {"states": states, "alphabet": [], "initial": initial, "finals": [final], "transitions": transitions}


def accepts_regex(expression: Regex, word: str) -> bool:
    """Evalúa una ER a través de su AFND de Thompson."""
    automaton = _regex_nfa(expression)
    table = outgoing(automaton)

    def closure(states: Iterable[str]) -> frozenset[str]:
        result = set(states)
        pending = list(states)
        while pending:
            current = pending.pop()
            for target in table[current].get(EPSILON, set()):
                if target not in result:
                    result.add(target)
                    pending.append(target)
        return frozenset(result)

    current = closure({automaton["initial"]})
    for symbol in word:
        moved: set[str] = set()
        for state in current:
            moved.update(table[state].get(symbol, set()))
        current = closure(moved)
    return bool(set(current) & set(automaton["finals"]))


def verify_equivalence(nfa_data: dict[str, Any], dfa_data: dict[str, Any], expression: Regex, max_length: int) -> dict[str, Any]:
    """Compara AFND, AFD y ER sobre todas las palabras de longitud hasta max_length."""
    nfa = validate_automaton(nfa_data)
    dfa = validate_automaton(dfa_data)
    if nfa["alphabet"] != dfa["alphabet"]:
        raise ValueError("El AFND y el AFD deben usar el mismo alfabeto y el mismo orden de símbolos.")
    if not isinstance(max_length, int) or max_length < 6:
        raise ValueError("La longitud máxima debe ser un entero de al menos 6.")
    mismatches = []
    checked = 0
    alphabet = nfa["alphabet"]
    regex_nfa = _regex_nfa(expression)
    # Reusar el autómata de Thompson evita reconstruirlo para cada cadena.
    regex_table = outgoing(regex_nfa)
    nfa_table = outgoing(nfa)
    dfa_table = outgoing(dfa)

    def nfa_accepts_with_table(word: str) -> bool:
        def closure(states: Iterable[str]) -> frozenset[str]:
            result = set(states)
            pending = list(states)
            while pending:
                current = pending.pop()
                for target in nfa_table[current].get(EPSILON, set()):
                    if target not in result:
                        result.add(target)
                        pending.append(target)
            return frozenset(result)

        current = closure({nfa["initial"]})
        for char in word:
            moved: set[str] = set()
            for state in current:
                moved.update(nfa_table[state].get(char, set()))
            current = closure(moved)
        return bool(set(current) & set(nfa["finals"]))

    def dfa_accepts_with_table(word: str) -> bool:
        current = dfa["initial"]
        for char in word:
            destinations = dfa_table[current].get(char, set())
            if len(destinations) != 1:
                return False
            current = next(iter(destinations))
        return current in dfa["finals"]

    def regex_accepts_with_table(word: str) -> bool:
        def closure(states: Iterable[str]) -> frozenset[str]:
            result = set(states)
            pending = list(states)
            while pending:
                current = pending.pop()
                for target in regex_table[current].get(EPSILON, set()):
                    if target not in result:
                        result.add(target)
                        pending.append(target)
            return frozenset(result)

        current = closure({regex_nfa["initial"]})
        for char in word:
            moved: set[str] = set()
            for state in current:
                moved.update(regex_table[state].get(char, set()))
            current = closure(moved)
        return bool(set(current) & set(regex_nfa["finals"]))

    for length in range(max_length + 1):
        for letters in product(alphabet, repeat=length):
            word = "".join(letters)
            nfa_result = nfa_accepts_with_table(word)
            dfa_result = dfa_accepts_with_table(word)
            regex_result = regex_accepts_with_table(word)
            checked += 1
            if not (nfa_result == dfa_result == regex_result):
                mismatches.append({
                    "word": word,
                    "nfa": nfa_result,
                    "dfa": dfa_result,
                    "regex": regex_result,
                })
    return {"checked": checked, "mismatches": mismatches, "max_length": max_length}
