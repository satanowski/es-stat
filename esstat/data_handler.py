# pylint: disable=missing-module-docstring,missing-class-docstring
from typing import Any

import aiohttp

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
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None

    def _ensure_session(self) -> aiohttp.ClientSession:
        if not self._session:
            raise RuntimeError("DataHandler requires 'async with' usage for network calls.")
        return self._session

    async def _get(self, path: str, *, default: Any):
        """Retrieve data from given url."""
        session = self._ensure_session()
        url = f"{self.scheme}://{self.api}:{self.port}/{path}"
        try:
            async with session.get(url) as ret:
                if ret.status == 200:
                    return await ret.json()
        except aiohttp.ClientError:
            return default
        return default

    async def get_status(self):
        """Get raw cluster status."""
        raw = await self._get("_cluster/health", default={}) or {}
        return {k: v for k, v in raw.items() if k in STATE_FIELDS}

    async def get_recovery(self):
        """Get list of shards being recovered."""
        return await self._get(
            "_cat/recovery?active_only=true&format=json", default=[]
        ) or []

    async def get_settings(self):
        """Get cluster settings."""
        raw_data = (
            await self._get(
                "_cluster/settings?include_defaults=true&flat_settings=true",
                default={},
            )
            or {}
        )
        raw = {
            **(raw_data.get("defaults", {})),
            **(raw_data.get("persistent", {})),
            **(raw_data.get("transient", {})),
        }
        return {k: v for k, v in raw.items() if k in SETTING_FIELDS}

    async def get_relocations(self):
        """Get list of shards being relocated.
        
        Splits the 'node' field into 'source' and 'target' for relocation arrows.
        """
        filter_out = ("STARTED",)
        records = await self._get(
            "_cat/shards?v=true&format=json", default=[]
        ) or []
        
        # Split node field into source and target
        for record in records:
            if "node" in record and "->" in record["node"]:
                parts = record["node"].split("->", 1)
                record["source"] = parts[0].strip()
                record["target"] = parts[1].strip() if len(parts) > 1 else ""
            else:
                # No relocation arrow, node is the source
                record["source"] = record.get("node", "")
                record["target"] = ""
        
        return list(filter(lambda r: r.get("state") not in filter_out, records))
