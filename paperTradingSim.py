import yfinance as yf
import csv
from datetime import datetime
import os
import requests

#catch invalid tickers
class InvalidPeriodError(Exception):
    pass

#initialize/wipe
def initialize_account():
    with open('papertrading.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Action", "Ticker", "Shares", "Price", "Time", "Total Shares", "Balance", "Position", "PnL"])

    while True:
        try:
            starting_balance = float(input("Enter your starting account balance: "))
            if starting_balance > 0:
                break
            else:
                print("Please enter a number greater than zero.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open('papertrading.csv', 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Deposit", "x", "x", "x", time, "x", starting_balance, "x", "x"])

        
def get_current_price(ticker):
    stock = yf.Ticker(ticker)
    todays_data = stock.history(period='1d')
    return todays_data['Close'][0]


def get_balance():
    with open('papertrading.csv', 'r', newline='') as file:
        reader = csv.reader(file)
        next(reader)  # Skip the header row

        rows = list(reader)
        if rows:
            return float(rows[-1][6])
        else:
            return None


#returns dictionary with open position tickers
def open_positions(ticker=None):
    open_positions_dict = {}
    
    with open('papertrading.csv', 'r', newline='') as file:
        reader = csv.reader(file)
        next(reader)  # Skip header row if it exists
        
        for row in reader:
            if row[7] == 'open' and (ticker is None or row[1] == ticker):
                if row[1] not in open_positions_dict:
                    open_positions_dict[row[1]] = []
                open_positions_dict[row[1]].append(row)
    
    return open_positions_dict


def get_open_position_total(ticker):
    shareNumber = 0
    shares_short = 0
    shares_long = 0
    owned_shares = open_positions(ticker)
    for asset, data in owned_shares.items():
        if data != []:
            shareNumber = sum([int(row[5]) for row in data])
    if shareNumber < 0:
        shares_short = shareNumber
    if shareNumber > 0:
        shares_long = shareNumber
    return shareNumber, shares_short, shares_long


