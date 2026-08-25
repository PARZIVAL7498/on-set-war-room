# Compatibility shim — prefer clickhouse_client for new code.
from app.integrations.clickhouse_client import (  # noqa: F401
    ClickHouseConfigError,
    close_client,
    command,
    get_client,
    get_config,
    insert,
    ping,
    query,
)
