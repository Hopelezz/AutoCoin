import sys
import logging
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QCheckBox, QPushButton, QTableWidget, QTableWidgetItem, 
                             QTextEdit, QTabWidget, QFormLayout, QLineEdit, QDoubleSpinBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from config import load_settings, load_coins_settings, update_settings, update_coins_settings
from coinbase import CoinbaseClient
from trends import Trends
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from datetime import datetime

class TradingBotGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Trading Bot GUI")
        self.setGeometry(100, 100, 1000, 800)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.init_ui()
        self.load_data()
        
        # Timer to update data periodically
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_data)
        self.timer.start(60000)  # Update every minute

        # Initialize Coinbase client
        self.coinbase_client = CoinbaseClient()

    def init_ui(self):
        # Create tabs
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        # Main tab
        main_tab = QWidget()
        main_layout = QVBoxLayout(main_tab)
        self.tabs.addTab(main_tab, "Main")

        # Test mode switch
        self.add_test_mode_switch(main_layout)

        # Statistics table
        self.init_stats_table(main_layout)

        # Refresh button
        self.refresh_button = QPushButton("Refresh Data")
        self.refresh_button.clicked.connect(self.update_data)
        main_layout.addWidget(self.refresh_button)

        # Log window
        self.log_window = QTextEdit()
        self.log_window.setReadOnly(True)
        main_layout.addWidget(self.log_window)

        # Charts tab
        self.init_charts_tab()

        # Settings tab
        self.init_settings_tab()

    def add_test_mode_switch(self, layout):
        test_mode_layout = QHBoxLayout()
        test_mode_label = QLabel("Test Mode:")
        self.test_mode_switch = QCheckBox()
        test_mode_layout.addWidget(test_mode_label)
        test_mode_layout.addWidget(self.test_mode_switch)
        test_mode_layout.addStretch()
        layout.addLayout(test_mode_layout)

    def init_stats_table(self, layout):
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(8)
        self.stats_table.setHorizontalHeaderLabels(["Coin", "Balance", "Current Price", "USD Value", "Trend", "Enabled", "Buy", "Sell"])
        layout.addWidget(self.stats_table)

    def init_charts_tab(self):
        charts_tab = QWidget()
        charts_layout = QVBoxLayout(charts_tab)
        self.tabs.addTab(charts_tab, "Charts")

        self.chart_figure = plt.figure(figsize=(5, 4))
        self.chart_canvas = FigureCanvas(self.chart_figure)
        charts_layout.addWidget(self.chart_canvas)

    def init_settings_tab(self):
        settings_tab = QWidget()
        settings_layout = QFormLayout(settings_tab)
        self.tabs.addTab(settings_tab, "Settings")

        self.refresh_interval_input = QDoubleSpinBox()
        self.refresh_interval_input.setRange(1, 3600)
        self.refresh_interval_input.setValue(60)
        settings_layout.addRow("Refresh Interval (seconds):", self.refresh_interval_input)

        self.sale_threshold_input = QDoubleSpinBox()
        self.sale_threshold_input.setRange(0.1, 100)
        self.sale_threshold_input.setValue(10)
        settings_layout.addRow("Sale Threshold (%):", self.sale_threshold_input)

        self.loss_limit_input = QDoubleSpinBox()
        self.loss_limit_input.setRange(0.1, 100)
        self.loss_limit_input.setValue(5)
        settings_layout.addRow("Loss Limit (%):", self.loss_limit_input)

        self.save_settings_button = QPushButton("Save Settings")
        self.save_settings_button.clicked.connect(self.save_settings)
        settings_layout.addRow(self.save_settings_button)

        settings_tab.setLayout(settings_layout)

    def load_data(self):
        try:
            settings = load_settings()
            coins_settings = load_coins_settings()

            # Set test mode switch
            self.test_mode_switch.setChecked(settings.get('testing', False))
            self.test_mode_switch.stateChanged.connect(self.toggle_test_mode)

            # Populate statistics table
            self.update_stats_table(coins_settings)

            # Load settings
            self.refresh_interval_input.setValue(settings.get('refresh_interval', 60))
            self.sale_threshold_input.setValue(settings.get('sale_threshold', 10))
            self.loss_limit_input.setValue(settings.get('loss_limit', 5))
        except Exception as e:
            self.log(f"Error loading data: {e}")

    def update_stats_table(self, coins_settings):
        self.stats_table.setRowCount(len(coins_settings))
        for row, (coin, data) in enumerate(coins_settings.items()):
            try:
                balance = data.get('balance', 0)
                current_price = data.get('current_price')
                if current_price is not None:
                    usd_value = balance * current_price
                else:
                    usd_value = 0

                self.stats_table.setItem(row, 0, QTableWidgetItem(coin))
                self.stats_table.setItem(row, 1, QTableWidgetItem(f"{balance:.8f}"))
                self.stats_table.setItem(row, 2, QTableWidgetItem(f"${current_price:.2f}" if current_price is not None else "N/A"))
                self.stats_table.setItem(row, 3, QTableWidgetItem(f"${usd_value:.2f}"))
                self.stats_table.setItem(row, 4, QTableWidgetItem(data.get('trend_status', 'N/A')))

                enabled_checkbox = QCheckBox()
                enabled_checkbox.setChecked(data.get('enabled', False))
                enabled_checkbox.stateChanged.connect(lambda state, c=coin: self.toggle_coin_enabled(c, state))
                self.stats_table.setCellWidget(row, 5, enabled_checkbox)

                buy_button = QPushButton("Buy")
                buy_button.clicked.connect(lambda _, c=coin: self.buy_coin(c))
                self.stats_table.setCellWidget(row, 6, buy_button)

                sell_button = QPushButton("Sell")
                sell_button.clicked.connect(lambda _, c=coin: self.sell_coin(c))
                self.stats_table.setCellWidget(row, 7, sell_button)

                logging.info(f"Updated row for {coin}: balance={balance}, current_price={current_price}, usd_value={usd_value}")
            except Exception as e:
                logging.error(f"Error updating row for {coin}: {e}")

        self.stats_table.resizeColumnsToContents()

    def toggle_test_mode(self, state):
        try:
            settings = load_settings()
            settings['testing'] = bool(state)
            update_settings(settings)
            self.log("Test mode " + ("enabled" if state else "disabled"))
        except Exception as e:
            self.log(f"Error toggling test mode: {e}")

    def toggle_coin_enabled(self, coin, state):
        try:
            coins_settings = load_coins_settings()
            coins_settings[coin]['enabled'] = bool(state)
            update_coins_settings(coins_settings)
            self.log(f"{coin} trading " + ("enabled" if state else "disabled"))
        except Exception as e:
            self.log(f"Error toggling coin enabled state for {coin}: {e}")

    def update_data(self):
        try:
            Trends.check_price_trends()
            coins_settings = load_coins_settings()
            self.coinbase_client.refresh_balances_and_prices(coins_settings)
            self.update_stats_table(coins_settings)
            self.update_chart()
        except Exception as e:
            self.log(f"Error updating data: {e}")

    #Temperary functions 
    def buy_coin(self, coin):
        try:
            # Implement buy logic here
            success, order_id, error = self.coinbase_client.place_market_order(coin, 'buy')
            if success:
                self.log(f"Buy order placed for {coin}. Order ID: {order_id}")
            else:
                self.log(f"Failed to place buy order for {coin}: {error}")
        except Exception as e:
            self.log(f"Error placing buy order for {coin}: {e}")
    
    #Temperary functions
    def sell_coin(self, coin):
        try:
            # Implement sell logic here
            success, order_id, error = self.coinbase_client.place_market_order(coin, 'sell')
            if success:
                self.log(f"Sell order placed for {coin}. Order ID: {order_id}")
            else:
                self.log(f"Failed to place sell order for {coin}: {error}")
        except Exception as e:
            self.log(f"Error placing sell order for {coin}: {e}")

    def save_settings(self):
        try:
            settings = load_settings()
            settings['refresh_interval'] = self.refresh_interval_input.value()
            settings['sale_threshold'] = self.sale_threshold_input.value()
            settings['loss_limit'] = self.loss_limit_input.value()
            update_settings(settings)
            self.log("Settings saved")
        except Exception as e:
            self.log(f"Error saving settings: {e}")

    def log(self, message):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"{timestamp} - {message}"
        self.log_window.append(log_message)

    def update_chart(self):
        # Placeholder for updating charts based on data
        pass


def main():
    app = QApplication(sys.argv)
    window = TradingBotGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
