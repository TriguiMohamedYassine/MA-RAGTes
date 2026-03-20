// SPDX-License-Identifier: MIT
    pragma solidity ^0.8.13;

    contract MetaCoin {
        mapping (address => uint) balances;

        event Transfer(address indexed _from, address indexed _to, uint256 _value);

        constructor() {
            balances[msg.sender] = 10000;
        }

        function sendCoin(address receiver, uint amount) public returns(bool sufficient) {
            require(balances[msg.sender] >= amount, "Solde insuffisant");
            balances[msg.sender] -= amount;
            balances[receiver] += amount;
            emit Transfer(msg.sender, receiver, amount);
            return true;
        }

        // CORRECTION ICI : On retire le '* 2'
        // La fonction renvoie maintenant la valeur exacte.
        function getBalanceInEth(address addr) public view returns(uint){
            return getBalance(addr); 
        }

        function getBalance(address addr) public view returns(uint) {
            return balances[addr];
        }
    }