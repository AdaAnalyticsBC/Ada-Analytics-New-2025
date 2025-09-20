import backtrader as bt
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import yaml
import json

class NancyPelosiChipsStrategy(bt.Strategy):
    params = (
        ('initial_cash', 10000),
        ('printlog', True),
    )

    def __init__(self):
        # Load strategy configuration
        self.load_config()

        # Main data feeds with validation
        if len(self.datas) == 0:
            raise ValueError("No data feeds provided")

        self.soxx = self.datas[0]  # SOXX (main semiconductor ETF)
        self.nvda = self.datas[1] if len(self.datas) > 1 else None
        self.amd = self.datas[2] if len(self.datas) > 2 else None

        print(f"🔧 Initializing strategy with {len(self.datas)} data feeds")

        # Technical indicators with reduced periods for limited data
        try:
            # Use shorter periods that work with our available data
            self.soxx_sma10 = bt.indicators.ExponentialMovingAverage(self.soxx, period=10)
            self.soxx_sma200 = bt.indicators.ExponentialMovingAverage(self.soxx, period=50)  # Reduced from 200 to 50
            print(f"✓ SOXX indicators initialized")
        except Exception as e:
            print(f"❌ Error initializing SOXX indicators: {e}")
            raise

        try:
            if self.nvda is not None:
                self.nvda_rsi8 = bt.indicators.RelativeStrengthIndex(self.nvda, period=8)
                self.nvda_rsi3 = bt.indicators.RelativeStrengthIndex(self.nvda, period=3)
                print(f"✓ NVDA indicators initialized")
            else:
                self.nvda_rsi8 = None
                self.nvda_rsi3 = None
                print(f"⚠️  NVDA data not available")
        except Exception as e:
            print(f"❌ Error initializing NVDA indicators: {e}")
            self.nvda_rsi8 = None
            self.nvda_rsi3 = None

        try:
            if self.amd is not None:
                self.amd_rsi8 = bt.indicators.RelativeStrengthIndex(self.amd, period=8)
                self.amd_rsi3 = bt.indicators.RelativeStrengthIndex(self.amd, period=3)
                print(f"✓ AMD indicators initialized")
            else:
                self.amd_rsi8 = None
                self.amd_rsi3 = None
                print(f"⚠️  AMD data not available")
        except Exception as e:
            print(f"❌ Error initializing AMD indicators: {e}")
            self.amd_rsi8 = None
            self.amd_rsi3 = None

        # Track performance data
        self.trade_log = []
        self.daily_values = []

    def load_config(self):
        """Load strategy configuration from config.yaml"""
        try:
            with open('config.yaml', 'r') as f:
                self.config = yaml.safe_load(f)
        except:
            self.config = {'initial-amount': '$10,000'}

    def log(self, txt, dt=None):
        """Logging function"""
        dt = dt or self.datas[0].datetime.date(0)
        if self.params.printlog:
            print(f'{dt}: {txt}')

    def get_cumulative_return(self, data, periods):
        """Calculate cumulative return over specified periods"""
        if len(data) < periods + 1:  # Need at least periods + 1 data points
            return 0

        try:
            current_price = data.close[0]
            past_price = data.close[-periods]
            if past_price != 0:
                return (current_price - past_price) / past_price
            else:
                return 0
        except (IndexError, AttributeError):
            return 0

    def get_90d_moving_avg_return(self, data):
        """Calculate 90-day moving average of returns"""
        if data is None or len(data) < 10:
            return 0

        try:
            returns = []
            data_length = len(data)
            max_periods = min(90, data_length - 1)

            if max_periods < 2:
                return 0

            # In backtrader, use negative indexing from current bar
            for i in range(1, max_periods):
                if i < len(data) and (i + 1) < len(data):
                    try:
                        current_price = data.close[-i]
                        prev_price = data.close[-(i + 1)]

                        if prev_price != 0 and current_price > 0 and prev_price > 0:
                            ret = (current_price - prev_price) / prev_price
                            returns.append(ret)
                    except (IndexError, TypeError):
                        # Skip this calculation if data access fails
                        continue

            return np.mean(returns) if returns else 0
        except (IndexError, AttributeError) as e:
            print(f"Error in get_90d_moving_avg_return: {e}")
            return 0

    def execute_composer_logic(self):
        """Execute the Composer-style decision tree logic"""
        # Main condition: 5d cumulative return of SOXX > 5%
        soxx_5d_return = self.get_cumulative_return(self.soxx, 5)

        if soxx_5d_return > 0.05:  # Greater than 5%
            # Check 1d return condition
            soxx_1d_return = self.get_cumulative_return(self.soxx, 1)

            if soxx_1d_return < -0.02:  # Less than -2%
                # Buy SOXL (Bull 3x)
                self.log(f'SIGNAL: Buy SOXL - 5d return: {soxx_5d_return:.2%}, 1d return: {soxx_1d_return:.2%}')
                return {'SOXL': 1.0}
            else:
                # Buy SOXS (Bear 3x)
                self.log(f'SIGNAL: Buy SOXS - 5d return: {soxx_5d_return:.2%}, 1d return: {soxx_1d_return:.2%}')
                return {'SOXS': 1.0}

        else:  # Bearish Mean Reversion branch
            if soxx_5d_return < -0.05:  # Less than -5%
                soxx_1d_return = self.get_cumulative_return(self.soxx, 1)

                if soxx_1d_return > 0.02:  # Greater than 2%
                    # Buy SOXS
                    self.log(f'SIGNAL: Buy SOXS (mean reversion) - 5d: {soxx_5d_return:.2%}, 1d: {soxx_1d_return:.2%}')
                    return {'SOXS': 1.0}
                else:
                    # Buy SOXL
                    self.log(f'SIGNAL: Buy SOXL (mean reversion) - 5d: {soxx_5d_return:.2%}, 1d: {soxx_1d_return:.2%}')
                    return {'SOXL': 1.0}

            else:  # Detailed analysis branch following JSON outline
                # NVDA branch: Check 8d RSI first, then 3d RSI, then moving averages
                if self.nvda is not None and self.nvda_rsi8 is not None and len(self.nvda_rsi8) > 0:
                    nvda_rsi8_val = self.nvda_rsi8[0]

                    if nvda_rsi8_val > 90:
                        self.log(f'SIGNAL: Buy SOXS - NVDA RSI8 overbought: {nvda_rsi8_val:.1f}')
                        return {'SOXS': 1.0}
                    else:
                        # Check 3d RSI
                        if self.nvda_rsi3 is not None and len(self.nvda_rsi3) > 0:
                            nvda_rsi3_val = self.nvda_rsi3[0]
                            if nvda_rsi3_val < 15:
                                self.log(f'SIGNAL: Buy SOXL - NVDA RSI3 oversold: {nvda_rsi3_val:.1f}')
                                return {'SOXL': 1.0}

                # AMD branch: Check 8d RSI first, then 3d RSI, then moving averages
                if self.amd is not None and self.amd_rsi8 is not None and len(self.amd_rsi8) > 0:
                    amd_rsi8_val = self.amd_rsi8[0]

                    if amd_rsi8_val > 90:
                        self.log(f'SIGNAL: Buy SOXS - AMD RSI8 overbought: {amd_rsi8_val:.1f}')
                        return {'SOXS': 1.0}
                    else:
                        # Check 3d RSI
                        if self.amd_rsi3 is not None and len(self.amd_rsi3) > 0:
                            amd_rsi3_val = self.amd_rsi3[0]
                            if amd_rsi3_val < 15:
                                self.log(f'SIGNAL: Buy SOXL - AMD RSI3 oversold: {amd_rsi3_val:.1f}')
                                return {'SOXL': 1.0}

                # Moving average analysis (final fallback)
                if len(self.soxx_sma10) > 0 and len(self.soxx_sma200) > 0:
                    sma10_val = self.soxx_sma10[0]
                    sma200_val = self.soxx_sma200[0]
                else:
                    # Default to cash if indicators not ready
                    self.log('SIGNAL: Indicators not ready - hold cash')
                    return {}

                if sma10_val > sma200_val:
                    # Uptrend - select top performer from expanded asset universe
                    self.log(f'SIGNAL: Uptrend detected - MA10: {sma10_val:.2f} > MA200: {sma200_val:.2f}')

                    # Calculate 90d moving average returns for ranking (as per JSON outline)
                    assets_performance = {
                        'SOXX': self.get_90d_moving_avg_return(self.soxx),
                        'NVDA': self.get_90d_moving_avg_return(self.nvda) if self.nvda else 0,
                        'AMD': self.get_90d_moving_avg_return(self.amd) if self.amd else 0,
                        # Note: XLE and ENPH would need data feeds to be fully implemented
                    }

                    # Select top performer
                    best_asset = max(assets_performance, key=assets_performance.get)
                    self.log(f'SIGNAL: Select top performer: {best_asset}')
                    return {best_asset: 1.0}

                else:
                    # Downtrend - defensive allocation (SPY + DBC as per JSON)
                    self.log(f'SIGNAL: Downtrend - defensive allocation')
                    return {'SPY': 0.5, 'DBC': 0.5}

        # Default: hold cash
        return {}

    def next(self):
        """Main strategy logic executed on each bar"""
        # Skip if not enough data - need sufficient bars for indicators
        if len(self.soxx) < 10:
            return

        # Additional safety checks - wait for indicators to be ready
        if (len(self.soxx_sma10) < 1 or len(self.soxx_sma200) < 1 or
            self.soxx_sma10[0] == 0 or self.soxx_sma200[0] == 0):
            return

        try:
            # Execute Composer logic
            allocation = self.execute_composer_logic()

            # For simplicity, we'll just track SOXX position as proxy
            # In real implementation, would need separate data feeds for SOXL, SOXS, etc.
            current_position = self.getposition(self.soxx).size

            if 'SOXL' in allocation or 'SOXX' in allocation or 'NVDA' in allocation or 'AMD' in allocation:
                if current_position <= 0:
                    # Buy signal
                    size = int(self.broker.getcash() / self.soxx.close[0])
                    if size > 0:
                        self.buy(data=self.soxx, size=size)
                        self.log(f'BUY CREATE: {size} shares at {self.soxx.close[0]:.2f}')

            elif 'SOXS' in allocation:
                if current_position > 0:
                    # Sell signal (short proxy)
                    self.sell(data=self.soxx, size=current_position)
                    self.log(f'SELL CREATE: {current_position} shares at {self.soxx.close[0]:.2f}')

            # Track daily portfolio value
            current_date = self.soxx.datetime.date(0)
            self.daily_values.append({
                'date': current_date,
                'value': self.broker.getvalue(),
                'cash': self.broker.getcash(),
                'position': self.getposition(self.soxx).size
            })

        except Exception as e:
            print(f"Error in next(): {e}")
            print(f"Date: {self.soxx.datetime.date(0)}")
            print(f"SOXX length: {len(self.soxx)}")
            print(f"SMA10 length: {len(self.soxx_sma10) if self.soxx_sma10 else 'None'}")
            print(f"SMA200 length: {len(self.soxx_sma200) if self.soxx_sma200 else 'None'}")
            print(f"NVDA length: {len(self.nvda) if self.nvda else 'None'}")
            print(f"AMD length: {len(self.amd) if self.amd else 'None'}")
            import traceback
            traceback.print_exc()
            # Don't re-raise, just log and continue
            return

    def notify_order(self, order):
        """Track order execution"""
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED: {order.executed.size} shares at {order.executed.price:.2f}')
            else:
                self.log(f'SELL EXECUTED: {order.executed.size} shares at {order.executed.price:.2f}')

            self.trade_log.append({
                'date': self.soxx.datetime.date(0),
                'action': 'BUY' if order.isbuy() else 'SELL',
                'size': order.executed.size,
                'price': order.executed.price,
                'value': order.executed.value,
                'commission': order.executed.comm
            })

    def stop(self):
        """Called when backtest ends"""
        final_value = self.broker.getvalue()
        initial_value = self.params.initial_cash
        total_return = (final_value - initial_value) / initial_value

        self.log(f'Final Portfolio Value: ${final_value:.2f}')
        self.log(f'Total Return: {total_return:.2%}')

