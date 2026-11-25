"""Calcula os critérios congelados da rodada 20 a partir de operações agregadas por pregão."""
from decimal import Decimal
from itertools import accumulate

ZERO = Decimal("0")


def assess(operations_by_day, max_exposure, profile, validation):
    """Recebe resultados líquidos individuais em ordem de encerramento para cada data."""
    sample = validation["amostra_formal"]
    rules = validation["criterios_conjuntivos"]
    day_count = len(operations_by_day)
    if day_count > sample["pregoes_cronologicos_fixos"]:
        raise ValueError("A quantidade de pregões supera a janela congelada.")
    if max_exposure < 0:
        raise ValueError("Informe a exposição absoluta máxima.")
    days = [[Decimal(str(result)) for result in operations_by_day[day]]
            for day in sorted(operations_by_day)]
    pnl = [trade for trades in days for trade in trades]
    if any(not trade.is_finite() for trade in pnl):
        raise ValueError("Os resultados precisam ser finitos.")
    daily_net = [sum(trades, ZERO) for trades in days]
    n = len(pnl)
    wins = sum(trade > ZERO for trade in pnl)
    net = sum(daily_net, ZERO)
    gain = sum((trade for trade in pnl if trade > ZERO), ZERO)
    loss = -sum((trade for trade in pnl if trade < ZERO), ZERO)
    daily_mean = net / day_count if day_count else ZERO
    frequency = Decimal(n) / day_count if day_count else ZERO
    top2 = sum((max(ZERO, day) for day in sorted(daily_net, reverse=True)[:2]), ZERO)
    peak = drawdown = ZERO
    for equity in accumulate(pnl):
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    worst = min(daily_net, default=ZERO)

    gates = {
        "liquido_positivo": net > ZERO,
        "media_diaria": daily_mean >= rules["liquido_por_pregao_min_reais"],
        "fator_lucro": gain > ZERO and gain >= loss * Decimal(str(rules["fator_lucro_liquido_min"])),
        "concentracao": net > ZERO and top2 <= net * Decimal(str(rules["participacao_top2_dias_max"])),
        "drawdown": drawdown <= rules["drawdown_realizado_max_reais"],
        "liquido_sobre_drawdown": net > ZERO and net >= drawdown * Decimal(str(rules["liquido_sobre_drawdown_min"])),
        "pior_pregao": worst >= rules["pior_pregao_min_reais"],
        "acerto": n > 0 and Decimal(wins) >= n * Decimal(str(rules["acerto_min"][profile])),
        "frequencia": rules["frequencia_minima_por_pregao"] <= frequency <= rules["frequencia_maxima_por_pregao"],
        "exposicao": max_exposure <= rules["exposicao_maxima_contratos"],
    }
    if 0 < day_count < sample["pregoes_cronologicos_fixos"]:
        decision = "piloto_descritivo"
    elif day_count == 0 or n < sample["operacoes_encerradas_minimo_por_perfil"]:
        decision = "amostra_insuficiente"
    else:
        decision = "aprovado" if all(gates.values()) else "nao_aprovado"
    return dict(decisao=decision, criterios=gates, operacoes=n, acertos=wins,
                liquido=float(net), liquido_por_pregao=float(daily_mean),
                operacoes_por_pregao=float(frequency), drawdown=float(drawdown),
                top2_liquido_positivo=float(top2),
                concentracao_top2=float(top2 / net) if net > ZERO else None)