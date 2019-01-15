from pylivetrader.api import order_target, symbol
from pylivetrader import *
from iexfinance.stocks import Stock
from iexfinance import get_available_symbols
from iexfinance import get_iex_listed_symbol_dir
from iexfinance.stocks import get_todays_earnings
from iexfinance.base import _IEXBase
from urllib.parse import quote
import pandas as pd
from Reports import *
import datetime



#
# Target 
#
# Class that queries sectors by stock and returns a filtered list
# of those stocks that have fully validated data sets
#
class Target(object):
    
    def __init__(self):

        # self.sectors = {"Energy":{"sector weight":.10}}
        self.masterFrame = None

        self.sectors = {"Healthcare":{"sector weight":.10},
            "Basic Materials":{"sector weight":.08},
            "Financial Services":{"sector weight":.08},
            "Industrials":{"sector weight":.09},
            "Technology":{"sector weight":.11},
            "Consumer Cyclical":{"sector weight":.12},
            "Real Estate":{"sector weight":.06},
            "Consumer Defensive":{"sector weight":.09},
            "Energy":{"sector weight":.080},
            "Utilities":{"sector weight":.06},
            "Communication Services":{"sector weight":.13}
            }

    #
    # method that retuuirns the IEX sectors in a list
    #
    def getSectors(self):
        return [sector for sector in self.sectors]

    #
    # checkEPS
    #
    # method that filters for two years of positive EPS
    #
    def checkEPS(self, sector, symbol):

        #
        # index the data reports
        #
        earningsReports = self.sectors[sector]['earnings'][symbol]

        if len(earningsReports) < 4:
            # The company must be very new. We'll skip it until it's had time to
            # prove itself.
            return False

        # earnings_reports should contain the information about the last four
        # quarterly reports.
        for report in earningsReports:

            # We want to see consistent positive EPS.
            try:

                if not (report['actualEPS']):
                    return False

                if report['actualEPS'] < 0:
                    return False

            except KeyError:
                # A KeyError here indicates that some data was missing or that a company is less than two years old.
                # We don't mind skipping over new companies until they've had more
                # time in the market.
                return False

            return True

    #
    # checkData
    #
    # method that checks to see tthat all of the neccessary
    # data is presented.
    #
    def checkData(self, sector, symbol):

        #
        # index the data reports
        #
        financials = self.sectors[sector]['financials'][symbol]
        quote = self.sectors[sector]['quote'][symbol]
        stats = self.sectors[sector]['stats'][symbol]
        earnings = self.sectors[sector]['earnings'][symbol]

        if len(financials) < 1 or quote['latestPrice'] is None:
            return
        try:
            if not (
                    quote['marketCap'] and
                    quote['peRatio'] and
                    stats['priceToBook'] and
                    stats['sharesOutstanding'] and
                    financials[0]['totalAssets'] and
                    financials[0]['currentAssets'] and
                    financials[0]['currentDebt'] and
                    quote['latestPrice']
            ):
                return False
        except KeyError:
            # A KeyError here indicates that some data we need to evaluate this
            # stock was missing.
            return False

        return True

    #
    # calcRatios
    #
    # method that calcs the ratios used as criteria to build the
    # positions
    #
    def calcRatios(self, sector, symbol):

        fundementals = {}
        baseline = 1000000

        #
        # start witht he financial data
        #
        financials = self.sectors[sector]['financials'][symbol]

        #
        # Calculate PB ratio.
        #
        stats = self.sectors[sector]['stats'][symbol]
        fundementals['pb_ratio'] = stats['priceToBook']

        #
        # Find the "Current Ratio" - current assets to current debt.
        #
        current_debt = financials[0]['currentDebt'] if financials[0]['currentDebt'] else 1
        fundementals['current_ratio'] = financials[0]['currentAssets'] / current_debt

        #
        # Find the ratio of long term debt to short-term liquiditable assets.
        #
        total_debt = financials[0]['totalDebt'] if financials[0]['totalDebt'] else 0
        fundementals['debt_to_liq_ratio'] = total_debt / financials[0]['currentAssets']

        #
        # Store other information for this stock so we can filter on the data
        # later.
        #
        quote = self.sectors[sector]['quote'][symbol]
        stats = self.sectors[sector]['stats'][symbol]
        fundementals['pe_ratio'] = quote['peRatio']
        fundementals['market_cap'] = quote['marketCap'] / baseline
        fundementals['dividend_yield'] = stats['dividendYield']

        return fundementals

    #
    # filterTargets
    #
    # method that checks for valid data and then populates the target
    # stock in the sector dictionary
    #
    def filterTargets(self):

        for sector in self.sectors:

            #
            # process each stock in turn
            #
            stocks = self.sectors[sector]['stocks']

            filteredDict = {}
            for symbol in stocks:
                # print(symbol)
                #
                # check for positive earning and that all relevant data
                # exists
                #
                if not self.checkEPS(sector, symbol) or not self.checkData(sector, symbol):
                    continue

                #
                # calc the ratios
                #
                filteredDict[symbol] = self.calcRatios(sector, symbol)
                filteredDict[symbol].update({'Weight': 0})
            #
            # se the targets
            #
            self.sectors[sector]['targets'] = filteredDict

        #
        # the filtered target list is done so build out
        # the data frames
        #
        self.buildDataFrames()


    #
    # updateSectorTargets
    #
    # method that batch processes the stock for each sector.  The
    # max number of stock that be returned ina quote is 100.
    #
    def updateSectorTargets(self):
        #
        # do each sector in turn
        #
        for sector in self.sectors:
            print("Processing {}".format(sector), end=' ')
            #
            # get the stocks
            #
            stocks = get_sector(sector)

            #
            # check that the sctor exists
            #
            if len(stocks) == 0:
                raise ValueError("Invalid sector name: {}".format(sector))


            #
            # register new dictionary entries to save all of the
            # symbol data for later recall and sorting
            #
            financials = self.sectors[sector]['financials'] = {}
            quote = self.sectors[sector]['quote'] = {}
            stats = self.sectors[sector]['stats'] = {}
            earnings = self.sectors[sector]['earnings'] = {}

            #
            # setup to process 100 stocks at a time until exhausted
            #
            sectorStocks = []
            batchIndex = 0
            maxBatch = 99
            while batchIndex < len(stocks):
                #
                # get the next batch of stocks and build a symbol list
                #
                stockList = [s['symbol'] for s in stocks[batchIndex:batchIndex + maxBatch]]
                sectorStocks.extend(stockList)

                stockReader = Stock(stockList)


                #
                # get all of the relevant data needed to validate each
                # stock in turn
                #
                financialsJSON = stockReader.get_financials()
                quotesJSON = stockReader.get_quote()
                statsJSON = stockReader.get_key_stats()
                earningsJSON = stockReader.get_earnings()


                #
                # loda the data dictionaries -- create a
                # new catalog for each data set by symbol
                for symbol in stockList:
                    financials[symbol] = financialsJSON[symbol]
                    quote[symbol] = quotesJSON[symbol]
                    stats[symbol] = statsJSON[symbol]
                    earnings[symbol] = earningsJSON[symbol]

                batchIndex += maxBatch
                print(".", end=' ')



            #
            # store the complete stock list that has been
            # registered
            #
            self.sectors[sector]['stocks'] = sectorStocks
            print("\n")

        self.filterTargets()

    #
    # concatenateFrame
    #
    # method that combines the scetor frames into one
    # master frame
    #
    def concatenateFrames(self):

        frameList = []
        for sector in self.sectors:

            frameExist = self.sectors[sector].get("data frame")
            if(frameExist is not None):
                df = self.sectors[sector]['data frame']
                #
                # the overall weight is the sector weight by the stock
                # frame weight
                #
                df.Weight = df.Weight * self.sectors[sector]['sector weight']
                frameList.append(df)

        if(len(frameList)):
            self.masterFrame = pd.concat(frameList)


    #
    # method that creates the data frames from the filtered stocks, and filters on the criteria
    # and then sets the weight based on market cap
    #
    def buildDataFrames(self):

        for sector in self.sectors:
            dataFrame = {}

            #
            # create the data frame
            #
            df = pd.DataFrame.from_dict(self.sectors[sector]['targets']).T

            #
            # apply the data criteria
            #
            df = df[(df.current_ratio > 1.5) & (df.pe_ratio < 16) & (df.pb_ratio < 1.2) & (df.dividend_yield > 1.0)]

            #
            # check to see that we have stocks in the sctor.  Sector weighting is done
            # only when at least one share is present
            #
            if len(df) > 0:
                #
                # set the weights for each of the stocks in the sector
                #
                sectorMarketCap = df['market_cap'].sum()
                df['Weight'] = df['market_cap'] / sectorMarketCap

                #
                # store the completed data frame in the sector
                # dictionary
                #
                self.sectors[sector]['data frame'] = df

        #
        # build the master fraem froma by combining of the
        # the sctor frames
        #
        self.concatenateFrames()


    def getDividendYields(self):

        symbols = [s['symbol'] for s in get_available_symbols()]


        dividendStocks = {}
        batchIndex = 0
        maxBatch = 99
        while(batchIndex < len(symbols)):
            slicedSymbols = symbols[batchIndex:batchIndex + maxBatch]
            stocks = Stock(slicedSymbols)
            stats = stocks.get_key_stats()
            quote = stocks.get_quote()
            companiesInfo = stocks.get_company()

            for symbol in slicedSymbols:
                dividendStats = {}
                try:
                    if (
                        stats[symbol]['dividendYield'] and
                        stats[symbol]['dividendRate'] and
                        companiesInfo[symbol]['issueType'] and
                        companiesInfo[symbol]['issueType'] ==  "cs" and
                        companiesInfo[symbol]['sector'] != 'Financial Services' and
                        quote[symbol]['sector'] == 'Industrials'
                    ):



                        dividendStats['Dividend Yield'] = stats[symbol]['dividendYield']
                        dividendStats['Dividend Rate'] = stats[symbol]['dividendRate']
                        dividendStocks[symbol] = dividendStats
                except:
                    continue
            batchIndex += maxBatch

        print(len(dividendStocks))
        df = pd.DataFrame.from_dict(dividendStocks).T
        df = df.sort_values('Dividend Yield')
        print(df)



    #
    # rebalance
    #
    # method that sells unwamted stock and then buys
    # the new targeted stocks.
    #
    def rebalance(self, context):

        #
        # xell any stocks that are not in the new list of
        # stocks to be purchased
        #
        desiredStocks = self.masterFrame.index.values
        for stock in context.portfolio.positions:
            if stock not in desiredStocks:
                order_target_percent(stock, 0)

        #
        # set the target weights for the stocks.  The weight is the sector weight
        # as a percentage of the portolio allocation
        #
        self.displayMasterFrame()
        df = self.masterFrame
        for stock in desiredStocks:
            try:
                print('Buying {}'.format(stock))
                weight = self.getWeight(stock, df)
                order_target_percent(symbol(stock), weight)
            except:
                print('Error: Tried to purchase {} but there was an error.'.format(stock))
                pass

    #
    # sendUpdate
    #
    # method that send an email update with the day's
    # performance
    #
    def sendUpdate(self, context):
        print("Send update")

    #
    # getWeight
    #
    # method that looks up the symbol and returns the sector
    # allocation weight
    #
    def getWeight(self, symbol, df):
        #s = df.index.values
        i = pd.Index(df.index.values).get_loc(symbol)
        col = df.columns.get_loc("Weight")
        weight = df.iloc[i, col]
        return weight

    #
    # displayFrame
    #
    # pretty print the data frame for each sector
    #
    def displayFrame(self):

        for sector in self.sectors:
            #
            # transpose the data frame so data fields label the columns
            #
            frameExist = self.sectors[sector].get('data frame')
            if(frameExist is not None):
                df = self.sectors[sector]['data frame']
                df = df.applymap("{:,.2f}".format)

                #
                # nice user labels
                #
                df.columns = ['Weight', 'Current', 'Debt/Lq', 'Dividend', 'Market Cap', 'Price/Book', 'PE']

                print("{} -> {}".format(sector, df['Current'].count()))
                print("{}\n".format(df.to_string()))

    #
    # displayAllocations
    #
    # method that loads an allocation frame
    # and prints the output
    #
    def displayAllocations(self):
        #
        # output the allocations at startup
        #
        df = pd.DataFrame.from_dict(self.sectors).T
        df = df[['sector weight']]


        if sum(df['sector weight'] > 100):
            print("Allocation exceeds 100%")

        df.loc['sum'] = df.sum()
        print("{}\n".format(df.to_string(formatters={'sector weight': '{:,.2%}'.format})))

    #
    # displayMaster Frame
    #
    # method that displays the concatenated sector frames.  This
    # the frame used to buy and sell securties
    #
    def displayMasterFrame(self):


        if(self.masterFrame is not None):
            df = self.masterFrame
            df = df.applymap("{:,.4f}".format)

            #
            # nice user labels
            #
            df.columns = ['Weight', 'Current', 'Debt/Lq', 'Dividend', 'Market Cap', 'Price/Book', 'PE']

            print("Master Frame -> {}\n{}\n".format(df['Current'].count(), df.to_string()))
            print("Master Frame Weight: {:.4}\n\n".format(self.masterFrame['Weight'].sum()))

    def displayRuntime(self):
        self.displayFrame()
        self.displayMasterFrame()

