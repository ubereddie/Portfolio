import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


#
# sendReport
#
# method that creates an HTML email and sends using the
# Google email system
#
def sendReport(df):

    with open('recipients') as f:
        emails = f.read().splitlines()
    f.close()

    #recipients = ["eddie@exigenthq.com", "ubereddie@icloud.com"]

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.ehlo()  # optional    # ...send emails
        server.login("eddie@exigenthq.com", "froboz7104!")

        for email in emails:
            msg = MIMEMultipart()

            # setup the parameters of the message
            msg['To'] = email
            msg['From'] = 'eddie@exigenthq.com'
            msg['Subject'] = "Eddie's Stock Follyio Report"

            # add in the message body
            msg.attach(MIMEText(df.to_html(), 'HTML'))
            # server.sendmail(email, email, "test mail")



            server.send_message(msg)
            del msg

        # Terminate the SMTP session and close the connection
        server.quit()

        print('Email sent!')
    except Exception as e:
        print('Error: could not send email...{}'.format(e))

#
# generateEndDayFile
#
# method called at the end of day that processes the portoflio
# posaitions.  The postional data for each asset is written to a file
# so that a report can be generated later without having to have the
# market be active
#
def generateEndDayFile(context):

    #
    # get all the postions hel;d on account
    #
    positions = [equity.symbol for equity in context.portfolio.positions]

    #
    # queries have a max length
    #
    if len(positions) > 100 :
        print("Warning: maximum query length exceeded generating file")

    #
    # get all of the data needed to be written out for
    # later processing
    #
    stocks = Stock(positions)
    quotes = stocks.get_quote()
    companies = stocks.get_company()

    #
    # build a dictionary entry for each position and its asscoiated
    # data in turn> Format: POSITION:{basis:x, amount:x, market:x, sector:s}
    #
    positionsDict = {}
    for position in positions:
        #
        # data dictionary
        #
        assetData = {}

        #
        # cost basis
        #
        basis = context.portfolio.positions[symbol(position)].cost_basis
        assetData['basis'] = basis

        #
        # Number of shares
        #
        shares = context.portfolio.positions[symbol(position)].amount
        assetData['amount'] = shares

        #
        # current market price
        #
        market = quotes[position]['latestPrice']
        assetData['market'] = market

        #
        # sector
        #
        assetData['sector'] = companies[position]['sector']
        positionsDict[position] = assetData

    #
    # write the opandas data frame and pickle the file
    df = pd.DataFrame.from_dict(positionsDict).T

    try:
        df.to_pickle("positions.pkl")
    except:
        print("Error: could not genrate report pickle file")

#
# generatePositions
#
# method that reads in the pickle file and creates all of the relevant
# portfolio data
#
def generatePositions():
    #
    # get the pickle file info
    #
    df = pd.read_pickle("positions.pkl")

    #
    # calc the relevant portfolio entries
    #
    df['cost basis'] = df['basis'] * df['amount']
    df['market value'] = df['market'] * df['amount']
    df['gain/loss%'] = (df['market'] - df['basis']) / df['basis']
    df['gain/loss$'] = df['market value'] - df['cost basis']
    df['PL%'] = (df['gain/loss$'] / df['gain/loss$'].sum())

    #
    # sort by sector to make it easier to read
    #
    df = df.sort_values('sector')

    #
    # move the sector data to the end of the table
    #
    df = df[['amount', 'basis', 'market', 'cost basis', 'market value', 'gain/loss%', 'gain/loss$', 'PL%', 'sector']]

    return df

#
# generateSectors
#
# Build a table that has the profit contribution by
# sector
#
def generateSectors(df, sectors):

    #
    # Build a pandas series
    #
    yieldList = []
    sectorList = []
    for sector in sectors:
        #
        # check to make sure we have at least one stock
        # in that sector
        #
        if sector in df.sector.values:
            sectorReturn = df.loc[df['sector'] == sector, 'PL%'].sum()
            yieldList.append(sectorReturn)
            sectorList.append(sector)
    #
    # create the data frame
    #
    dfSector = pd.DataFrame(data=yieldList, columns=['sector%'], index=sectorList)
    dfSector.loc['Total'] = dfSector.sum()

    return dfSector

#
# generateEndDayReport
#
# method that reads the positions and associated data in from the pickle
# file created at market close and then generate a data frame.  Finally
# the data frame is emailed out a HTML document
#
def generateEndDayReport(sectors):

    dfPos = generatePositions()
    dfSector = generateSectors(dfPos, sectors)


    #
    # display the posiution data frame to the user
    #
    dfPos['gain/loss%'] = dfPos['gain/loss%'].apply('{:,.2%}'.format)
    dfPos['PL%'] = dfPos['PL%'].apply("{:,.2%}".format)
    print(dfPos.to_string())

    #
    # display the sector contributions
    #
    print(dfSector.to_string(header=["Sector Returns(%)"], formatters={'sector%': '{:,.2%}'.format}))

    #
    # send the email
    #
    sendReport(dfPos)






# myTargets.displayAllocations()
# myTargets.updateSectorTargets()
# myTargets.displayRuntime()
# from iexfinance.stocks import get_sector_performance
#
# df = get_sector_performance(output_format='pandas')
# df = pd.DataFrame.transpose(df)
# df = df['performance']
# print(df)