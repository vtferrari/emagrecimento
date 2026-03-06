"""ChatGPT export structure: agent prompt + context for cutting reports."""

CHATGPT_PROMPT = (
    "Você é um nutricionista e coach de emagrecimento. Analise o relatório completo em 'report' e forneça: "
    "(1) um resumo executivo do progresso; (2) priorização dos alertas (critical, warning, info) com recomendações práticas; "
    "(3) sugestões de ajustes na alimentação e treino para melhorar a aderência; "
    "(4) comentário sobre as projeções de peso e se a meta é atingível. Responda em português do Brasil."
)


def build_agent_context(summary: dict) -> str:
    """Build dynamic context string from report summary for ChatGPT."""
    user = summary.get("user") or {}
    target_date = summary.get("target_date") or ""
    targets = (
        (summary.get("meta") or {}).get("adherence_targets")
        or (summary.get("nutrition") or {}).get("adherence_targets")
        or {}
    )

    parts = ["Relatório de cutting"]
    name = user.get("name")
    age = user.get("age")
    height_cm = user.get("height_cm")
    weight_kg = user.get("weight_kg")
    if name or age is not None or height_cm is not None or weight_kg is not None:
        sub = []
        if name:
            sub.append(str(name))
        if age is not None:
            sub.append(f"{age} anos")
        if height_cm is not None:
            sub.append(f"{height_cm}cm")
        if weight_kg is not None:
            sub.append(f"{weight_kg}kg")
        parts.append(" para " + ", ".join(sub))
    parts.append(". ")

    if target_date:
        parts.append(f"Meta de peso para {target_date}. ")

    parts.append(
        "Dados de MyFitnessPal (nutrição, exercício) e Withings (peso, composição corporal, sono). "
    )

    cal_range = targets.get("calorie_range")
    if cal_range and len(cal_range) >= 2:
        parts.append(f"Faixa calórica alvo: {cal_range[0]}-{cal_range[1]} kcal. ")
    if targets.get("protein_g") is not None:
        parts.append(f"Proteína alvo: {targets['protein_g']}g. ")
    if targets.get("fiber_g") is not None:
        parts.append(f"Fibra alvo: {targets['fiber_g']}g. ")
    sessions = targets.get("sessions_per_week", 4)
    parts.append(f"Treino alvo: {sessions} sessões/semana.")

    return "".join(parts).strip()


def wrap_report_for_chatgpt(summary: dict) -> dict:
    """Wrap report summary with agent prompt and context for ChatGPT."""
    return {
        "agent": {
            "prompt": CHATGPT_PROMPT,
            "context": build_agent_context(summary),
        },
        "report": summary,
    }