#
# SectorCollection
#
# extend IEX Finance to add a class that enables query of stocks by sector.
# this is a new endpoint.
#
class SectorCollection(_IEXBase):

    def __init__(self, sector, **kwargs):
        self.sector = quote(sector)
        self.output_format = 'json'
        super().__init__(**kwargs)

    @property
    def url(self):
        return '/stock/market/collection/sector?collectionName={}'.format(self.sector)

#
# get_sector
#
# method that callerd to query the stocks by sector
#
def get_sector(sector_name):
    collection = SectorCollection(sector_name)
    return collection.fetch()



myTargets = Target()
#myTargets.updateSectorTargets()
#myTargets.displayRuntime()
#myTargets.displayAllocations()

#generateEndDayReport(myTargets.getSectors())


#myTargets.getDividendYields()

#
# initialize
#
# method invoked by pylivetrader at start up
#
def initialize(context):
    print("Initializing trading system")
    # myTargets = Target()
    # myTargets.displayAllocations()
    # myTargets.updateSectorTargets()

    #context.masterFrame = myTargets.masterFrame
    context.sectors = myTargets.getSectors()
    schedule_function(generateEndDayFile, date_rule=date_rules.every_day(), time_rule=time_rules.market_close())

def handle_data(context, data):
    #myTargets.rebalance(context)
    pass






