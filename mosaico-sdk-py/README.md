# Mosaico SDK

The **Mosaico SDK** is the primary interface for interacting with the **Mosaico Data Platform**, a high-performance system designed for the ingestion, storage and retrieval of multi-modal sensor data (Robotics, IoT).

For full documentation, see the [Mosaico SDK Documentation](https://docs.mosaico.dev/SDK).
## Catalog TUI

Browse catalog data (sequences, topics, metadata) from a running Mosaico server:

```bash
mosaico_catalog --host <HOST> --port 6726
```

Connection defaults can also be provided through environment variables:

```bash
export MOSAICO_HOST=<HOST>
export MOSAICO_PORT=6726
mosaico_catalog
```
