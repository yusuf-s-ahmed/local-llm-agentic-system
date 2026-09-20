import datetime as dt
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from mplfinance.original_flavor import candlestick_ohlc
import matplotlib
matplotlib.use('Agg')



plt.rcParams['font.family'] = 'Consolas'

def visualize(tickers: list):
    end = dt.datetime.today()
    start = end - dt.timedelta(days=6*30)  # last ~6 months

    # Create one figure with len(tickers) subplots
    fig, axes = plt.subplots(len(tickers), 1, figsize=(10, 4*len(tickers)), squeeze=False)
    axes = axes.flatten()  # ensure it's a 1D array even if only 1 ticker

    for ax, ticker in zip(axes, tickers):
        # Download data
        data = yf.download(ticker, start=start, end=end)
        data = data[['Open', 'High', 'Low', 'Close']]
        data.reset_index(inplace=True)
        data['Date'] = data['Date'].map(mdates.date2num)

        # Style the subplot
        ax.grid(True, color='lightgray')
        ax.set_axisbelow(True)
        ax.set_title(f'{ticker} Share Price', color='black')
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.set_facecolor('white')
        ax.tick_params(axis='x', colors='black')
        ax.tick_params(axis='y', colors='black')
        ax.xaxis_date()

        # Plot candlestick chart
        candlestick_ohlc(ax, data.values, width=0.5, colorup='#2ECC71', colordown='#E74C3C')

    plt.tight_layout()
    plt.savefig("data/stock_plot.png", bbox_inches="tight")
    plt.close(fig)

def plot_stock_data(tickers, stock_data, output_path="data/stock_plot.png"):
    fig, axes = plt.subplots(
        len(tickers),
        1,
        figsize=(10, 4 * len(tickers)),
        squeeze=False,
    )

    for index, ticker in enumerate(tickers):
        axis = axes[index][0]
        data = stock_data[ticker]

        axis.plot(data.index, data["Close"])
        axis.set_title(f"{ticker} Stock Price")
        axis.set_xlabel("Date")
        axis.set_ylabel("Price")
        axis.grid(True)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return output_path

# Example usage:

# tickers = ['AAPL', 'MSFT', 'GOOGL']
# visualize(tickers)