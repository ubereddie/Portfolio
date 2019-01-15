from pylivetrader.api import order_target, symbol

def initialize(context):


    print("Initializing trading system")


def handle_data(context, data):
    #
    # sell any stocks that are not in the new list of
    # stocks to be purchased
    #
    print("Liquidating...")
    for stock in context.portfolio.positions:
            order_target_percent(stock, 0)