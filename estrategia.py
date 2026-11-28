"""Replay local de estratégias NTSL por candle."""
import argparse
import csv
from copy import deepcopy
from dataclasses import asdict, dataclass
from fractions import Fraction
import hashlib
import html
import json
import math
from time import monotonic
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd

from diagnostico import chart
from execucoes import cli_audit
from ntsl import ORDER_CONSTANTS, NTSLError, Rolling, SERIES, compile_ntsl
from simulador import OHLC, read_export, read_ticks, search_target, validate_ohlc


def source_text(path):
    data = Path(path).read_bytes()
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252")


FORMATS = {
    "profit": ("Indicador exportado do Profit", {"data_minuto_origem", "v_barra_id", *OHLC}),
    "ohlc": ("Candles OHLC com timestamp", {"timestamp", *OHLC}),
    "integrado": ("Eventos ProfitRTD integrados", {"timestamp_evento", "sequencia_fonte", "ativo_origem", "preco_ultimo", "quantidade_negocio", "segmento"}),
    "negocios": ("Negócios com timestamp", {"timestamp", "preco"}),
}


def csv_format(path, requested="auto"):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        columns = set(next(csv.reader(stream, delimiter=";"), []))
    detected = next((key for key, (_, required) in FORMATS.items() if required <= columns), None)
    if requested == "auto":
        if detected:
            return detected
        raise ValueError("Formato do CSV não reconhecido. Confira os nomes das colunas e o separador ponto e vírgula.")
    if requested not in FORMATS:
        raise ValueError(f"Formato desconhecido: {requested}.")
    label, required = FORMATS[requested]
    if required <= columns:
        return requested
    if detected:
        raise ValueError(f'O CSV corresponde a “{FORMATS[detected][0]}”. Selecione esse formato ou “Detectar automaticamente”.')
    missing = ", ".join(sorted(required - columns))
    raise ValueError(f'Colunas ausentes no formato “{label}”: {missing}. Confira o separador ponto e vírgula.')


def load_bars(path, seconds, format_name):
    if format_name == "profit":
        frame = read_export(path, seconds)
        stamp = frame["minuto"]
    elif format_name in {"negocios", "integrado"}:
        frame = read_ticks(path, seconds, integrated=format_name == "integrado")
        stamp = frame["inicio"]
        frame["v_trades_atual"] = frame["negocios"]
    elif format_name == "ohlc":
        frame = pd.read_csv(path, sep=";", decimal=",", encoding="utf-8-sig")
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], format="ISO8601")
        if frame["timestamp"].isna().any() or frame["timestamp"].duplicated().any():
            raise ValueError("Cada candle OHLC precisa ter um timestamp válido e único.")
        frame = frame.sort_values("timestamp").reset_index(drop=True)
        stamp = frame["timestamp"]
    else:
        raise ValueError(f"Formato desconhecido: {format_name}.")
    if seconds < 1:
        raise ValueError("O intervalo precisa ser positivo.")
    validate_ohlc(frame)
    for column in OHLC:
        frame[column] = pd.to_numeric(frame[column])
    frame["pregao"] = stamp.dt.strftime("%Y-%m-%d")
    delta = stamp.diff().dt.total_seconds().fillna(0)
    day_change = frame["pregao"].ne(frame["pregao"].shift())
    boundary = frame["segmento"].ne(frame["segmento"].shift()) if "segmento" in frame else delta.ne(seconds) | day_change
    if format_name == "integrado":
        boundary |= delta.gt(seconds)
    frame["segmento"] = (boundary | day_change).cumsum()
    frame["lacuna_intradiaria"] = boundary & ~day_change
    frame["intervalo_barra_segundos"] = delta
    frame["barras_no_segmento"] = frame.groupby("segmento", sort=False).cumcount()+1
    frame["data_ntsl"] = (stamp.dt.year-1900)*10000 + stamp.dt.month*100 + stamp.dt.day
    frame["hora_ntsl"] = stamp.dt.hour*100 + stamp.dt.minute
    if format_name != "profit":
        frame["segundos_do_dia_barra"] = stamp.dt.hour*3600 + stamp.dt.minute*60 + stamp.dt.second
    frame["barra_ntsl"] = np.arange(1,len(frame)+1)
    return frame


@dataclass
class Order:
    function: str
    action: str
    kind: str
    quantity: int
    price: float = 0
    limit: float | None = None
    triggered: bool = False
    sent_at: int = -1
    eligible_at: int = -1
    eligible_ns: int = -1
    requested_quantity: int = 0
    market_entry: bool = False
    requested_price: float | None = None
    tick_adjustment: str = ""


@dataclass(frozen=True)
class ExecutionRules:
    custo_por_contrato_lado: float = 0.0
    slippage_ticks: float = 0.0
    limite_exige_ultrapassar: bool = False
    ordem_so_proxima_barra: bool = True
    historico_continuo: bool = True
    latencia_barras: int = 0
    motor_ticks: bool = False
    latencia_ticks_ms: int = 0
    lacuna_ticks_ms: int = 5000
    volume_financeiro_ntsl: bool = False
    agressao_por_barra: bool = False
    agressao_referencia_injetada: bool = False
    vwap_continuo_lacunas: bool = False
    protecao_no_candle_entrada: bool = False
    rastrear_ordens: bool = False
    avaliacao_pos_preenchimento: bool = False
    historico_continuo_lacunas: bool = False
    entrada_mercado_atraves_lacuna: bool = False
    protecoes_ate_cancelar: bool = False
    ajuste_tick_saidas_venda: bool = False

    def __post_init__(self):
        for value in (self.latencia_ticks_ms, self.lacuna_ticks_ms):
            if type(value) is not int or not 0 <= value <= 86_400_000:
                raise ValueError("Latência e lacuna tick a tick devem estar entre 0 e 86400000 ms.")
        if type(self.motor_ticks) is not bool:
            raise ValueError("motor_ticks deve ser booleano.")
        if self.motor_ticks and self.latencia_barras:
            raise ValueError("Para tick a tick, zere a latência em barras e use a latência em milissegundos.")
        if self.ajuste_tick_saidas_venda and self.motor_ticks:
            raise ValueError("--ajuste-tick-saidas-venda só se aplica ao motor OHLC.")
        if self.protecoes_ate_cancelar and self.motor_ticks:
            raise ValueError("--protecoes-ate-cancelar só se aplica ao motor OHLC.")
        if self.entrada_mercado_atraves_lacuna and self.motor_ticks:
            raise ValueError("A entrada a mercado através de lacuna só se aplica ao motor OHLC.")
        if self.entrada_mercado_atraves_lacuna and not self.historico_continuo_lacunas:
            raise ValueError("--entrada-mercado-atraves-lacuna exige --historico-continuo-lacunas.")
        if self.motor_ticks and self.historico_continuo_lacunas:
            raise ValueError("A continuidade histórica em lacunas só se aplica ao motor OHLC.")
        if self.motor_ticks and self.protecao_no_candle_entrada:
            raise ValueError("A proteção no candle da entrada só se aplica ao motor OHLC.")
        if self.avaliacao_pos_preenchimento and (self.motor_ticks or self.protecao_no_candle_entrada):
            raise ValueError("A avaliação pós-preenchimento exige OHLC e substitui a proteção no candle da entrada.")
        if type(self.latencia_barras) is not int or self.latencia_barras < 0:
            raise ValueError("A latência adicional deve ser um inteiro não negativo em barras.")
        for value in (self.custo_por_contrato_lado, self.slippage_ticks):
            if type(value) not in {int, float} or not math.isfinite(value) or value < 0:
                raise ValueError("Custo e slippage devem ser números finitos e não negativos.")
        for value in (self.limite_exige_ultrapassar, self.ordem_so_proxima_barra,
                      self.historico_continuo, self.volume_financeiro_ntsl,
                      self.agressao_por_barra, self.agressao_referencia_injetada,
                      self.vwap_continuo_lacunas, self.protecao_no_candle_entrada,
                      self.rastrear_ordens, self.avaliacao_pos_preenchimento,
                      self.historico_continuo_lacunas, self.entrada_mercado_atraves_lacuna,
                      self.protecoes_ate_cancelar, self.ajuste_tick_saidas_venda):
            if type(value) is not bool:
                raise ValueError("As regras de execução devem ser booleanas.")


