class Strategy:
    # option setting needed
    def __setitem__(self, key, value):
        self.options[key] = value

    # option setting needed
    def __getitem__(self, key):
        return self.options.get(key, "")

    def __getattr__(self, key):
        if key in self.options:
            return int(self.options.get(key, ""))

    def __init__(self):
        # strategy property
        self.subscribedBooks = {
            "Bitfinex": {"pairs": ["ETH-USDT"]},
        }
        self.period = 10 * 60
        self.options = {}
        self.invest = 0

        # user defined class attribute
        self.last_type = None
        self.last_cross_status = None
        self.trace = np.empty((0, 5))
        self.close_price_trace = np.array([])
        self.orders = []
        self.UP = 1
        self.DOWN = 2
        self.max_buy_price = 0

    def abs(self, value):
        return value if value > 0 else -value

    def smooth(self, l, weight=None):
        if weight is None:
            weight = float(self["weight"])
        scalars = l.tolist()
        last = None
        smoothed = []
        for point in scalars:
            if np.isnan(point):
                last = None
                smoothed.append(point)
                continue
            if last is None:
                last = point
                smoothed.append(point)
                continue
            # Calculate smoothed value
            smoothed_val = last * weight + (1 - weight) * point
            smoothed.append(smoothed_val)  # Save it
            last = smoothed_val  # Anchor the last smoothed value

        return np.array(smoothed)

    # called every self.period
    def trade(self, information):
        """
        {
            "assets":{
                "Bitfinex":{
                    "ETH": 0.0,
                    "USDT": 10000.0
                }
            },
            "candles": {
                "Bitfinex":{
                    "ETH-USDT":[
                        "open": 416.55,
                        "high": 416.65,
                        "Iow": 415.76,
                        "close": 416.47941946,
                        "volume": 10.50279728,
                        "time": "2020-10-23T12:30:00.000Z"
                    ]
                }
            }
        }
        """
        exchange = 'Binance'
        pair = "ETH-USDT"
        current_status = information["candles"][exchange][pair][0]
        close_price = current_status["close"]
        asset_ETH = information["assets"][exchange]["ETH"]
        asset_USDT = information["assets"][exchange]["USDT"]

        # add latest price into trace
        self.trace = np.append(
            self.trace,
            [
                [
                    current_status["open"],
                    current_status["high"],
                    current_status["low"],
                    current_status["close"],
                    current_status["volume"],
                ]
            ],
            axis=0,
        )

        if self.trace.shape[0] < 12 + 16:
            return []

        amount = 0
        action = None

        rsi = talib.RSI(self.trace[:, 3], 9)
        adx = talib.ADX(self.trace[:, 1], self.trace[:, 2], self.trace[:, 3], 12)

        current_rsi = rsi[-1]
        current_adx = adx[-1]
        rsi_diff = rsi[-1] - rsi[-3]
        if rsi[-3] > 70 and current_rsi > 70 and current_adx < 50:
            action = "sell"
            amount = self.invest
        elif (current_adx > 50 and current_rsi < 30) or (
            current_status["close"] < self.max_buy_price * 0.9
        ):
            action = "sell"
            amount = self.invest
        elif current_adx > 50 and current_rsi > 70 and rsi_diff > 10:
            action = "buy"
            amount = np.min(
                [
                    2
                    ** (
                        int(current_status["close"] - np.min(self.trace[:, 3][-3:]))
                        // 1.5
                    ),
                    asset_USDT // current_status["close"],
                ]
            )
            self.max_buy_price = max(current_status["close"], self.max_buy_price)
        self.last_type = action
        if amount == 0:
            return []
        if action:
            Log(f"{self.last_type} | {current_adx} | {current_rsi} | {rsi_diff}")
        order = []
        if action == "buy":
            self.invest += amount
            order = [
                {
                    "exchange": exchange,
                    "amount": amount,
                    "price": -1,
                    "type": "MARKET",
                    "pair": pair,
                }
            ]
        elif action == "sell":
            order = [
                {
                    "exchange": exchange,
                    "amount": -amount,
                    "price": -1,
                    "type": "MARKET",
                    "pair": pair,
                }
            ]
            self.invest -= amount
        return order
