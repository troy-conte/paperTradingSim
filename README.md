# paperTradingSim
Simulation Trades based upon Yahoo Finance ticker data

This project is a script that attempts to simulate a stock trading account for the user. It starts by asking to create an account which includes the size. After the program establishes a baseline account amount, it will ask for a ticker from which it will retrieve a price from yfinance. The user is asked to either buy or sell the stock. The user can sell more than they possess, this is known as short selling. The program will account for selling, buying, and covering varying positional sizes and directions. The program will also update a csv for persistent storage of the transactions should the user want to save them for later. 

There are several core functions that run the program. The main one is paper_trading(), this one controls the flow of the script for the user. It starts by checking if there is a csv database, if not it will create one and run init() to get the user’s desired account size. It then will get the balance by asking for an input and then checking to make sure the input is greater than zero and is a valid number. The script continues by confirming account balance, formatted in dollar denomination and asks for input from the user of ‘balance, wipe,flat’. Each respectively has its own try, catch error controls that ensures users inputs are valid. If the input is not balance,wipe,or flat the script will assume the user tried to enter a ticker. It will then check for a valid ticker, pull the ticker’s updated share price, and ask if user wants to buy or sell. The buy/sell checks for cost of the transaction against the user’s balance before executing the trade by calling update_ledger().

	Update_ledger() is the function that carries the weight of the program. The main idea is that there are three scenarios to account for. The first is that we are in a position to add to, so we are selling into a flat or short position or buying into a long or flat position. The next is we are buying into a position where we have enough shares to cover the transaction. The third scenario accounts for transactions that we have shares but not enough to cover the transaction. This will search open positions, close them and open up the remainder of the order as new position in opposite direction. This is important as selling covered shares will garner back the cost of the share plus the pnl, whereas selling naked will charge the cost of the share and deduct it from the user’s balance. 	
