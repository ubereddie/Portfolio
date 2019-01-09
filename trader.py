from pylivetrader.api import order_target, symbol
import datetime

def initialize(context):
    context.i = 0
    context.asset = symbol('VZ')
    context.eddie = symbol('AAPL')
    
    print("Init")

def handle_data(context, data):
    


    # Trading logic
    # order_target orders as many shares as needed to
    # achieve the desired number of shares.
    print("placing Order {}".format(context.asset))

    order_target(context.asset, 10)
    order_target(context.eddie, 10)
    