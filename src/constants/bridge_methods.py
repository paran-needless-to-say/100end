METHODS: dict[str, dict[str, str]] = {
    '0x4d8160ba': {
        'function': 'strictlySwapAndCall(address _srcTokenIn,uint256 _srcAmountIn,bytes _srcTokenInPermitEnvelope,address _srcSwapRouter,bytes _srcSwapCalldata,address _srcTokenOut,uint256 _srcTokenExpectedAmountOut,address _srcTokenRefundRecipient,address _target,bytes _targetData)',
        'label': 'DeBridge'
    },
    '0xae328590': {
        'function': 'startBridgeTokensViaRelay(tuple _bridgeData,tuple _relayData)',
        'label': 'Relay'
    },
    '0xc7c7f5b3': {
        'function': 'send(tuple _sendParam,tuple _fee,address _refundAddress)',
        'label': 'USDT0'
    }
}