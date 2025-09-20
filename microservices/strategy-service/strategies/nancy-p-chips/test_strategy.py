import os
import sys
import backtrader as bt
import yfinance as yf
import pandas as pd
import requests
import yaml
from datetime import datetime, timedelta
import importlib.util
import sys

# Load the strategy module with hyphens in the name
spec = importlib.util.spec_from_file_location("nancy_p_chips_strategy", "nancy-p-chips-strategy.py")
nancy_strategy = importlib.util.module_from_spec(spec)
sys.modules["nancy_p_chips_strategy"] = nancy_strategy
spec.loader.exec_module(nancy_strategy)

NancyPelosiChipsStrategy = nancy_strategy.NancyPelosiChipsStrategy

def load_config():
    """Load strategy configuration"""
    try:
        with open('config.yaml', 'r') as f:
            return yaml.safe_load(f)
    except:
        return {
            'strategy': {'benchmark': 'SPY'},
            'data_source': {'api_url': 'http://localhost:8000'},
            'performance': {'risk_free_rate': 0.02}
        }

def fetch_data_from_api(ticker, timeframe=None):
    """Fetch historical data from our data-service API"""
    config = load_config()
    api_url = config.get('data_source', {}).get('api_url', 'http://localhost:8000')

    # Use timeframe from config if not provided
    if timeframe is None:
        timeframe = config.get('data_source', {}).get('lookback', '5Y')

    api_timeframe = timeframe

    try:
        # Only use start date since API ends at current time
        url = f"{api_url}/historical-data/{ticker}?timeframe={api_timeframe}"
        print(f"🌐 Fetching {ticker} from API: {url}")

        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            print(f"📦 API Response keys: {list(data.keys())}")

            if 'data' in data and len(data['data']) > 0:
                # Convert API data to pandas DataFrame
                # Based on helpers.py, the data structure is:
                # {"open": a.open, "high": a.high, "low": a.low, "close": a.close, "volume": a.volume, "timestamp": a.timestamp}
                df_data = []
                for point in data['data']:
                    df_data.append({
                        'Date': pd.to_datetime(point['timestamp'], unit='ms'),
                        'Open': point['open'],
                        'High': point['high'],
                        'Low': point['low'],
                        'Close': point['close'],
                        'Volume': point['volume']
                    })

                df = pd.DataFrame(df_data)
                df.set_index('Date', inplace=True)
                print(f"✅ API data: {len(df)} candles from {df.index[0].date()} to {df.index[-1].date()}")
                return df
            else:
                print(f"⚠️  API returned no data for {ticker}")

        else:
            print(f"⚠️  API returned status {response.status_code} for {ticker}")

    except requests.exceptions.ConnectionError:
        print(f"⚠️  Could not connect to data-service API for {ticker}")
    except requests.exceptions.Timeout:
        print(f"⚠️  API request timed out for {ticker}")
    except Exception as e:
        print(f"⚠️  API error for {ticker}: {e}")

    return None