class Engine:
    def __init__(self, program, frame, tick, overrides, seconds, point_value,
                 series_data=None, history=None, days=None, regras=None):
        self.program, self.frame, self.tick = program, frame, float(tick)
        if not math.isfinite(self.tick) or self.tick <= 0:
            raise ValueError("O tick precisa ser positivo.")
        self.point_value = float(point_value)
        if not math.isfinite(self.point_value) or self.point_value <= 0:
            raise ValueError("O valor por ponto precisa ser positivo.")
        self.rules = ExecutionRules(**(regras or {}))
        self.price_tick = Fraction(str(self.tick)) if self.rules.ajuste_tick_saidas_venda else None
        self.tick_adjustments = {"ajustado": 0, "empate_meio_tick": 0}
        self.costs = self.daily_costs = 0.0
        self.values = program.defaults.copy()
        self.arrays = {symbol.slot: [0.0]*(program.defaults[symbol.slot][1]-program.defaults[symbol.slot][0]+1)
                       for symbol in program.symbols.values() if symbol.kind == "array"}
        self.loop_budget = 0
        self.series_data = (self.prepare_series(program, frame, self.rules)
                            if series_data is None else series_data)
        self.days = frame["pregao"].to_numpy() if days is None else days
        self.gap = (frame["lacuna_intradiaria"].to_numpy(dtype=bool) if "lacuna_intradiaria" in frame
                    else np.r_[False, (frame["segmento"].to_numpy()[1:] != frame["segmento"].to_numpy()[:-1])
                                    & (self.days[1:] == self.days[:-1])] if "segmento" in frame else np.zeros(len(frame), bool))
        history_resets = self.gap & (not self.rules.historico_continuo_lacunas)
        self.segment_starts = np.maximum.accumulate(np.where(history_resets, np.arange(len(frame)), 0))
        self.orders_cancelled_at_gaps = self.gaps_with_exposure = 0
        self.checkpoint = None
        for name, value in overrides.items():
            name = name.lower()
            if name not in program.inputs:
                raise ValueError(f"Input NTSL desconhecido: {name}.")
            if not isinstance(value,(int,float,bool,str)) or (not isinstance(value,str) and not math.isfinite(value)):
                raise ValueError(f"O input {name} requer texto, número finito ou booleano.")
            self.values[program.symbols[name].slot] = value
        self.ignored_asset = any(symbol.kind == "asset" for symbol in program.symbols.values())
        self.seconds = seconds
        self.history = np.empty((len(frame),len(self.values)), dtype=float) if history is None else history
        tick_input = program.symbols.get("p_exec_tick")
        if not self.rules.motor_ticks and "p_exec_tick" in program.inputs and self.values[tick_input.slot] != 0:
            raise ValueError("O replay roda por candle. Ajuste p_Exec_Tick para 0.")
        self.variable_slots = [s.slot for s in program.symbols.values()
                               if s.kind in {"float","real","boolean","integer"}]
        self.row = self.cursor = self.session_start = self.completed = 0
        self.position = 0
        self.basis = self.daily = self.realized = 0.0
        self.orders = {}
        self.fills = []
        self.logs = []
        self.plots = {}
        self.trace = []
        self.rolling = {}
        self.ambiguities = 0
        self.entry_intentions = set()
        self.order_events = []
        self.opening_evaluation_row = None

    def audit_order(self, event, order=None, key="", execution_price=""):
        if not self.rules.rastrear_ordens:
            return
        row = self.row if self.opening_evaluation_row is None else self.opening_evaluation_row
        timestamp = ""
        for column in ("timestamp", "inicio", "minuto"):
            if column in self.frame:
                timestamp = self.frame.iloc[row][column]
                break
        record = dict(
            barra=row+1, pregao=self.days[row], timestamp=timestamp,
            evento=event, chave=key,
            ordem="" if order is None else order.function,
            acao="" if order is None else order.action,
            tipo="" if order is None else order.kind,
            quantidade="" if order is None else order.quantity,
            gatilho="" if order is None else order.price,
            limite="" if order is None or order.limit is None else order.limit,
            preco_execucao=execution_price,
            primeira_barra_elegivel="" if order is None else order.eligible_at+1,
            posicao=self.position, preco_medio=self.basis,
        )
        if self.rules.avaliacao_pos_preenchimento:
            record["barra_contexto_ntsl"] = self.row+1
        if self.rules.ajuste_tick_saidas_venda:
            priced = order is not None and order.kind in {"limit", "stop"} and order.price > 0
            requested = order.requested_price if priced and order.requested_price is not None else (
                order.price if priced else ""
            )
            limit = order.limit if priced and order.limit is not None else ""
            record.update(nivel_solicitado=requested, nivel_efetivo=order.price if priced else "",
                          limite_solicitado=limit, limite_efetivo=limit,
                          ajuste_tick=order.tick_adjustment if priced else "")
        self.order_events.append(record)

    @staticmethod
    def prepare_series(program, frame, regras=None):
        rules = regras if isinstance(regras, ExecutionRules) else ExecutionRules(**(regras or {}))
        series_data = {}
        required = {name: SERIES[name] for name in program.used & SERIES.keys()}
        if "volume" in required and rules.volume_financeiro_ntsl:
            required["volume"] = "volume_financeiro"
        for name, column in (("totalbuyqtd","v_qtd_compra_book"),
                             ("totalsellqtd","v_qtd_venda_book")):
            if name in program.used:
                required[name] = column
        required.update({key: SERIES[key] for key in ("open","high","low","close")})
        for name, column in required.items():
            if column not in frame:
                raise ValueError(f"{name} precisa da coluna {column} no CSV.")
            values = pd.to_numeric(frame[column], errors="raise").to_numpy(dtype=float)
            if not np.isfinite(values).all():
                raise ValueError(f"A coluna {column} contém dados ausentes ou inválidos.")
            series_data[name] = values
        if "vwap" in program.used:
            volume_col = "volume_contratos" if "volume_contratos" in frame else "volume"
            if volume_col not in frame:
                raise ValueError("VWAP exige volume_contratos ou volume no CSV.")
            volume = pd.to_numeric(frame[volume_col]).astype(float)
            price = (pd.to_numeric(frame["v_vwap_barra"]) if "v_vwap_barra" in frame else
                     (series_data["high"] + series_data["low"] + series_data["close"])/3)
            if not np.isfinite(volume).all() or (volume < 0).any() or not np.isfinite(price).all():
                raise ValueError("VWAP recebeu preço ou volume inválido.")
            dates = pd.to_datetime(frame["pregao"])
            gap_epoch = (pd.Series(0, index=frame.index) if rules.vwap_continuo_lacunas else
                         frame.get("lacuna_intradiaria", pd.Series(False, index=frame.index)).cumsum())
            turnover = volume * price
            series_data["vwap_0"] = np.where(volume > 0, price, 0.0)
            for period, group in enumerate((dates, dates.dt.to_period("W-SUN"), dates.dt.to_period("M")), 1):
                total = volume.groupby([group, gap_epoch], sort=False).cumsum()
                weighted = turnover.groupby([group, gap_epoch], sort=False).cumsum()
                series_data[f"vwap_{period}"] = weighted.div(total.where(total > 0)).fillna(0).to_numpy()
        if "agressionvolbalance" in program.used:
            if rules.agressao_referencia_injetada:
                if "v_agressao_saldo_referencia" not in frame:
                    raise ValueError("Agressao de referencia exige v_agressao_saldo_referencia no CSV.")
                balance = pd.to_numeric(frame["v_agressao_saldo_referencia"])
            elif "v_agressao_saldo_acumulado" in frame:
                balance = pd.to_numeric(frame["v_agressao_saldo_acumulado"])
            else:
                cols = {"v_agressao_compra", "v_agressao_venda"}
                if not cols <= set(frame.columns):
                    raise ValueError("AgressionVolBalance exige o saldo acumulado ou as duas colunas de agressão do CSV.")
                buy, sell = (pd.to_numeric(frame[c]) for c in ("v_agressao_compra", "v_agressao_venda"))
                if (buy < 0).any() or (sell < 0).any():
                    raise ValueError("Informe volumes de agressão compradora e vendedora não negativos.")
                if rules.agressao_por_barra:
                    balance = buy-sell
                else:
                    gap_epoch = frame.get("lacuna_intradiaria", pd.Series(False, index=frame.index)).cumsum()
                    balance = (buy-sell).groupby([frame["pregao"], gap_epoch], sort=False).cumsum()
            if not np.isfinite(balance).all():
                raise ValueError("AgressionVolBalance recebeu dados inválidos.")
            series_data["agressionvolbalance"] = balance.to_numpy(dtype=float)
        return series_data

    @property
    def history_start(self):
        return max(int(self.segment_starts[self.cursor]), 0 if self.rules.historico_continuo else self.session_start)

    def series(self, name, offset=0):
        index = self.cursor - self.integer(offset,0)
        return float(self.series_data[name][index]) if index >= self.history_start else 0.0

    def read(self, slot):
        if self.cursor == self.row or isinstance(self.values[slot], (tuple,str)):
            return self.values[slot]
        return self.history[self.cursor,slot]

    def lag(self, slot, offset):
        index = self.cursor - self.integer(offset,0)
        if index < self.history_start:
            return self.program.defaults[slot]
        return self.read(slot) if index == self.cursor else float(self.history[index,slot])

    @staticmethod
    def integer(value, lower):
        if not isinstance(value,(int,float,np.number)) or not np.isfinite(value) or int(value) != value or value < lower:
            raise NTSLError(f"esperado inteiro >= {lower}, recebido {value}.")
        return int(value)

    @staticmethod
    def cast(kind, value):
        if kind == "boolean":
            return bool(value)
        return int(value) if kind == "integer" else float(value)

    def loop_step(self):
        self.loop_budget -= 1
        if self.checkpoint and self.loop_budget % 1024 == 0:
            self.checkpoint()
        if self.loop_budget < 0:
            raise NTSLError("limite de 100.000 iterações por candle atingido.")

    def iterate(self, start, end, step):
        start, end = self.integer(start, -10**12), self.integer(end, -10**12)
        for value in range(start, end+step, step):
            self.loop_step()
            yield value

    def array_index(self, slot, index):
        lower, upper, _ = self.program.defaults[slot]
        index = self.integer(index, lower)
        if index > upper:
            raise NTSLError(f"índice {index} fora do array [{lower}..{upper}].")
        return index-lower

    def read_array(self, slot, index):
        return self.arrays[slot][self.array_index(slot,index)]

    def write_array(self, slot, index, value):
        self.arrays[slot][self.array_index(slot,index)] = self.cast(self.program.defaults[slot][2], value)

    @staticmethod
    def add(a,b):
        return str(a)+str(b) if isinstance(a,str) or isinstance(b,str) else a+b

    @staticmethod
    def divide(a,b):
        if not b:
            raise NTSLError("divisão por zero.")
        return a/b

    def average(self, key, kind, count, value):
        period = self.integer(count,1)
        if period > 100_000:
            raise NTSLError("janela máxima de 100.000 barras.")
        saved_row = self.cursor
        state = self.rolling.get(key)
        if state is None or state.window.maxlen != period or state.row > saved_row:
            state = self.rolling[key] = Rolling(period)
        if saved_row == state.row:
            return state.value
        first = max(self.history_start,state.row+1)
        if kind not in {"mediaexp", "wilder"}:
            first = max(first,saved_row-period+1)
        try:
            for index in range(first,saved_row+1):
                self.cursor = index
                state.update(index,float(value()),kind)
        finally:
            self.cursor = saved_row
        return state.value

    def shift_call(self, offset, callback):
        index = self.cursor-self.integer(offset,0)
        if index < self.history_start:
            return 0.0
        original = self.cursor
        self.cursor = index
        try:
            return callback()
        finally:
            self.cursor = original

    def atr(self, key, period, kind):
        kind = self.integer(kind,0)
        kinds = ("media", "mediaexp", "wilder", "weighted")
        if kind >= len(kinds):
            raise NTSLError("AvgTrueRange aceita tipo de média entre 0 e 3.")
        return self.average(key,kinds[kind],period,lambda: self.call("truerange"))

    def state(self, name):
        return {
            "isbought": self.position>0, "issold": self.position<0,
            "hasposition": self.position!=0, "haspendingorders": bool(self.orders),
            "buyprice": self.basis if self.position>0 else 0,
            "sellprice": self.basis if self.position<0 else 0,
            "price": self.basis, "position": self.position,
            "buyposition": max(0,self.position), "sellposition": max(0,-self.position),
            "minpriceincrement": self.tick, "positionqty": self.position,
            "buypositionqty": max(0,self.position), "sellpositionqty": max(0,-self.position),
        }[name]

    @staticmethod
    def remainder(dividend, divisor):
        dividend, divisor = int(dividend), int(divisor)
        if not divisor:
            raise NTSLError("divisão por zero em Mod.")
        result = abs(dividend) % abs(divisor)
        return -result if dividend < 0 else result

    def call(self, name, *args):
        math_calls = {"abs": abs, "max": max, "min": min, "sqrt": math.sqrt, "round": round,
                      "floor": math.floor, "ceiling": math.ceil, "power": pow,
                      "mod": self.remainder,
                      "intportion": math.trunc, "fracportion": lambda x: math.modf(x)[0],
                      "square": lambda x: x*x, "sign": lambda x: int(x>0)-int(x<0),
                      "log": math.log, "exp": math.exp}
        if name in math_calls:
            return math_calls[name](*args)
        if name == "calctime":
            hhmm, delta = self.integer(args[0], 0), int(args[1])
            hour, minute = divmod(hhmm, 100)
            if hour > 23 or minute > 59:
                raise NTSLError("CalcTime exige horário HHMM válido.")
            hour, minute = divmod((hour*60 + minute + delta) % 1440, 60)
            return hour*100 + minute
        if name == "truerangecustom":
            high, low, previous = args
            return max(high,previous)-min(low,previous)
        if name in {"truerange", "truehigh", "truelow", "typicalprice", "medianprice", "avgprice"}:
            high, low = self.series("high"), self.series("low")
            if name == "medianprice":
                return (high+low)/2
            if name == "typicalprice":
                return (high+low+self.series("close"))/3
            if name == "avgprice":
                return (high+low+self.series("open")+self.series("close"))/4
            prev = self.series("close",1) if self.cursor>self.history_start else self.series("open")
            upper, lower = max(high,prev), min(low,prev)
            return upper if name=="truehigh" else lower if name=="truelow" else upper-lower
        if name == "vwap":
            period = self.integer(args[0],0)
            if period > 3:
                raise NTSLError("VWAP exige período entre 0 e 3.")
            return self.series(f"vwap_{period}")
        if name == "agressionvolbalance":
            return self.series(name)
        if name == "dailyresult":
            unrealized = (self.series("close")-self.basis)*self.position if args and args[0] else 0
            return (self.daily + unrealized) * self.point_value - self.daily_costs
        if name in {"totalbuyqtd","totalsellqtd"}:
            return self.series(name)
        if name == "sendorder":
            side, kind, qty, limit, stop = args
            side_map = {ORDER_CONSTANTS["osbuy"]: "net_long", ORDER_CONSTANTS["ossell"]: "net_short"}
            type_map = {ORDER_CONSTANTS["otmarket"]: "market", ORDER_CONSTANTS["otlimit"]: "limit",
                        ORDER_CONSTANTS["otstoplimit"]: "stop"}
            if side not in side_map or kind not in type_map:
                raise NTSLError("SendOrder exige osBuy/osSell e otMarket/otLimit/otStopLimit.")
            kind = type_map[kind]
            price = float(stop if kind == "stop" else limit)
            limit = float(limit) if kind == "stop" else None
            if kind != "market" and (not math.isfinite(price) or price <= 0):
                raise NTSLError("preço inválido em SendOrder.")
            if kind == "stop" and (not math.isfinite(limit) or limit <= 0 or
                                  (limit < price if side_map[side] == "net_long" else limit > price)):
                raise NTSLError("limite inválido em SendOrder stop-limit.")
            quantity = self.integer(qty,1)
            key = f"sendorder_{side}_{kind}"
            self.place(key, Order(name, side_map[side], kind, quantity, price, limit))
            if side_map[side] == "net_long" and quantity > -self.position:
                self.entry_intentions.add("long")
            if side_map[side] == "net_short" and quantity > self.position:
                self.entry_intentions.add("short")
        elif name == "reverseposition":
            if self.position:
                self.orders.clear()
                action = "net_short" if self.position>0 else "net_long"
                self.place(name, Order(name,action,"market",2*abs(self.position)))
                self.entry_intentions.add("short" if self.position>0 else "long")
        elif name == "cancelpendingorders":
            self.orders.clear()
        elif name == "consolelog":
            if len(self.logs) < 10_000:
                self.logs.append((self.row+1,str(args[0])))
        elif name.startswith("plot") or name == "paintbar":
            self.plots[name] = float(args[0])
        else:
            self.queue(name,args)
        return 0

    def queue(self,name,args):
        if name == "closeposition":
            if not self.position:
                return
            action = "exit_long" if self.position>0 else "exit_short"
            self.orders.clear()
            self.place(name, Order(name,action,"market",abs(self.position)))
            return
        prefix = next(prefix for prefix in ("selltocover","buytocover","sellshort","buyat")
                      if name.startswith(prefix))
        action = {"selltocover":"exit_long","buytocover":"exit_short",
                  "sellshort":"short","buyat":"long"}[prefix]
        kind = next(kind for kind in ("market","limit","stop") if name.endswith(kind))
        exit_order = action.startswith("exit")
        if (action == "exit_long" and self.position<=0) or (action == "exit_short" and self.position>=0):
            return
        # Entradas do lado oposto exigem zerar antes, como nas funções *ToCover.
        if (action == "long" and self.position<0) or (action == "short" and self.position>0):
            return
        quantity = abs(self.position) if exit_order else 1
        price,limit = 0,None
        if kind == "market":
            if args:
                quantity = self.integer(args[0],1)
        else:
            price = float(args[0])
            if kind == "stop":
                limit = float(args[1]) if len(args)>1 else None
                if limit == 0:
                    limit = None
                if len(args)>2:
                    quantity = self.integer(args[2],1)
                buying = action in {"long","exit_short"}
                if limit is not None and ((buying and limit<price) or (not buying and limit>price)):
                    raise NTSLError("preço limite do stop no lado incorreto do gatilho.")
            elif len(args)>1:
                quantity = self.integer(args[1],1)
            if not math.isfinite(price) or price <= 0 or (limit is not None and
                                                         (not math.isfinite(limit) or limit<=0)):
                raise NTSLError("preço inválido na ordem.")
        self.place(name, Order(name,action,kind,quantity,price,limit))
        if not exit_order:
            self.entry_intentions.add(action)

    def adjust_sell_exit(self, order):
        order.requested_price = order.price
        # As representações decimais passam a frações exatas para evitar erro na comparação do meio tick.
        units, remainder = divmod(Fraction(str(order.price)), self.price_tick)
        if remainder == 0:
            order.tick_adjustment = "na_grade"
            return
        if 2 * remainder == self.price_tick:
            order.tick_adjustment = "empate_meio_tick"
        else:
            nearest = units + (2 * remainder > self.price_tick)
            if nearest == 0:
                raise NTSLError("O nível ajustado ao tick precisa ser positivo.")
            order.price = float(nearest * self.price_tick)
            order.tick_adjustment = "ajustado"
        self.tick_adjustments[order.tick_adjustment] += 1

    def place(self, key, order):
        if self.opening_evaluation_row is not None:
            exit_action = "exit_long" if self.position > 0 else "exit_short"
            if order.action != exit_action or order.kind not in {"limit", "stop"}:
                return
        if self.price_tick is not None and order.action == "exit_long" and order.kind in {"limit", "stop"}:
            self.adjust_sell_exit(order)
        old = self.orders.get(key)
        order.requested_quantity = order.quantity
        order.market_entry = order.kind == "market" and (
            order.action in {"long", "short"}
            or (self.position == 0 and order.action in {"net_long", "net_short"})
        )
        same_order = old and (old.price, old.limit, old.requested_quantity or old.quantity) == (
            order.price, order.limit, order.quantity)
        if same_order:
            order.triggered = old.triggered
            order.quantity = old.quantity
        order.eligible_at = old.eligible_at if same_order else self.row+1+self.rules.latencia_barras
        if self.rules.motor_ticks:
            order.eligible_ns = (old.eligible_ns if same_order else
                                 int(self.event_time[self.row])+self.rules.latencia_ticks_ms*1_000_000)
        order.sent_at = self.row
        self.orders[key] = order
        self.audit_order("solicitacao_renovada" if same_order else "solicitacao", order, key)
        if order.tick_adjustment == "empate_meio_tick":
            self.audit_order("empate_meio_tick", order, key)

    def slipped(self, price, buying):
        return price + (1 if buying else -1) * self.rules.slippage_ticks * self.tick

    def match(self, order,o,h,l):
        buying = order.action in {"long","exit_short","net_long"}
        price = order.price
        if order.kind == "market":
            return self.slipped(o, buying)
        if order.kind == "stop" and not order.triggered:
            touched = h>=price if buying else l<=price
            if not touched:
                return None
            order.triggered = True
            fill = self.slipped(max(o,price) if buying else min(o,price), buying)
            limit = order.limit
            if limit is None or (fill<=limit if buying else fill>=limit):
                return fill
            # A volta até o limite na mesma barra é indeterminada após gap.
            return None
        limit = order.limit if order.kind == "stop" else price
        if limit is None:
            return o
        penetration = self.tick if self.rules.limite_exige_ultrapassar else 0
        if buying and l<=limit-penetration:
            return min(o,limit)
        if not buying and h>=limit+penetration:
            return max(o,limit)
        return None

    def execute(self, order, price):
        action, quantity = order.action, order.quantity
        old = self.position
        if action in {"net_long", "net_short"}:
            direction = 1 if action == "net_long" else -1
            if old*direction < 0:
                closed = min(quantity,abs(old))
                self.execute(Order(order.function,"exit_short" if direction>0 else "exit_long",
                                   order.kind,closed),price)
                quantity -= closed
            if quantity:
                self.execute(Order(order.function,"long" if direction>0 else "short",order.kind,quantity),price)
            return
        pnl = 0.0
        if action in {"long","short"}:
            direction = 1 if action=="long" else -1
            if old*direction<0:
                return
            self.basis = (self.basis*abs(old)+price*quantity)/(abs(old)+quantity)
            self.position += direction*quantity
        else:
            direction = 1 if action=="exit_long" else -1
            if old*direction<=0:
                return
            quantity = min(quantity,abs(old))
            pnl = (price-self.basis)*quantity*direction
            self.position -= direction*quantity
            self.daily += pnl
            self.realized += pnl
            self.orders = {key:item for key,item in self.orders.items()
                           if not item.action.startswith("exit")}
            if not self.position:
                self.basis = 0.0
        cost = quantity * self.rules.custo_por_contrato_lado
        self.costs += cost
        self.daily_costs += cost
        self.fills.append(dict(barra=self.row+1,pregao=self.days[self.row],
                               ordem=order.function,acao=action,preco=price,quantidade=quantity,
                               pontos_contrato=pnl,posicao=self.position, tipo=order.kind,
                               custo_reais=cost, liquido_reais=pnl*self.point_value-cost))
        self.audit_order("preenchimento", order, order.function, price)

    def is_position_protection(self, order):
        if not self.position:
            return False
        exit_action = "exit_long" if self.position > 0 else "exit_short"
        return order.action == exit_action and (
            order.kind == "limit" or (order.kind == "stop" and order.limit is not None)
        )

    def fill_market_close_at_open(self, opening_price):
        if not any(order.eligible_at <= self.row and self.is_position_protection(order)
                   for order in self.orders.values()):
            return False

        exit_action, net_action = (("exit_long", "net_short") if self.position > 0
                                   else ("exit_short", "net_long"))
        quantity = abs(self.position)
        for key, order in self.orders.items():
            if order.kind != "market" or self.row < order.eligible_at:
                continue
            if ((order.action == exit_action and order.quantity >= quantity)
                    or (order.action == net_action and order.quantity == quantity)):
                # A zeragem na abertura encerra a exposição antes de examinar a faixa da barra.
                self.orders.pop(key)
                self.execute(order, self.slipped(opening_price, exit_action == "exit_short"))
                return True
        return False

    def process_orders(self, only_keys=None):
        o,h,l = (self.series(name) for name in ("open","high","low"))
        if (only_keys is None and self.rules.protecoes_ate_cancelar and self.rules.ordem_so_proxima_barra
                and self.fill_market_close_at_open(o)):
            return
        matched = []
        for key,order in self.orders.items():
            if only_keys is not None and key not in only_keys:
                continue
            if self.row < order.eligible_at:
                continue
            triggered = order.triggered
            fill = self.match(order,o,h,l)
            if not triggered and order.triggered:
                self.audit_order("gatilho_stop", order, key)
            if fill is not None:
                matched.append((key,order,fill))
        exits = [item for item in matched if item[1].action.startswith("exit")]
        if exits:
            if len(exits)>1:
                self.ambiguities += 1
            chosen = min(exits,key=lambda item: (item[1].kind!="market",
                                                item[2] if self.position>0 else -item[2]))
            self.orders.pop(chosen[0],None)
            self.execute(chosen[1],chosen[2])
        else:
            # Quando duas entradas opostas são tocadas, a primeira ordem enviada prevalece.
            if len({item[1].action for item in matched})>1:
                self.ambiguities += 1
            for key,order,fill in matched:
                self.orders.pop(key,None)
                self.execute(order,fill)

    def snapshot(self):
        state = dict(barras=self.completed, inicio_pregao=self.session_start,
                     valores=[self.values[slot] for slot in self.variable_slots],
                     arrays=self.arrays, posicao=self.position, preco_medio=self.basis,
                     diario=self.daily, realizado=self.realized, ordens_canceladas_lacuna=self.orders_cancelled_at_gaps,
                     lacunas_com_posicao=self.gaps_with_exposure, custos=self.costs, custos_diarios=self.daily_costs, ambiguidades=self.ambiguities,
                     ordens=[(key, asdict(order)) for key, order in self.orders.items()],
                     execucoes=self.fills, candles=self.trace, console=self.logs,
                     eventos_ordens=self.order_events,
                     indicadores=[(key, value.window.maxlen, list(value.window),
                                   value.row, value.sum, value.ema, value.value)
                                  for key, value in self.rolling.items()])
        if self.price_tick is not None:
            state["ajustes_tick_saidas_venda"] = self.tick_adjustments.copy()
        return state, self.history[:self.completed]

    def restore(self, state, package):
        completed = state["barras"]
        if type(completed) is not int or not 0 <= completed <= len(self.frame):
            raise ValueError("Quantidade de barras da sessão incompatível.")
        if len(state["valores"]) != len(self.variable_slots) or len(state["candles"]) != completed:
            raise ValueError("Estado do replay incompatível com a estratégia.")
        target = self.history[:completed]
        with ZipFile(package) as archive, archive.open("historico.npy") as member:
            version = np.lib.format.read_magic(member)
            if version != (1, 0):
                raise ValueError("Formato do histórico do replay incompatível.")
            shape, is_fortran, dtype = np.lib.format.read_array_header_1_0(member)
            if shape != target.shape or is_fortran or dtype != target.dtype:
                raise ValueError("Dimensões ou tipo do histórico incompatíveis.")
            if target.nbytes:
                remaining = memoryview(target).cast("B")
                while remaining:
                    count = member.readinto(remaining[:1024**2])
                    if not count:
                        raise ValueError("Histórico do replay incompleto.")
                    remaining = remaining[count:]
            if member.read(1):
                raise ValueError("Histórico do replay contém dados excedentes.")
        self.completed = completed
        self.session_start = state["inicio_pregao"]
        for slot, value in zip(self.variable_slots, state["valores"]):
            self.values[slot] = value
        self.arrays = {int(slot): values for slot, values in state["arrays"].items()}
        self.position, self.basis = state["posicao"], state["preco_medio"]
        self.daily, self.realized = state["diario"], state["realizado"]
        self.costs, self.daily_costs = state.get("custos",0.0), state.get("custos_diarios",0.0)
        self.orders_cancelled_at_gaps = state.get("ordens_canceladas_lacuna", 0)
        self.gaps_with_exposure = state.get("lacunas_com_posicao", 0)
        self.ambiguities = state["ambiguidades"]
        self.tick_adjustments.update(state.get("ajustes_tick_saidas_venda", {}))
        self.orders = {key: Order(**order) for key, order in state["ordens"]}
        self.fills, self.trace, self.logs = state["execucoes"], state["candles"], state["console"]
        self.order_events = state.get("eventos_ordens", [])
        for fill in self.fills:
            fill.setdefault("custo_reais", 0.0)
            fill.setdefault("liquido_reais", fill["pontos_contrato"] * self.point_value)
        for key, period, window, row, total, ema, value in state["indicadores"]:
            if type(period) is not int or not 1 <= period <= 100_000 or len(window) > period:
                raise ValueError("Janela de indicador inválida na sessão.")
            indicator = self.rolling[key] = Rolling(period)
            indicator.window.extend(window)
            indicator.row, indicator.sum, indicator.ema, indicator.value = row, total, ema, value

    def evaluate_strategy(self, event="avaliacao_ntsl"):
        self.plots = {}
        self.entry_intentions = set()
        self.loop_budget = 100_000
        self.audit_order(event)
        try:
            self.program.strategy(self)
        except (ValueError,TypeError,OverflowError,ZeroDivisionError,RecursionError) as error:
            raise NTSLError(f"Barra {self.row+1}, pregão {self.days[self.row]}: {error}") from error

    def protect_at_open(self):
        row = self.row
        values, arrays, rolling, orders = self.values, self.arrays, self.rolling, self.orders
        # A avaliação adicional lê a última barra fechada. Seus escalares
        # passam ao fechamento sem alterar o histórico dessa barra.
        self.values = values.copy()
        self.arrays = {slot: array.copy() for slot, array in arrays.items()}
        self.rolling = deepcopy(rolling)
        self.orders = {key: order for key, order in orders.items()
                       if not order.action.startswith("exit")}
        self.opening_evaluation_row = row
        self.row = self.cursor = row-1
        try:
            self.evaluate_strategy("avaliacao_ntsl_pos_preenchimento")
            protections = {key: order for key, order in self.orders.items()
                           if order.action.startswith("exit")}
            for slot in self.variable_slots:
                values[slot] = self.values[slot]
        finally:
            self.row = self.cursor = row
            self.opening_evaluation_row = None
            self.values, self.arrays, self.rolling, self.orders = values, arrays, rolling, orders
        if protections:
            self.orders.update(protections)
            self.process_orders(protections)

    def run(self, record_trace=True, on_progress=None, checkpoint=None, safe_point=None):
        self.checkpoint = checkpoint
        days = self.days
        var_slots = self.variable_slots
        var_set = set(var_slots)
        constants = [(idx,val) for idx,val in enumerate(self.values) if idx not in var_set]
        numeric_constants = [(idx,0.0 if isinstance(val,(tuple,str)) else val) for idx,val in constants]
        last_update = 0.0
        boundary = safe_point or checkpoint
        for row in range(self.completed, len(self.frame)):
            if boundary and row % 64 == 0:
                boundary()
            self.row = self.cursor = row
            if row==0 or days[row]!=days[row-1]:
                self.session_start = row
                self.daily = self.daily_costs = 0.0
                if not self.rules.historico_continuo:
                    self.rolling.clear()
            carry_market_entries = False
            if self.gap[row]:
                carry_market_entries = self.rules.entrada_mercado_atraves_lacuna and self.position == 0
                orders_before_gap = len(self.orders)
                self.gaps_with_exposure += bool(self.position)
                if carry_market_entries:
                    self.orders = {key: order for key, order in self.orders.items() if order.market_entry}
                else:
                    self.orders.clear()
                cancelled = orders_before_gap - len(self.orders)
                self.orders_cancelled_at_gaps += cancelled
                if not self.rules.historico_continuo_lacunas:
                    self.rolling.clear()
                if record_trace:
                    if self.orders:
                        message = (f"Lacuna de dados. Ordens canceladas: {cancelled}; "
                                   f"entradas a mercado preservadas: {len(self.orders)}; posição anterior: {self.position}.")
                    else:
                        message = f"Lacuna de dados. Ordens canceladas; posição anterior: {self.position}."
                    self.logs.append((row+1, message))
            position_before_orders = self.position
            fills_before_orders = len(self.fills)
            self.process_orders()
            opening_fills = self.fills[fills_before_orders:]
            opened_by_market_at_open = (
                position_before_orders == 0 and self.position != 0
                and any(fill["acao"] in {"long", "short"} and fill["tipo"] == "market"
                        for fill in opening_fills)
            )
            if (self.rules.avaliacao_pos_preenchimento and opened_by_market_at_open
                    and row > self.session_start and (not self.gap[row] or carry_market_entries)
                    and all(fill["acao"] in {"long", "short"} and fill["tipo"] == "market"
                            for fill in opening_fills)):
                self.protect_at_open()
            self.evaluate_strategy()
            if self.rules.protecao_no_candle_entrada and opened_by_market_at_open:
                exit_action = "exit_long" if self.position > 0 else "exit_short"
                # A segunda passagem representa somente proteções vinculadas à
                # entrada a mercado preenchida na abertura. Uma saída a mercado
                # decidida no fechamento nunca pode retroagir para essa abertura.
                protections = [(key, order) for key, order in self.orders.items()
                               if order.sent_at == row
                               and order.action == exit_action
                               and order.kind in {"limit", "stop"}]
                for key, order in protections:
                    order.eligible_at = row
                    self.audit_order("protecao_elegivel_candle_entrada", order, key)
                if protections:
                    self.process_orders({key for key, _ in protections})
            if self.rules.ordem_so_proxima_barra and not self.rules.motor_ticks:
                self.orders = {
                    key: order for key, order in self.orders.items()
                    if order.sent_at == row or order.eligible_at > row
                    or (self.rules.protecoes_ate_cancelar and self.is_position_protection(order))
                }
            for slot in var_slots:
                self.history[row,slot] = self.values[slot]
            for slot,val in numeric_constants:
                self.history[row,slot] = val
            if row+1==len(days) or days[row+1]!=days[row]:
                self.orders.clear()
                if self.position:
                    action = "exit_long" if self.position>0 else "exit_short"
                    self.execute(Order("fim_pregao",action,"market",abs(self.position)),
                                 self.slipped(self.series("close"), action=="exit_short"))
            if on_progress and (row % 256 == 0 or row+1 == len(days)):
                now = monotonic()
                if now-last_update >= .5 or row+1 == len(days):
                    on_progress(dict(etapa='replay', barras=row+1, barras_total=len(days),
                                     resultado=self.realized, liquido_reais=self.realized*self.point_value-self.costs, preenchimentos=len(self.fills)))
                    last_update = now
            if record_trace:
                self.trace.append({"sinal_compra": "long" in self.entry_intentions,
                               "sinal_venda": "short" in self.entry_intentions,
                               "posicao":self.position,"pontos_contrato_acumulados":self.realized,**self.plots})
            self.completed = row + 1


