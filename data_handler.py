from requests import get

STATE_FIELDS = (
    "active_primary_shards",
    "active_shards",
    "active_shards_percent_as_number",
    "delayed_unassigned_shards",
    "initializing_shards",
    "number_of_data_nodes",
    "number_of_in_flight_fetch",
    "number_of_nodes",
    "number_of_pending_tasks",
    "relocating_shards",
    "task_max_waiting_in_queue_millis",
    "unassigned_shards",
    "cluster_name",
    "status",
    "timed_out",
)

SETTING_FIELDS = (
    "cluster.name",
    "cluster.routing.allocation.disk.watermark.flood_stage",
    "cluster.routing.allocation.disk.watermark.high",
    "cluster.routing.allocation.disk.watermark.low",
    "cluster.routing.allocation.enable",
    "cluster.routing.allocation.type",
    "cluster.routing.rebalance.enable",
    "indices.recovery.max_bytes_per_sec",
    "cluster.routing.allocation.balance.index",
    "cluster.routing.allocation.balance.shard",
    "cluster.routing.allocation.balance.threshold",
    "cluster.routing.allocation.cluster_concurrent_rebalance",
    "cluster.routing.allocation.node_concurrent_recoveries",
)


class DataHandler:
    def __init__(self, api: str, port=9200, scheme="http"):
        self.api = api
        self.port = port
        self.scheme = scheme

    def _get(self, path: str):
        with get(f"{self.scheme}://{self.api}:{self.port}/{path}") as ret:
            return ret.json() if ret.ok else None

    def get_status(self):
        raw = self._get("_cluster/health") or {}
        return {k: v for k, v in raw.items() if k in STATE_FIELDS}

    def get_recovery(self):
        return self._get("_cat/recovery?active_only=true&format=json") or []

    def get_settings(self):
        raw_data = (
            self._get("_cluster/settings?include_defaults=true&flat_settings=true")
            or {}
        )
        raw = {
            **(raw_data.get("defaults", {})),
            **(raw_data.get("persistent", {})),
            **(raw_data.get("transient", {})),
        }
        return {k: v for k, v in raw.items() if k in SETTING_FIELDS}

    def get_relocations(self):
        filter_out = ("STARTED",)
        records = self._get("_cat/shards?v=true&format=json") or []
        return list(filter(lambda r: r.get("state") not in filter_out, records))