#calculates postional transactions entered by the user and manages csv file
def update_ledger(action, ticker, shareOrder, balance):
    time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    current_price = get_current_price(ticker)
    open_transactions = open_positions(ticker)
    shareNumber, shares_short, shares_long = get_open_position_total(ticker)
    total_open_for_ticker = shareNumber
    original_order = shareOrder  

    if action == 'buy':

        if total_open_for_ticker >= 0:  # check for long position to add to

            sellCost = current_price * shareOrder
            balance -= sellCost
            with open('papertrading.csv', 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([action, ticker, shareOrder, current_price, time, shareOrder, balance, "open", ""])  # added new open position

        elif total_open_for_ticker < 0 and shareOrder <= abs(shares_short):  # we are short and have enough shares to buy

            for transaction in open_transactions[ticker]:  # iterate to find open positions and close them in time order, calculate positions, balance, pnl
                transaction_shares = int(transaction[5])
                transaction_price = float(transaction[3])
                transaction_time = transaction[4]

                if shareOrder == abs(transaction_shares):  # Can only fill orders up to the amount of the transaction or up to the shareOrder, whichever comes first
                    filledOrder = abs(transaction_shares) 
                else:
                    filledOrder = shareOrder 

                pnl = (transaction_price - current_price) * transaction_shares  # short calculation for transaction share bought
                balance += filledOrder * transaction_price  # update balance for negative fillOrder
                transaction_shares += filledOrder  # updates amount of shares for open position

                # region / Updates transactions as closed or open through the openTransactions loop
                with open('papertrading.csv', 'r', newline='') as file:
                    rows = list(csv.reader(file))
                with open('papertrading.csv', 'w', newline='') as file:
                    writer = csv.writer(file)
                    for row in rows:
                        if row[1] == ticker and row[4] == transaction_time:
                            if transaction_shares == 0:
                                row[5] = transaction_shares + filledOrder #if shares left is zero, transaction is going to be marked closed, fill in the total amount closed
                                row[7] = "closed"
                                row[8] = pnl
                            else:
                                row[5] = transaction_shares
                        writer.writerow(row)  # update previous transaction
                # endregion
            with open('papertrading.csv', 'a', newline='') as file:  # log the buy as closed because we have enough shares to buy
                writer = csv.writer(file)
                writer.writerow([action, ticker, original_order, current_price, time, original_order, balance, "closed", pnl])

        else:  # total_open_for_ticker > shareOrder = don't have enough and will go long

            for transaction in open_transactions[ticker]:  # Find all open positions and cover them
                transaction_shares = int(transaction[5]) 
                transaction_price = float(transaction[3])
                transaction_time = transaction[4]

                filledOrder = abs(transaction_shares)
                pnl = (transaction_price - current_price) * transaction_shares  # short calculation for short liquidation of transaction
                balance += transaction_price * filledOrder  # balance updated with purchase of short positions
                shareOrder -= filledOrder
            
                with open('papertrading.csv', 'r', newline='') as file:
                    rows = list(csv.reader(file))
                with open('papertrading.csv', 'w', newline='') as file:
                    writer = csv.writer(file)
                    for row in rows:
                        if row[1] == ticker and row[4] == transaction_time:
                            row[5] = filledOrder  # Wanted this to reflect the total number of shares either sold/bought when closed for the transaction #change to zero if wanted to reflect active contracts
                            row[7] = "closed"
                            row[8] = pnl
                        writer.writerow(row)  # update previous transaction

            # enter long positions with remaining shares
            buyCost = current_price * shareOrder
            balance -= buyCost
            with open('papertrading.csv', 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([action, ticker, original_order, current_price, time, shareOrder, balance, 'open', ''])  # added new open position            
    
    if action == 'sell':
            
        if total_open_for_ticker <= 0:  # check for short position to add to
                       
            buyCost = current_price * shareOrder
            balance -= buyCost
            with open('papertrading.csv', 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([action, ticker, -shareOrder, current_price, time, -shareOrder , balance, "open", ""])  # added new open position
                              
        elif total_open_for_ticker > 0 and shareOrder <= total_open_for_ticker:  # we are long and have enough shares to sell

            for transaction in open_transactions[ticker]:  # iterate to find open positions and close them in time order, calculate positions, balance, pnl
                transaction_shares = int(transaction[5])
                transaction_price = float(transaction[3])
                transaction_time = transaction[4]
                    
                if shareOrder >= transaction_shares: #Can only fill orders up to the amount of the transaction or up to the shareorder, whichever comes first
                    filledOrder = transaction_shares
                else:
                    filledOrder = shareOrder  
                    
                pnl = (current_price - transaction_price) * transaction_shares  # long calculation for transaction share sold
                balance += filledOrder * transaction_price  #update balance                    
                transaction_shares -= filledOrder      
                    
                #region / Updates transactions as closed or open each transaction iteration
                with open('papertrading.csv', 'r', newline='') as file:
                    rows = list(csv.reader(file))
                with open('papertrading.csv', 'w', newline='') as file: 
                    writer = csv.writer(file)
                    for row in rows:
                        if row[1] == ticker and row[4] == transaction_time:
                            if transaction_shares == 0:
                                row[5] = transaction_shares + filledOrder
                                row[7] = "closed"
                                row[8] = pnl
                            else: 
                                row[5] = transaction_shares
                        writer.writerow(row)  #update previous transaction   
                #endregion
            with open('papertrading.csv', 'a', newline='') as file: # log the sell as closed because we have enough shares to sell
                writer = csv.writer(file)
                writer.writerow([action, ticker, -original_order, current_price, time, -original_order, balance, "closed", pnl])  
                                
            # commented out because we want total shares to be reflected in total bought or closed for the transaction #uncomment if wanted to reflect active contracts 
            # region / Closing positions within the for loop above does not update the total shares for closed tickers, this cleans up those transactions logs
            '''with open('papertrading.csv', 'r', newline='') as file:
                rows = list(csv.reader(file))
            update_close_position_totals = True            
            for row in rows:
                if row[1] == ticker and row[7] == "open": #check, if all positions are 'closed', set total shares to zero for that ticker
                    update_close_position_totals = False           
            if update_close_position_totals: # Update the rows if needed
                for row in rows:
                    if row[1] == ticker:
                        row[5] = 0          
            with open('papertrading.csv', 'w', newline='') as file: # Write the updated rows back to the file
                writer = csv.writer(file)
                for row in rows:
                    writer.writerow(row)'''
            # endregion                                         
                                                       
        else: #total_open_for_ticker < shareorder = don't have enough and will go short                    
            
                for transaction in open_transactions[ticker]:  #Find all open positions and cover them
                    transaction_shares = int(transaction[5]) #Will be positive
                    transaction_price = float(transaction[3])
                    transaction_time = transaction[4]                   
                    
                    filledOrder = transaction_shares
                    pnl = (current_price - transaction_price) * transaction_shares  # long calculation for long liquidation of transaction
                    balance += transaction_price * transaction_shares #balance updated with sale of long positions
                    shareOrder -= transaction_shares
                                        
                    with open('papertrading.csv', 'r', newline='') as file:
                        rows = list(csv.reader(file))
                    with open('papertrading.csv', 'w', newline='') as file: 
                            writer = csv.writer(file)
                            for row in rows:
                                if row[1] == ticker and row[4] == transaction_time:
                                    row[5] = filledOrder #Wanted this to reflect the total number of shares either sold/bought when closed for the transaction #change to zero if wanted to reflect active contracts
                                    row[7] = "closed"
                                    row[8] = pnl
                                writer.writerow(row)  #update previous transaction
                
                #enter short positions with remaining shares               
                sellCost = current_price * shareOrder
                balance -= sellCost
                with open('papertrading.csv', 'a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow([action, ticker, 0 - original_order, current_price, time, -shareOrder, balance, 'open', ''])  # added new open position
                        
#cover long or short                                                                                   
def go_flat(ticker=None):
    if not ticker:
        tickers_to_flatten = get_unique_tickers()
    else:
        tickers_to_flatten = [ticker]

    for ticker in tickers_to_flatten:
        shareNumber, shares_short, shares_long = get_open_position_total(ticker)
        balance = get_balance()
        
        if shareNumber > 0:
            action = "sell"
            update_ledger(action, ticker, shares_long, balance)
        elif shareNumber < 0:
            action = "buy"
            update_ledger(action, ticker, shares_short, balance)
        else:
            continue


#get list of tickers in account
def get_unique_tickers():
    unique_tickers = set()
    with open('papertrading.csv', 'r', newline='') as file:
        reader = csv.reader(file)
        for row in reader:
            if row[1] != "":
                unique_tickers.add(row[1])
    return list(unique_tickers)

#program flow control / Main
def paper_trading():
    #if files required do not exist
    if not os.path.isfile('papertrading.csv') or os.stat('papertrading.csv').st_size == 0:
        initialize_account() 
    
    while True:
        #get balance -> catch if database becomes corrupted
        try:
                balance = get_balance()
        except Exception as e: 
                print("Error fetching balance:", e)
                user_choice = input("Would you like to wipe the account and start over? (yes/no): ").lower()
                if user_choice == 'yes':
                    initialize_account()
                    balance = get_balance()
                else:
                    paper_trading()
                
        print(f"Current account balance: ${balance:.2f}")
        
        #prompt user for intial input action or ticker
        ticker = input("Enter a stock ticker, type 'balance' to check your balance and positions, 'wipe' to reset your account, 'flat' to go flat on a stock or entire account: ").upper()
        
        if ticker == 'BALANCE':
            balance = get_balance()
            positions = open_positions()
            if positions:
                print("Your current positions are:")
                for asset, data in positions.items():
                    if data != []:
                        shares = sum([int(row[5]) for row in data])
                        print(f"{asset}: {shares} shares")
            else:
                print("You don't have any open positions.")
        elif ticker == 'WIPE':
            confirm = input("Are you sure you want to reset your account and wipe all transactions? (yes/no) ").lower()
            if confirm == 'yes':
                initialize_account()
                print("Your account has been reset.")
            else:
                print("Account reset canceled.")
        elif ticker == 'FLAT':
            open_positions_dict = open_positions()
            specific_ticker = input("Enter a specific stock ticker to go flat on or type 'all' to go flat on your entire account or 'back': ").upper()
            if specific_ticker == 'ALL':
                if open_positions_dict:
                    go_flat()
                    print("All positions flattened")    
                else:
                    print("No positions open")          
            elif specific_ticker == 'BACK':
                continue
            else:
                if specific_ticker in open_positions_dict:
                    go_flat(specific_ticker)
                    print(f"{specific_ticker} position flattened")
                  
                else:
                    print(f"You don't have an open position in {specific_ticker}.")
        #catch invalid tickers
        else:
            try:
                info = yf.Ticker(ticker).info
                if 'shortName' not in info:
                    raise ValueError("Invalid ticker.")
            except (ValueError, requests.exceptions.HTTPError):
                print(f"{ticker} is not a valid ticker symbol.")
                continue
            except InvalidPeriodError as e:
                print(e)
                continue
            else:
                #reports current price
                current_price = get_current_price(ticker)
                print(f"Current price of {ticker}: ${current_price:.2f}")
                shareNumber, shares_short, shares_long = get_open_position_total(ticker)
                #prompts user for action on ticker
                action = input("Enter 'buy', 'sell': ").lower()
                if action not in ['buy', 'sell']:
                    print("Invalid action")
                elif action == 'buy':
                    while True:
                        try:
                            shares = abs(int(input("Enter the number of shares: ")))
                            if shares > 0:
                                break
                            else:
                                print("Please enter a number greater than zero.")
                        except ValueError:
                                print("Invalid input. Please enter a number.")
                    shares_short = 0
                    shareNumber = 0
                    balance = get_balance()
                    price = get_current_price(ticker)                  
                    shares_short = shareNumber
                    buyCost = (shares-abs(shares_short)) * price 
                    if balance < buyCost:
                        print("Not enough funds for purchase")
                    else:
                        update_ledger('buy', ticker, shares, balance)  
                elif action == 'sell':
                    shares = abs(int(input("Enter the number of shares: ")))
                    shares_long = 0
                    shareNumber = 0
                    balance = get_balance()
                    price = get_current_price(ticker)
                    shares_long = shareNumber
                    sellCost = (shares-shares_long) * price
                    if balance < sellCost:
                        print("Not enough funds for purchase")
                    else:
                        update_ledger('sell', ticker, shares, balance)            


if __name__ == "__main__":
    paper_trading()
