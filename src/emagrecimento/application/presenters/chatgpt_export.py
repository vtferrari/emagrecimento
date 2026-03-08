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

    # Withings ZIP (daily history) when available
    wz = summary.get("withings_zip")
    if wz:
        bc = wz.get("body_composition", {})
        latest = bc.get("latest", {})
        first = bc.get("first", {})
        delta = bc.get("delta", {})
        sleep = wz.get("sleep", {}).get("summary", {})
        activity = wz.get("activity", {}).get("summary", {})
        cardio = wz.get("cardiovascular", {})
        ecg = cardio.get("ecg_summary") or {}

        lines = ["Withings ZIP (histórico diário):"]
        if latest and first:
            w_first = first.get("weight_kg")
            w_latest = latest.get("weight_kg")
            d_w = delta.get("weight_kg")
            if w_first is not None and w_latest is not None:
                d_str = f" ({d_w:+.1f} kg)" if d_w is not None else ""
                lines.append(f"- Peso: {w_first} kg → {w_latest} kg{d_str}")
            fat_f = first.get("fat_mass_kg")
            fat_l = latest.get("fat_mass_kg")
            d_f = delta.get("fat_mass_kg")
            if fat_f is not None and fat_l is not None:
                d_str = f" ({d_f:+.1f} kg)" if d_f is not None else ""
                lines.append(f"- Gordura: {fat_f} kg → {fat_l} kg{d_str}")
            mus_f = first.get("muscle_mass_kg")
            mus_l = latest.get("muscle_mass_kg")
            d_m = delta.get("muscle_mass_kg")
            if mus_f is not None and mus_l is not None:
                d_str = f" ({d_m:+.1f} kg)" if d_m is not None else ""
                lines.append(f"- Músculo: {mus_f} kg → {mus_l} kg{d_str}")
            visc_f = first.get("visceral_fat")
            visc_l = latest.get("visceral_fat")
            d_v = delta.get("visceral_fat")
            if visc_f is not None and visc_l is not None:
                d_str = f" ({d_v:+.1f})" if d_v is not None else ""
                lines.append(f"- Gordura visceral: {visc_f} → {visc_l}{d_str}")
            meta_f = first.get("metabolic_age")
            meta_l = latest.get("metabolic_age")
            d_meta = delta.get("metabolic_age")
            if meta_f is not None and meta_l is not None:
                d_str = f" ({d_meta:+.0f} anos)" if d_meta is not None else ""
                lines.append(f"- Idade metabólica: {meta_f} → {meta_l} anos{d_str}")
        if sleep:
            avg_sleep = sleep.get("avg_total_h")
            total_nights = sleep.get("total_nights", 0)
            if avg_sleep is not None:
                lines.append(f"- Sono médio: {avg_sleep:.1f}h/noite ({total_nights} noites registradas)")
        if activity and activity.get("avg_daily_steps") is not None:
            lines.append(f"- Passos médios: {activity['avg_daily_steps']:,.0f}/dia")
        if ecg:
            total = ecg.get("total", 0)
            normal = ecg.get("normal", 0)
            lines.append(f"- ECGs: {total} registros, {normal} normais")

        if len(lines) > 1:
            parts.append("\n" + "\n".join(lines))

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
