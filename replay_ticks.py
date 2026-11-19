"""Replay NTSL orientado aos negócios observados, com liquidez por evento."""
from dataclasses import replace

import numpy as np
import pandas as pd

from estrategia import Engine


def load_events(path, format_name, rules):
    if format_name not in {"negocios", "integrado"}:
        raise ValueError("O replay tick a tick exige um CSV de negócios ou de eventos integrados.")
    frame = pd.read_csv(path, sep=";", decimal=",")
    if format_name == "integrado":
        if frame.ativo_origem.isna().any() or frame.ativo_origem.nunique() != 1:
            raise ValueError("Use um único ativo no replay tick a tick.")
        frame = frame.rename(columns={
            "timestamp_evento":"timestamp", "sequencia_fonte":"sequencia",
            "preco_ultimo":"preco", "quantidade_negocio":"quantidade",
            **{name: "v_"+name for name in ("bid","ask","qtd_bid","qtd_ask","qtd_compra_book","qtd_venda_book",
                                            "agressao_compra","agressao_venda")},
        })
    if frame.empty or "quantidade" not in frame:
        raise ValueError("O CSV tick a tick precisa de negócios com timestamp, preço e quantidade.")
    raw = frame.timestamp.astype("string")
    local = ~raw.str.contains(r"(?:Z|[+-]\d{2}:?\d{2})$", na=False)
    zoned = pd.to_datetime(raw.where(~local), format="ISO8601", utc=True)
    local_time = pd.to_datetime(raw.where(local), format="ISO8601").dt.tz_localize("America/Sao_Paulo",
                                                                                  ambiguous="raise", nonexistent="raise")
    frame["timestamp"] = zoned.fillna(local_time.dt.tz_convert("UTC")).dt.tz_convert("America/Sao_Paulo")
    if frame.timestamp.isna().any():
        raise ValueError("Negócio sem timestamp válido.")
    if "sequencia" not in frame:
        if frame.timestamp.duplicated().any():
            raise ValueError("Negócios com timestamp empatado precisam da coluna sequencia.")
        frame["sequencia"] = np.arange(len(frame))
    sequence = pd.to_numeric(frame.sequencia)
    if (not np.isfinite(sequence).all() or (sequence<0).any() or (sequence%1!=0).any() or (sequence>=2**63).any()):
        raise ValueError("sequencia deve conter inteiros não negativos de até 63 bits.")
    frame["sequencia"] = sequence.astype("int64")
    frame = frame.drop_duplicates()
    keys = ["timestamp","sequencia"]
    if frame.duplicated(keys).any():
        raise ValueError("Negócios conflitantes no mesmo timestamp e sequência.")
    frame = frame.sort_values(keys, kind="stable").reset_index(drop=True)
    prices, sizes = (pd.to_numeric(frame[key]) for key in ("preco","quantidade"))
    if (not np.isfinite(prices).all() or (prices<=0).any() or not np.isfinite(sizes).all()
            or (sizes<=0).any() or (sizes%1!=0).any() or (sizes>=2**63).any()):
        raise ValueError("Informe preço positivo e quantidade inteira positiva por negócio.")
    for key in ("abertura","maxima","minima","fechamento","v_vwap_barra"):
        frame[key] = prices
    frame["volume_contratos"] = sizes.astype("int64")
    frame["v_trades_atual"] = 1
    stamp = frame.timestamp.dt
    day = stamp.strftime("%Y-%m-%d")
    if "pregao" in frame and not frame.pregao.astype(str).eq(day).all():
        raise ValueError("Data do evento divergente do pregão informado.")
    frame["pregao"] = day
    delta = frame.timestamp.diff().dt.total_seconds().fillna(0)
    new_day = day.ne(day.shift())
    boundary = new_day | (delta.gt(rules.lacuna_ticks_ms/1000) if rules.lacuna_ticks_ms else False)
    if "segmento" in frame:
        if frame.segmento.isna().any():
            raise ValueError("Evento integrado sem segmento.")
        boundary |= frame.segmento.ne(frame.segmento.shift())
    frame["segmento"] = boundary.cumsum()
    frame["lacuna_intradiaria"] = boundary & ~new_day
    frame["intervalo_barra_segundos"] = delta
    frame["barras_no_segmento"] = frame.groupby("segmento",sort=False).cumcount()+1
    frame["barra_ntsl"] = np.arange(1,len(frame)+1)
    frame["data_ntsl"] = (stamp.year-1900)*10000 + stamp.month*100 + stamp.day
    frame["hora_ntsl"] = stamp.hour*100 + stamp.minute
    frame["segundos_do_dia_barra"] = stamp.hour*3600 + stamp.minute*60 + stamp.second
    return frame


class TickEngine(Engine):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event_time = self.frame.timestamp.array.as_unit("ns").asi8
        self.event_sizes = self.frame.volume_contratos.to_numpy(dtype="int64")
        self.event_sequences = self.frame.sequencia.to_numpy(dtype="int64")

    def execute(self, order, price):
        start = len(self.fills)
        super().execute(order, price)
        if not order.action.startswith("net_"):
            for fill in self.fills[start:]:
                fill.update(timestamp=self.frame.timestamp.iloc[self.row].isoformat(),
                            sequencia_evento=int(self.event_sequences[self.row]),
                            fechamento_sintetico=order.function=="fim_pregao")

    def process_orders(self):
        price = self.series("close")
        available = int(self.event_sizes[self.row])
        now = int(self.event_time[self.row])
        # Saídas de cobertura precedem novas entradas. Empates usam ordem de envio.
        entries = sorted(self.orders.items(), key=lambda item: not item[1].action.startswith("exit"))
        for key, order in entries:
            if not available:
                break
            if (self.orders.get(key) is not order or self.row < order.eligible_at
                    or now < order.eligible_ns):
                continue
            fill = self.match(order, price, price, price)
            if fill is None:
                continue
            quantity = min(available, order.quantity)
            first = len(self.fills)
            self.execute(replace(order, quantity=quantity), fill)
            traded = sum(item["quantidade"] for item in self.fills[first:])
            available -= traded
            self.orders.pop(key, None)
            if traded == quantity and order.quantity > traded:
                if not order.action.startswith("exit") or self.position:
                    order.quantity -= traded
                    self.orders[key] = order
