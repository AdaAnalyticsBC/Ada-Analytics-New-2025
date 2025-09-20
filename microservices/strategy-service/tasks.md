# Strategy Service - Future Tasks

## Overview
This document outlines the planned refactoring and enhancement tasks for the strategy service and related microservices.

## Current Status
✅ **Completed:**
- Nancy Pelosi CHIPS strategy implemented with backtrader
- Strategy service with REST API endpoints
- YAML-based configuration for strategies
- YFinance integration for consistent historical data
- Live websocket data client implementation
- Strategy execution via main.py endpoints

## Planned Tasks

### 1. Data Service Enhancements

#### 1.1 Live Data Refactoring
**Priority: High**
- **Objective**: Use Polygon.io for live data only, refactor data service accordingly
- **Details**:
  - Evaluate if yfinance data delay is significant enough to warrant Polygon live data
  - If yes, implement Polygon WebSocket for real-time market data
  - Update data-service to serve live data from Polygon and historical data from yfinance
  - Modify websocket endpoints to use Polygon feed
- **Files to modify**:
  - `data-service/main.py`
  - `data-service/helpers.py`
  - `strategy-service/strategies/nancy-p-chips/live_data.py`

#### 1.2 Enhanced Timeframe Support
**Priority: Medium**
- **Objective**: Edit data service to return backtested chart data with comprehensive timeframes
- **Details**:
  - Support all timeframes: 1D, 1W, 1M, 3M, 6M, YTD, 1Y, 3Y, 5Y, 7Y
  - Ensure data consistency across all timeframes
  - Add data validation and error handling
  - Implement caching for frequently requested timeframes
- **Files to modify**:
  - `data-service/main.py`
  - `data-service/helpers.py`
  - Add new endpoints for chart data specific to backtesting

### 2. Backtesting Service Separation

#### 2.1 Create Dedicated Backtesting Service
**Priority: High**
- **Objective**: Separate backtesting functions into reusable service
- **Details**:
  - Create new microservice: `/microservices/backtesting-service/`
  - Move backtrader logic from strategy-service to backtesting-service
  - Create standardized backtesting API
  - Implement performance metrics calculation
  - Add benchmark comparison functionality
- **Structure**:
  ```
  backtesting-service/
  ├── main.py (FastAPI service)
  ├── requirements.txt
  ├── dockerfile
  ├── backtesting/
  │   ├── __init__.py
  │   ├── engine.py (backtrader execution)
  │   ├── metrics.py (performance calculations)
  │   └── benchmarks.py (benchmark comparisons)
  └── tests/
      └── test_backtesting.py
  ```

#### 2.2 API Endpoints for Backtesting Service
**Priority: High**
- **Endpoints to implement**:
  - `POST /backtest` - Run backtest with strategy configuration
  - `GET /backtest/{backtest_id}` - Get backtest results
  - `GET /backtest/{backtest_id}/metrics` - Get performance metrics
  - `GET /backtest/{backtest_id}/trades` - Get trade history
  - `POST /backtest/compare` - Compare multiple strategies
- **Integration**:
  - Strategy service calls backtesting service
  - Standardized request/response format
  - Async job processing for long-running backtests

### 3. Strategy Service Improvements

#### 3.1 Strategy Management
**Priority: Medium**
- **Objective**: Enhance strategy discovery and management
- **Details**:
  - Auto-discovery of strategy configurations
  - Strategy validation before execution
  - Strategy versioning and history
  - Template system for new strategies

#### 3.2 Live Trading Integration
**Priority: Low**
- **Objective**: Prepare for live trading capabilities
- **Details**:
  - Paper trading mode
  - Risk management integration
  - Position tracking
  - Real-time P&L calculation

### 4. Infrastructure Improvements

#### 4.1 Service Communication
**Priority: Medium**
- **Objective**: Improve inter-service communication
- **Details**:
  - Service discovery mechanism
  - Health checks for all services
  - Circuit breaker pattern for resilience
  - Centralized logging

#### 4.2 Configuration Management
**Priority: Low**
- **Objective**: Centralize configuration across services
- **Details**:
  - Environment-specific configurations
  - Secrets management
  - Dynamic configuration updates

## Implementation Priority

1. **Phase 1** (High Priority):
   - Create backtesting-service
   - Refactor strategy-service to use backtesting-service
   - Implement live data with Polygon (if needed)

2. **Phase 2** (Medium Priority):
   - Enhanced timeframe support in data-service
   - Strategy management improvements
   - Service communication enhancements

3. **Phase 3** (Low Priority):
   - Live trading preparation
   - Configuration management
   - Advanced monitoring and alerting

## Notes

- All new services should follow the same Docker containerization pattern
- Maintain backward compatibility during refactoring
- Add comprehensive testing for each new component
- Document API changes and new endpoints
- Consider performance implications of service separation