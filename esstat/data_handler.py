# pylint: disable=missing-module-docstring,missing-class-docstring
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

    async def _get(self, path: str):
        """Retrieve data from given url"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.scheme}://{self.api}:{self.port}/{path}"
            ) as ret:
                return await ret.json() if ret.status == 20 else None

    async def get_status(self):
        """Get raw cluster status."""
        raw = await self._get("_cluster/health") or {}
        return {k: v for k, v in raw.items() if k in STATE_FIELDS}

    async def get_recovery(self):
        """Get list of shards beeing recovered."""
        return await self._get("_cat/recovery?active_only=true&format=json") or []

    async def get_settings(self):
        """Get cluster settings."""
        raw_data = (
            await self._get(
                "_cluster/settings?include_defaults=true&flat_settings=true"
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
        """Get list of shards being relocated."""
        filter_out = ("STARTED",)
        records = await self._get("_cat/shards?v=true&format=json") or []
        return list(filter(lambda r: r.get("state") not in filter_out, records))
