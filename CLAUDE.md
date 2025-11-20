# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Trace-X Backend is a blockchain transaction analysis system that tracks fund flows, bridges, and cross-chain transactions. The system analyzes on-chain activity across multiple EVM-compatible chains (Ethereum, BNB, Base, Plasma, Polygon, Arbitrum) to detect transaction patterns, classify transaction types (swaps, bridges, transfers), and build transaction graphs.

## Architecture

### Core Components

1. **API Layer** ([src/api/app.py](src/api/app.py))
   - Flask-based REST API
   - Endpoints for dashboard, live detection, fund flow analysis, and bridge analysis
   - Currently stubbed out with planned integrations

2. **Analysis Engine** ([src/analysis/](src/analysis/))
   - Transaction analysis and classification
   - Fund flow tracking through transaction graphs
   - Bridge transaction detection and linking across chains

3. **Data Models** ([src/analysis/types/](src/analysis/types/))
   - `Node`: Represents addresses with metadata (labels, contract status, risk scoring)
   - `Edge`: Represents transactions between addresses
   - `BridgeTransaction`: Links transactions across source and destination chains

### Transaction Classification System

The system uses function signature matching to identify transaction types:

- **Function Signatures** ([src/analysis/configs/function_signatures.json](src/analysis/configs/function_signatures.json)):
  - Maps 4-byte function selectors to transaction types (ERC20_TRANSFER, SWAP, BRIDGE)
  - Identifies specific protocols (Uniswap V4, PancakeSwap, DeBridge, LI.FI, etc.)

- **Address Labels** ([src/analysis/configs/address_label.json](src/analysis/configs/address_label.json)):
  - Known contract addresses labeled by chain
  - Protocol-specific router and adapter contracts

### Multi-Chain Support

RPC endpoints for supported chains are defined in [src/analysis/enums/rpc_enum.py](src/analysis/enums/rpc_enum.py). Each chain has a dedicated RPC endpoint using 1rpc.io or chain-specific providers.

## Data Flow

1. Transaction data is fetched from blockchain RPCs
2. Function signatures are extracted and matched against known patterns
3. Transactions are classified as transfers, swaps, or bridges
4. For bridges, the system matches source and destination transactions across chains
5. Graph structure is built with addresses as nodes and transactions as edges
6. Risk scoring and labeling is applied based on transaction patterns

## Key Implementation Notes

### Bridge Transaction Matching

Bridge transactions appear on both source and destination chains with different transaction hashes. The system must:
- Identify bridge function calls on the source chain
- Track token amounts, addresses, and timestamps
- Match corresponding transactions on destination chains
- Link them in `BridgeTransaction` objects with both `SRC_TX_HASH` and `DST_TX_HASH`

### Transaction Graph Structure

- **Nodes** represent unique addresses across chains (format: `{chain}:{address}`)
- **Edges** represent fund transfers with token amounts, timestamps, and transaction types
- Risk scoring aggregates suspicious patterns across the graph

### Adding New Transaction Types

To support new protocols or transaction types:

1. Add function signature to [src/analysis/configs/function_signatures.json](src/analysis/configs/function_signatures.json)
2. Add known contract addresses to [src/analysis/configs/address_label.json](src/analysis/configs/address_label.json)
3. Update transaction classification logic in the analysis engine

## Development

### Running the API Server

```bash
python -m flask --app src/api/app run
```

### Project Dependencies

The project uses:
- Flask for API server
- etherscan for blockchain data access
- Standard Python dataclasses for type definitions

Note: No requirements.txt or dependency management file currently exists in the repository.

### Testing Endpoints

API endpoints:
- `GET /api/dashboard/summary` - Dashboard summary data
- `GET /api/dashboard/monitoring` - Real-time monitoring
- `GET /api/live-detection/summary` - Live detection summary
- `GET /api/analysis/fund-flow?chainId=<id>&address=<addr>` - Fund flow analysis
- `POST /api/analysis/bridge?chainId=<id>&txHash=<hash>` - Bridge analysis