def run_backtest():
    """Run backtrader backtest with real data"""
    print("=" * 80)
    print("NANCY PELOSI CHIPS STRATEGY - BACKTRADER TEST")
    print("=" * 80)

    # Initialize cerebro
    cerebro = bt.Cerebro()

    # Add our strategy
    cerebro.addstrategy(NancyPelosiChipsStrategy, initial_cash=10000, printlog=True)

    # Download data for testing
    print("📊 Downloading market data...")

    # Load config to get lookback period
    config = load_config()
    lookback = config.get('data_source', {}).get('lookback', '5Y')

    # Set date range for backtest - end at current date, start based on lookback
    end_date = datetime.now()

    # Calculate start date based on lookback period
    if lookback == "1D":
        start_date = end_date - timedelta(days=7)  # 1 week for 1D to have enough data
    elif lookback == "1W":
        start_date = end_date - timedelta(weeks=4)  # 1 month for 1W
    elif lookback == "1M":
        start_date = end_date - timedelta(days=90)  # 3 months for 1M
    elif lookback == "3M":
        start_date = end_date - timedelta(days=180)  # 6 months for 3M
    elif lookback == "6M":
        start_date = end_date - timedelta(days=365)  # 1 year for 6M
    elif lookback == "1Y":
        start_date = end_date - timedelta(days=730)  # 2 years for 1Y
    elif lookback == "3Y":
        start_date = end_date - timedelta(days=1460)  # 4 years for 3Y
    elif lookback == "5Y":
        start_date = end_date - timedelta(days=1825)  # 5 years for 5Y
    elif lookback == "7Y":
        start_date = end_date - timedelta(days=2555)  # 7 years for 7Y
    else:
        # Default to 5 years if unknown lookback
        start_date = end_date - timedelta(days=1825)

    print(f"📅 Backtest period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} (lookback: {lookback})")

    # Define benchmarks
    benchmarks = ['SPY', 'QQQ', 'XLE', 'DBC']
    benchmark_data = {}

    try:
        # Use yfinance for consistency with indicators and historical data
        print("📊 Downloading SOXX data from yfinance for consistent backtesting...")
        soxx_data = yf.download('SOXX', start=start_date, end=end_date)
        if soxx_data.empty:
            print("ERROR: Failed to download SOXX data")
            return

        # Fix column names (yfinance returns multiindex columns)
        if isinstance(soxx_data.columns, pd.MultiIndex):
            soxx_data.columns = soxx_data.columns.droplevel(1)

        # Debug: Check data quality
        print(f"📊 SOXX data shape: {soxx_data.shape}")
        print(f"📊 SOXX date range: {soxx_data.index[0]} to {soxx_data.index[-1]}")
        print(f"📊 SOXX columns: {list(soxx_data.columns)}")

        # Create backtrader data feed
        soxx_feed = bt.feeds.PandasData(
            dataname=soxx_data,
            name='SOXX'
        )
        cerebro.adddata(soxx_feed)

        # Try to add NVDA data
        try:
            nvda_data = yf.download('NVDA', start=start_date, end=end_date)
            if not nvda_data.empty:
                # Fix column names
                if isinstance(nvda_data.columns, pd.MultiIndex):
                    nvda_data.columns = nvda_data.columns.droplevel(1)

                nvda_feed = bt.feeds.PandasData(
                    dataname=nvda_data,
                    name='NVDA'
                )
                cerebro.adddata(nvda_feed)
                print("✓ Added NVDA data feed")
        except:
            print("⚠️  Could not add NVDA data feed")

        # Try to add AMD data
        try:
            amd_data = yf.download('AMD', start=start_date, end=end_date)
            if not amd_data.empty:
                # Fix column names
                if isinstance(amd_data.columns, pd.MultiIndex):
                    amd_data.columns = amd_data.columns.droplevel(1)

                amd_feed = bt.feeds.PandasData(
                    dataname=amd_data,
                    name='AMD'
                )
                cerebro.adddata(amd_feed)
                print("✓ Added AMD data feed")
        except:
            print("⚠️  Could not add AMD data feed")

        # Download benchmark data for analysis
        print("📊 Downloading benchmark data...")
        config = load_config()
        primary_benchmark = config.get('strategy', {}).get('benchmark', 'SPY')

        for benchmark in benchmarks:
            try:
                # Use yfinance for consistent historical data
                bench_data = yf.download(benchmark, start=start_date, end=end_date)
                if not bench_data.empty:
                    # Fix column names
                    if isinstance(bench_data.columns, pd.MultiIndex):
                        bench_data.columns = bench_data.columns.droplevel(1)

                    benchmark_data[benchmark] = bench_data
                    symbol = "🎯" if benchmark == primary_benchmark else "✓"
                    print(f"{symbol} Downloaded {benchmark} benchmark data")
            except Exception as e:
                print(f"⚠️  Could not download {benchmark}: {e}")

        print("✓ Market data loaded successfully")

    except Exception as e:
        print(f"ERROR downloading data: {e}")
        return

    # Set initial cash
    cerebro.broker.setcash(10000.0)

    # Add commission (0.1% per trade)
    cerebro.broker.setcommission(commission=0.001)

    print(f"\n💰 Starting Portfolio Value: ${cerebro.broker.getvalue():.2f}")

    # Run the backtest
    print("\n🚀 Running backtest...")
    try:
        results = cerebro.run()
        strategy = results[0]

        print(f"💰 Final Portfolio Value: ${cerebro.broker.getvalue():.2f}")

        # Generate additional analysis
        generate_detailed_analysis(strategy, benchmark_data, soxx_data)

    except Exception as e:
        print(f"ERROR during backtest: {e}")
        return

    # Plot results (optional)
    try:
        print("\n📈 Generating plots...")
        cerebro.plot(style='candlestick')
    except Exception as e:
        print(f"Could not generate plots: {e}")

