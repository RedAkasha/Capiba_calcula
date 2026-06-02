import pandas as pd


class SimulationStorage:
    def __init__(self):
        self.fleet_db = []        # lista de veículos individuais
        self.fleets = {}          # { nome_frota: [vehicle_id, ...] }
        self._next_id = 1

    # ── Veículos ──────────────────────────────────────────────────────

    def register_vehicle(self, name: str, category: str, fuel: str) -> str:
        vid = self._next_id
        self._next_id += 1
        self.fleet_db.append({
            "id":         vid,
            "nome":       name,
            "categoria":  category,
            "combustivel": fuel,
        })
        return f"Veículo '{name}' cadastrado com sucesso (ID: {vid})!"

    def get_fleet(self) -> pd.DataFrame:
        return pd.DataFrame(self.fleet_db) if self.fleet_db else pd.DataFrame(
            columns=["id", "nome", "categoria", "combustivel"])

    def get_vehicle_names(self) -> list[str]:
        """Retorna lista de nomes para exibição no Simulador."""
        return [f"[{v['id']}] {v['nome']} – {v['categoria']} / {v['combustivel']}"
                for v in self.fleet_db]

    def get_vehicle_by_display(self, display: str):
        """Recupera dict do veículo a partir da string de exibição."""
        for v in self.fleet_db:
            prefix = f"[{v['id']}]"
            if display.startswith(prefix):
                return v
        return None

    # ── Frotas ────────────────────────────────────────────────────────

    def create_fleet(self, fleet_name: str, vehicle_ids: list[int]) -> str:
        if not fleet_name.strip():
            return "Erro: informe um nome para a frota."
        if not vehicle_ids:
            return "Erro: selecione ao menos um veículo."
        self.fleets[fleet_name] = vehicle_ids
        names = [v["nome"] for v in self.fleet_db if v["id"] in vehicle_ids]
        return (f"Frota '{fleet_name}' criada com {len(names)} veículo(s): "
                f"{', '.join(names)}.")

    def get_fleet_names(self) -> list[str]:
        return list(self.fleets.keys())

    def get_vehicles_in_fleet(self, fleet_name: str) -> list[dict]:
        ids = self.fleets.get(fleet_name, [])
        return [v for v in self.fleet_db if v["id"] in ids]


storage = SimulationStorage()