def replay_input(csv, seconds, format_name, rules):
    if rules.motor_ticks:
        from replay_ticks import TickEngine, load_events
        return TickEngine, load_events(csv, format_name, rules)
    return Engine, load_bars(csv, seconds, format_name)


def run_strategy(csv, source, output, seconds, format_name, tick, overrides=None, point_value=1,
                 on_progress=None, checkpoint=None, session=None, resume_archive=None, safe_point=None, regras=None, validacao=None, on_validation=None):
    program = compile_ntsl(source)
    format_name = csv_format(csv, format_name)
    rules = ExecutionRules(**(regras or {}))
    engine_type, frame = replay_input(csv, seconds, format_name, rules)
    engine = engine_type(program,frame,tick,overrides or {},seconds,point_value,regras=regras)
    if session:
        if session.resume is not None:
            engine.restore(session.resume, resume_archive)
        session.snapshot = engine.snapshot
    if safe_point:
        safe_point()
    engine.run(on_progress=on_progress, checkpoint=checkpoint if not session else None, safe_point=safe_point)
    boundary = safe_point or checkpoint
    if boundary:
        boundary()
    if on_progress:
        on_progress(dict(etapa="relatorio", barras=len(frame), barras_total=len(frame),
                         resultado=engine.realized, liquido_reais=engine.realized*point_value-engine.costs, preenchimentos=len(engine.fills)))
    output = Path(output)
    output.mkdir(parents=True,exist_ok=False)
    fills = pd.DataFrame(engine.fills,columns=[
        "barra","pregao","ordem","acao","preco","quantidade","pontos_contrato","posicao","tipo","custo_reais","liquido_reais"])
    if rules.motor_ticks:
        for column in ("timestamp", "sequencia_evento", "fechamento_sintetico"):
            fills[column] = [fill[column] for fill in engine.fills]
    fills.to_csv(output/"execucoes.csv",index=False)
    columns = [key for key in ("timestamp","sequencia","inicio","minuto","ordem_no_minuto","v_barra_id",
                               "pregao","segmento","lacuna_intradiaria","intervalo_barra_segundos","barras_no_segmento",*OHLC,"classe") if key in frame]
    trace = pd.concat([frame[columns],pd.DataFrame(engine.trace)],axis=1)
    trace.to_csv(output/"candles.csv",index_label="indice")
    pd.DataFrame(engine.logs,columns=["barra","mensagem"]).to_csv(output/"console.csv",index=False)
    if rules.rastrear_ordens:
        pd.DataFrame(engine.order_events).to_csv(output/"eventos_ordens.csv",index=False)
    exits = fills[fills.acao.str.startswith("exit")] if len(fills) else fills
    pnl = exits["pontos_contrato"].to_numpy(dtype=float)
    equity = np.r_[0,pnl.cumsum()]
    liquid_equity = np.r_[0,fills["liquido_reais"].fillna(0).to_numpy(dtype=float).cumsum()]
    summary = dict(versao=Path(__file__).with_name("VERSION").read_text().strip(),
                   estrategia_sha256=hashlib.sha256(source.encode()).hexdigest(),
                   barras=len(frame),pregoes=int(frame["pregao"].nunique()),
                   sinais_compra=int(trace.sinal_compra.sum()),sinais_venda=int(trace.sinal_venda.sum()),
                   preenchimentos=len(fills),saidas=len(exits),saidas_positivas=int((pnl>0).sum()),
                   saidas_negativas=int((pnl<0).sum()),pontos_contrato=engine.realized,
                   drawdown_pontos_contrato=float((np.maximum.accumulate(equity)-equity).max()),
                   barras_ambiguas=engine.ambiguities, lacunas_intradiarias=int(engine.gap.sum()),
                   lacunas_com_posicao=engine.gaps_with_exposure, ordens_canceladas_lacuna=engine.orders_cancelled_at_gaps, formato_csv=FORMATS[format_name][0],
                   motor_execucao="tick_a_tick" if rules.motor_ticks else "candle",
                   eventos=len(frame) if rules.motor_ticks else None,
                   intervalo_segundos=None if rules.motor_ticks else seconds,tick=tick,
                   valor_por_ponto=point_value,resultado_bruto_convertido=engine.realized*point_value,
                   custos_reais=engine.costs, resultado_liquido_reais=engine.realized*point_value-engine.costs,
                   drawdown_liquido_reais=float((np.maximum.accumulate(liquid_equity)-liquid_equity).max()),
                   regras_execucao=asdict(engine.rules),
                   inputs=program.inputs|{k.lower():v for k,v in (overrides or {}).items()},
                   usa_asset_snapshot=engine.ignored_asset)
    if rules.ajuste_tick_saidas_venda:
        summary["ajustes_tick_saidas_venda"] = engine.tick_adjustments
    else:
        del summary["regras_execucao"]["ajuste_tick_saidas_venda"]
    validation_graphs = ""
    validation_links = ""
    if validacao is not None:
        from validacao import export_validation
        stats, validation_graphs = export_validation(output, frame, engine.fills, summary, validacao)
        summary.update(stats)
        validation_links = (' · <a href="validacao.csv">CSV para conferência</a>'
                            ' · <a href="nota_corretagem_simulada.pdf">Nota simulada em PDF</a>')
        if on_validation:
            on_validation(stats, validation_graphs)
    (output/"metricas.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding="utf-8")
    (output/"estrategia.ntsl").write_text(source,encoding="utf-8")
    table = "".join(f"<tr><th>{html.escape(k.replace('_',' '))}</th><td>{html.escape(str(v))}</td></tr>"
                    for k,v in summary.items() if k!="inputs")
    sample = sorted(set(np.linspace(0, len(liquid_equity)-1, min(len(liquid_equity), 350), dtype=int)))
    payoff = [{"geracao": int(i), "resultado": float(liquid_equity[i])} for i in sample]
    performance = chart(payoff, [("resultado", "R$ líquido")], "Resultado líquido realizado", axis="Execução")
    report_title = "Validação do modelo" if validacao is not None else "Replay NTSL"
    order_link = ' · <a href="eventos_ordens.csv">Ciclo das ordens</a>' if rules.rastrear_ordens else ''
    items = '<a href="execucoes.csv">Execuções</a> · <a href="candles.csv">Candles e sinais</a> · <a href="console.csv">Console</a>' + order_link + ' · <a href="metricas.json">Métricas e inputs</a>'
    if rules.motor_ticks:
        description = ("O código é executado a cada negócio. Ordens novas ficam elegíveis em evento posterior. "
                       "O preenchimento usa preço e quantidade observados, sem posição real na fila.")
    elif rules.avaliacao_pos_preenchimento:
        description = ("Na abertura, uma entrada a mercado a partir de posição zerada permite criar proteções "
                       "com a barra anterior. O fechamento avalia a posição resultante.")
    elif rules.protecao_no_candle_entrada:
        description = ("O código roda uma vez por candle. Entradas novas são elegíveis na barra seguinte; "
                       "a proteção criada após uma entrada a mercado também é testada no candle da entrada.")
    else:
        description = "O código roda no fechamento de cada candle. Ordens novas só são elegíveis na barra seguinte."
    (output/"relatorio.html").write_text(f"""<!doctype html><html lang="pt-BR"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{report_title}</title>
<style>
body{{font:16px system-ui;max-width:850px;margin:3rem auto;padding:0 1.1rem;background:#f2f7f6;color:#172e2b}}
h1{{font-size:2.3rem}}table{{border-collapse:collapse;width:100%;background:white}}
th,td{{text-align:left;padding:.6rem 1rem;border-bottom:1px solid #d9e4e1}}a{{color:#146253}}
figure{{margin:1rem 0;background:white;padding:1rem}} svg{{width:100%;max-height:245px;font-size:11px}}
</style><h1>{report_title}</h1><p>{items}{validation_links}</p>
<p>{description}
O bruto usa os preços simulados após slippage. O líquido deduz as taxas configuradas por contrato e lado.
A sequência intrabar e a fila do livro permanecem indeterminadas.</p>
{validation_graphs or performance}<table>{table}</table></html>""",encoding="utf-8")
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv",required=True)
    p.add_argument("--ntsl",required=True)
    p.add_argument("--saida",required=True)
    p.add_argument("--segundos",type=int,required=True)
    p.add_argument("--formato",choices=["auto", "profit", "negocios", "ohlc", "integrado"],default="auto")
    p.add_argument("--tick",type=float,default=5)
    p.add_argument("--valor-ponto",type=float,default=1,help="Multiplicador de DailyResult e do resultado bruto")
    p.add_argument("--custo-por-contrato-lado", type=float, default=0)
    p.add_argument("--slippage-ticks", type=float, default=0)
    p.add_argument("--limite-exige-ultrapassar", action="store_true")
    p.add_argument("--ordem-so-proxima-barra", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--protecoes-ate-cancelar", action="store_true",
                   help="OHLC experimental: mantém saídas limite e stop-limit compatíveis em barras consecutivas")
    p.add_argument("--ajuste-tick-saidas-venda", action="store_true",
                   help="OHLC experimental: aproxima alvo limite e gatilho de stop das saídas de posição comprada")
    p.add_argument("--latencia-barras", type=int, default=0)
    p.add_argument("--historico-continuo", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--historico-continuo-lacunas", action="store_true",
                   help="OHLC: preserva janelas e referências históricas em lacunas intradiárias")
    p.add_argument("--entrada-mercado-atraves-lacuna", action="store_true",
                   help="OHLC experimental: preserva entradas a mercado com posição zerada; exige histórico contínuo em lacunas")
    p.add_argument("--motor-ticks", action="store_true")
    p.add_argument("--latencia-ticks-ms", type=int, default=0)
    p.add_argument("--lacuna-ticks-ms", type=int, default=5000)
    p.add_argument("--volume-financeiro-ntsl", action="store_true",
                   help="Modo de paridade: Volume NTSL usa volume_financeiro")
    p.add_argument("--agressao-por-barra", action="store_true",
                   help="Diagnostico: AgressionVolBalance nao acumula por segmento")
    p.add_argument("--agressao-referencia-injetada", action="store_true",
                   help="Diagnostico: usa v_agressao_saldo_referencia exportado do Profit")
    p.add_argument("--vwap-continuo-lacunas", action="store_true",
                   help="Diagnostico: VWAP diaria nao reinicia em lacuna intradiaria")
    p.add_argument("--protecao-no-candle-entrada", action="store_true",
                   help="OHLC de paridade: testa somente alvo/stop novos no candle da entrada a mercado preenchida na abertura")
    p.add_argument("--avaliacao-pos-preenchimento", action="store_true",
                   help="OHLC experimental: cria proteções na abertura com o contexto da barra anterior")
    p.add_argument("--rastrear-ordens", action="store_true",
                   help="Grava solicitacoes, elegibilidade, gatilhos, preenchimentos e posicao vista pelo NTSL")
    p.add_argument("--inputs",help="Arquivo JSON com valores de inputs a substituir")
    args=p.parse_args()
    try:
        with cli_audit(args.saida, args.csv, "estrategia"):
            overrides=json.loads(Path(args.inputs).read_text(encoding="utf-8-sig")) if args.inputs else {}
            print(json.dumps(run_strategy(args.csv,source_text(args.ntsl),args.saida,args.segundos,
                                          args.formato,args.tick,overrides,args.valor_ponto,
                                          regras={key:getattr(args,key) for key in ExecutionRules.__dataclass_fields__}),ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError) as error:
        p.exit(2,f"Erro: {error}\n")


class StrategyReplay:
    """Executa o NTSL com cada conjunto de inputs do otimizador."""
    def __init__(self, frame, program, seconds, target, specification, excluded, tick, point_value, regras=None):
        from diagnostico import BLOCKED, labels

        self.frame, self.program, self.seconds = frame, program, seconds
        self.target, self.specification = target, specification or {}
        self.excluded = set(excluded) | BLOCKED
        inputs = {SERIES[name] for name in program.used & SERIES.keys()}
        execution_rules = ExecutionRules(**(regras or {}))
        if "volume" in program.used and execution_rules.volume_financeiro_ntsl:
            inputs.discard("volume")
            inputs.add("volume_financeiro")
        if program.used & {"truerange","truehigh","truelow","typicalprice","medianprice","avgprice","avgtruerange"}:
            inputs |= set(OHLC)
        if "dailyresult" in program.used:
            inputs.add("fechamento")
        inputs |= {column for name, column in (("totalbuyqtd", "v_qtd_compra_book"),
                                               ("totalsellqtd", "v_qtd_venda_book")) if name in program.used}
        if "vwap" in program.used:
            inputs |= {"v_vwap_barra"} if "v_vwap_barra" in frame else {"maxima", "minima", "fechamento"}
            inputs.add("volume_contratos" if "volume_contratos" in frame else "volume")
        if "agressionvolbalance" in program.used:
            if execution_rules.agressao_referencia_injetada:
                inputs.add("v_agressao_saldo_referencia")
            else:
                inputs |= ({"v_agressao_saldo_acumulado"} if "v_agressao_saldo_acumulado" in frame
                           else {"v_agressao_compra", "v_agressao_venda"})
        conflicts = inputs & self.excluded
        if conflicts:
            raise ValueError("O NTSL lê campos excluídos: " + ", ".join(sorted(conflicts))
                             + ". Altere o código ou a seleção para executar a estratégia.")
        self.tick, self.point_value, self.rules = tick, point_value, regras
        self.day = frame["pregao"].to_numpy()
        self.defaults = program.inputs
        self.in_memory = False
        self.prepared_series = None
        self.history_buffer = None
        if self.specification.get("modo") == "resultado":
            self.label, self.valid_label = np.zeros(len(frame), bool), np.ones(len(frame), bool)
        else:
            self.label, self.valid_label = labels(frame, target, self.specification)

    def subset(self, mask):
        return StrategyReplay(self.frame.loc[mask].reset_index(drop=True), self.program, self.seconds,
                              self.target, self.specification, self.excluded, self.tick, self.point_value, self.rules)

    def score(self, parameters, checkpoint=None):
        if self.in_memory and self.prepared_series is None:
            self.prepared_series = Engine.prepare_series(self.program, self.frame, self.rules)
            self.history_buffer = np.empty((len(self.frame), len(self.program.defaults)), dtype=float)
        engine_type = Engine
        if (self.rules or {}).get("motor_ticks"):
            from replay_ticks import TickEngine
            engine_type = TickEngine
        engine = engine_type(self.program, self.frame, self.tick, parameters, self.seconds, self.point_value,
                        series_data=self.prepared_series, history=self.history_buffer, days=self.day, regras=self.rules)
        engine.run(record_trace=False, checkpoint=checkpoint)
        if checkpoint:
            checkpoint()
        scores = np.zeros((len(self.frame), 5))
        for fill in engine.fills:
            row = scores[fill["barra"]-1]
            row[2] += fill["pontos_contrato"] - fill["custo_reais"] / self.point_value
            row[4] += fill["pontos_contrato"]
            action = fill["acao"]
            if action in {"long", "short"}:
                if self.specification.get("modo") == "resultado" or fill["tipo"] == "market":
                    row[0 if action == "long" else 1] = 1
            else:
                row[3] += 1
        return scores


def strategy_replay(path, source, seconds, format_name, config, tick, point_value):
    format_name = csv_format(path, format_name)
    _, frame = replay_input(path, seconds, format_name, ExecutionRules(**(config.get("regras_execucao") or {})))
    specification = search_target(config)
    if config.get("busca") != "aleatoria" and config["genetico"].get("metrica") in {"resultado", "resultado_menos_drawdown", "resultado_estavel"}:
        specification = specification | {"modo": "resultado"}
    return StrategyReplay(frame, compile_ntsl(source), seconds, config.get("classe_alvo", "1C"),
                          specification, config.get("campos_excluidos", ()), tick, point_value, config.get("regras_execucao"))


if __name__=="__main__":
    main()