def calculate_benchmark_metrics(strategy_returns, benchmark_returns):
    """Calculate Alpha, Beta, R^2, and R for a strategy vs benchmark"""
    import numpy as np
    from scipy import stats

    # Align the data
    min_len = min(len(strategy_returns), len(benchmark_returns))
    strat_ret = strategy_returns[-min_len:]
    bench_ret = benchmark_returns[-min_len:]

    if len(strat_ret) < 2:
        return {'alpha': 0, 'beta': 0, 'r_squared': 0, 'correlation': 0}

    # Linear regression: strategy_returns = alpha + beta * benchmark_returns
    slope, intercept, r_value, p_value, std_err = stats.linregress(bench_ret, strat_ret)

    beta = slope
    alpha = intercept * 252  # Annualized alpha
    r_squared = r_value ** 2
    correlation = r_value

    return {
        'alpha': alpha,
        'beta': beta,
        'r_squared': r_squared,
        'correlation': correlation
    }

def calculate_trailing_returns(returns_series, periods):
    """Calculate trailing returns for specified periods (in trading days)"""
    if len(returns_series) < periods:
        return 0

    trailing_values = returns_series[-periods:]
    return (trailing_values.iloc[-1] / trailing_values.iloc[0]) - 1

def generate_detailed_analysis(strategy, benchmark_data, soxx_data):
    """Generate detailed analysis matching the required output format"""
    print("\n" + "=" * 80)
    print("DETAILED PERFORMANCE ANALYSIS")
    print("=" * 80)

    if not strategy.daily_values:
        print("No performance data available")
        return

    # Convert to DataFrame for analysis
    df = pd.DataFrame(strategy.daily_values)

    if df.empty:
        print("No daily values recorded")
        return

    # Load config for risk-free rate
    config = load_config()
    risk_free_rate = config.get('performance', {}).get('risk_free_rate', 0.02)

    # Calculate benchmark comparison
    initial_value = strategy.params.initial_cash
    final_value = df['value'].iloc[-1]

    # Calculate returns series
    df['returns'] = df['value'].pct_change().fillna(0)

    if len(df) < 2:
        print("Insufficient data for analysis")
        return

    # Performance metrics
    print("\n1. SIMULATED RETURNS")
    print("-" * 40)
    print(f"Initial Investment:    ${initial_value:,.2f}")
    print(f"Final Value:          ${final_value:,.2f}")
    print(f"Total Return:         {((final_value/initial_value) - 1):.2%}")
    print(f"Regulatory Fees:      ${initial_value * 0.001:,.2f}")
    print(f"Total Slippage:       ${initial_value * 0.002:,.2f}")

    # Strategy performance calculations - Composer methodology
    total_return = (final_value / initial_value) - 1
    days_trading = len(df)
    years_trading = days_trading / 252.0  # Trading days per year

    # Composer-style Annualized Return: CAGR (Compound Annual Growth Rate)
    if years_trading > 0:
        annualized_return = (final_value / initial_value) ** (1 / years_trading) - 1
    else:
        annualized_return = 0

    # Risk metrics - Composer methodology
    if len(df['returns']) > 1:
        # Remove zero returns for better volatility calculation
        non_zero_returns = df['returns'][df['returns'] != 0]

        # Daily volatility (standard deviation of daily returns)
        daily_volatility = df['returns'].std()

        # Annualized volatility - Composer uses sqrt(252) scaling
        annualized_volatility = daily_volatility * (252 ** 0.5)

        # Sharpe Ratio - Composer methodology: (Portfolio Return - Risk Free Rate) / Portfolio Volatility
        # Convert risk-free rate to daily and then annualize properly
        daily_risk_free = risk_free_rate / 252

        # Calculate using daily returns for more accuracy
        daily_excess_returns = df['returns'] - daily_risk_free
        sharpe_ratio = daily_excess_returns.mean() / daily_excess_returns.std() * (252 ** 0.5) if daily_excess_returns.std() > 0 else 0

        excess_return = annualized_return - risk_free_rate
    else:
        annualized_volatility = 0
        sharpe_ratio = 0
        excess_return = annualized_return

    # Maximum Drawdown - Composer methodology
    df['cumulative_return'] = (1 + df['returns']).cumprod()
    df['running_max'] = df['cumulative_return'].expanding().max()
    df['drawdown'] = (df['cumulative_return'] - df['running_max']) / df['running_max']
    max_drawdown = abs(df['drawdown'].min())

    # Calmar Ratio - Composer methodology: Annualized Return / Maximum Drawdown
    if max_drawdown > 0:
        calmar_ratio = annualized_return / max_drawdown
    else:
        calmar_ratio = float('inf') if annualized_return > 0 else 0

    # Trailing returns (1M = ~22 trading days, 3M = ~66 trading days)
    trailing_1m = calculate_trailing_returns(df['value'], 22)
    trailing_3m = calculate_trailing_returns(df['value'], 66)

    # Debug output for validation - Composer-style metrics
    print(f"\n🔍 COMPOSER-STYLE METRIC VALIDATION:")
    print(f"   Total Return: {total_return:.4f} ({total_return:.2%})")
    print(f"   Days Trading: {days_trading} ({years_trading:.2f} years)")
    print(f"   CAGR (Annualized Return): {annualized_return:.4f} ({annualized_return:.2%})")
    print(f"   Daily Volatility: {daily_volatility:.4f} ({daily_volatility:.2%})")
    print(f"   Annualized Volatility: {annualized_volatility:.4f} ({annualized_volatility:.2%})")
    print(f"   Risk-Free Rate: {risk_free_rate:.4f} ({risk_free_rate:.2%})")
    print(f"   Excess Return: {excess_return:.4f} ({excess_return:.2%})")
    print(f"   Max Drawdown: {max_drawdown:.4f} ({max_drawdown:.2%})")
    print(f"   Sharpe Ratio: {sharpe_ratio:.4f}")
    print(f"   Calmar Ratio: {calmar_ratio:.4f}")

    # Additional Composer-style metrics
    win_rate = len(df[df['returns'] > 0]) / len(df[df['returns'] != 0]) if len(df[df['returns'] != 0]) > 0 else 0
    avg_win = df[df['returns'] > 0]['returns'].mean() if len(df[df['returns'] > 0]) > 0 else 0
    avg_loss = df[df['returns'] < 0]['returns'].mean() if len(df[df['returns'] < 0]) > 0 else 0

    print(f"   Win Rate: {win_rate:.4f} ({win_rate:.2%})")
    print(f"   Average Win: {avg_win:.4f} ({avg_win:.2%})")
    print(f"   Average Loss: {avg_loss:.4f} ({avg_loss:.2%})")

    # Calculate benchmark metrics
    print("\n2. BENCHMARKS (per Ticker)")
    print("-" * 60)
    print(f"{'Ticker':<12} {'Alpha':<10} {'Beta':<10} {'R^2':<10} {'R':<10}")
    print("-" * 60)

    benchmark_metrics = {}
    for ticker, bench_data in benchmark_data.items():
        # Calculate benchmark returns aligned with strategy dates
        bench_returns = bench_data['Close'].pct_change().fillna(0)

        # Align dates with strategy data
        strategy_dates = pd.to_datetime(df['date'])
        bench_aligned = bench_returns.reindex(strategy_dates, method='ffill').fillna(0)

        metrics = calculate_benchmark_metrics(df['returns'], bench_aligned)
        benchmark_metrics[ticker] = metrics

        print(f"{ticker:<12} {metrics['alpha']:<10.4f} {metrics['beta']:<10.4f} {metrics['r_squared']:<10.4f} {metrics['correlation']:<10.4f}")

    # Calculate benchmark performance for comparison
    print("\n3. PERFORMANCE METRICS (against benchmarks)")
    print("-" * 80)
    print(f"{'Metric':<20} {'NANCY':<12} ", end="")

    # Add benchmark headers
    for ticker in benchmark_data.keys():
        print(f"{ticker:<12} ", end="")
    print()
    print("-" * 80)

    # Performance comparison table
    metrics_data = {
        'Cumulative Return': total_return,
        'Annualized Return': annualized_return,
        'Trailing 1M Return': trailing_1m,
        'Trailing 3M Return': trailing_3m,
        'Sharpe Ratio': sharpe_ratio,
        'Standard Deviation': annualized_volatility,
        'Max Drawdown': -max_drawdown,  # Display as negative
        'Calmar Ratio': calmar_ratio
    }

    for metric_name, nancy_value in metrics_data.items():
        print(f"{metric_name:<20} ", end="")

        # Format Nancy's value
        if metric_name in ['Cumulative Return', 'Annualized Return', 'Trailing 1M Return',
                          'Trailing 3M Return', 'Standard Deviation', 'Max Drawdown']:
            print(f"{nancy_value:<12.2%} ", end="")
        else:
            print(f"{nancy_value:<12.2f} ", end="")

        # Calculate and display benchmark values
        for ticker, bench_data in benchmark_data.items():
            if metric_name == 'Cumulative Return':
                bench_total_return = (bench_data['Close'].iloc[-1] / bench_data['Close'].iloc[0]) - 1
                print(f"{bench_total_return:<12.2%} ", end="")
            elif metric_name == 'Annualized Return':
                bench_total_return = (bench_data['Close'].iloc[-1] / bench_data['Close'].iloc[0]) - 1
                bench_ann_return = (1 + bench_total_return) ** (252 / len(bench_data)) - 1
                print(f"{bench_ann_return:<12.2%} ", end="")
            elif metric_name == 'Standard Deviation':
                bench_returns = bench_data['Close'].pct_change().fillna(0)
                bench_vol = bench_returns.std() * (252 ** 0.5)
                print(f"{bench_vol:<12.2%} ", end="")
            else:
                print(f"{'N/A':<12} ", end="")
        print()

    # Trading activity summary
    print(f"\n4. TRADING ACTIVITY")
    print("-" * 50)
    print(f"Total Trading Days:   {len(df)}")

    if strategy.trade_log:
        trades_df = pd.DataFrame(strategy.trade_log)
        print(f"Total Trades:         {len(trades_df)}")
        print(f"Buy Orders:           {len(trades_df[trades_df['action'] == 'BUY'])}")
        print(f"Sell Orders:          {len(trades_df[trades_df['action'] == 'SELL'])}")

        # Show trading allocation table
        print(f"\nRecent Trading Days:")
        print(f"{'Date':<12} {'SOXX':<8} {'Cash':<8} {'Position':<10}")
        print("-" * 45)

        # Show last 10 days
        for _, row in df.tail(10).iterrows():
            position_pct = (row['value'] - row['cash']) / row['value'] * 100 if row['value'] > 0 else 0
            cash_pct = row['cash'] / row['value'] * 100 if row['value'] > 0 else 100

            action = "LONG" if row['position'] > 0 else "CASH"
            print(f"{row['date']!s:<12} {position_pct:<7.1f}% {cash_pct:<7.1f}% {action:<10}")

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run_backtest()