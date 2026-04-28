// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title USDCShieldDelegate
 * @author Manus AI
 * @notice Contratto delegate EIP-7702 per proteggere USDC su un EOA esistente.
 *         Implementa Spending Limits giornalieri, Whitelist destinatari con timelock,
 *         e Vault con timelock per prelievi superiori al limite.
 *
 * @dev Questo contratto è progettato per essere usato come delegation target
 *      tramite EIP-7702 (transaction type 4). Lo storage è ancorato tramite
 *      ERC-7201 per evitare collisioni con altre deleghe.
 *
 *      IMPORTANTE: La chiave privata dell'EOA mantiene sempre il pieno controllo.
 *      Questo contratto protegge solo le transazioni che passano attraverso
 *      le sue funzioni (via executeFromSelf o bundler ERC-4337).
 */

// ============================================================================
// Interfacce minimali
// ============================================================================

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
}

interface IEntryPoint {
    function getNonce(address sender, uint192 key) external view returns (uint256);
}

// ============================================================================
// Contratto principale
// ============================================================================

contract USDCShieldDelegate {

    // ========================================================================
    // ERC-7201: Namespace storage per evitare collisioni
    // keccak256(abi.encode(uint256(keccak256("usdc.shield.delegate.v1")) - 1)) & ~bytes32(uint256(0xff))
    // ========================================================================
    bytes32 private constant STORAGE_SLOT =
        0x8a0c9d8ec1d9f8b4162010f4d10fb8f720e39f4775a5f2e8d9d0c0b3a1e2f300;

    // ========================================================================
    // Costanti
    // ========================================================================

    /// @notice Indirizzo USDC su Ethereum Mainnet
    address public constant USDC = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48;

    /// @notice EntryPoint v0.7 canonico ERC-4337
    address public constant ENTRY_POINT = 0x0000000071727De22E5E9d8BAf0edAc6f37da032;

    // ========================================================================
    // Struct per lo storage ERC-7201
    // ========================================================================

    struct WithdrawalRequest {
        address to;
        uint256 amount;
        uint256 executeAfter;   // timestamp dopo il quale si può eseguire
        bool executed;
        bool cancelled;
    }

    struct PendingRecipient {
        bool adding;            // true = aggiunta, false = rimozione
        uint256 executeAfter;   // timestamp dopo il quale si può confermare
        bool executed;
    }

    struct ShieldStorage {
        // Stato di inizializzazione
        bool initialized;
        
        // Owner (l'EOA che ha delegato)
        address owner;
        
        // Guardiani per emergenze
        address[] guardians;
        uint256 guardianThreshold;
        mapping(address => bool) isGuardian;
        
        // Spending limits
        uint256 dailyLimit;         // Limite giornaliero in unità USDC (6 decimali)
        uint256 epochDuration;      // Durata epoca (default 1 day)
        uint256 currentEpochStart;  // Inizio epoca corrente
        uint256 spentThisEpoch;     // Speso nell'epoca corrente
        
        // Timelock
        uint256 timelockDuration;   // Durata timelock per prelievi cold
        
        // Whitelist destinatari
        mapping(address => bool) whitelistedRecipients;
        
        // Pending recipient changes (con timelock)
        uint256 pendingRecipientCount;
        mapping(uint256 => address) pendingRecipientAddress;
        mapping(uint256 => PendingRecipient) pendingRecipients;
        
        // Whitelist DeFi (contratti approvati)
        mapping(address => bool) whitelistedContracts;
        
        // Withdrawal requests (cold vault)
        uint256 withdrawalCount;
        mapping(uint256 => WithdrawalRequest) withdrawals;
        
        // Pausa di emergenza
        bool paused;
        uint256 pauseExpiry;
        
        // Pending limit changes (con timelock)
        uint256 pendingNewLimit;
        uint256 pendingLimitExecuteAfter;
        bool hasPendingLimitChange;
    }

    // ========================================================================
    // Eventi
    // ========================================================================

    event Initialized(address indexed owner, uint256 dailyLimit, uint256 timelockDuration);
    event HotSpend(address indexed to, uint256 amount, uint256 remainingBudget);
    event WithdrawalRequested(uint256 indexed requestId, address indexed to, uint256 amount, uint256 executeAfter);
    event WithdrawalExecuted(uint256 indexed requestId, address indexed to, uint256 amount);
    event WithdrawalCancelled(uint256 indexed requestId, address indexed cancelledBy);
    event RecipientChangeRequested(uint256 indexed changeId, address indexed recipient, bool adding, uint256 executeAfter);
    event RecipientChangeExecuted(uint256 indexed changeId, address indexed recipient, bool added);
    event RecipientRemoved(address indexed recipient);
    event ContractWhitelisted(address indexed contractAddr, bool status);
    event Paused(address indexed by, uint256 expiry);
    event Unpaused(address indexed by);
    event LimitChangeRequested(uint256 newLimit, uint256 executeAfter);
    event LimitChangeExecuted(uint256 oldLimit, uint256 newLimit);
    event LimitDecreased(uint256 oldLimit, uint256 newLimit);
    event GuardianAdded(address indexed guardian);
    event GuardianRemoved(address indexed guardian);

    // ========================================================================
    // Errori
    // ========================================================================

    error AlreadyInitialized();
    error NotOwner();
    error NotOwnerOrGuardian();
    error NotGuardian();
    error ContractPaused();
    error RecipientNotWhitelisted();
    error ExceedsDailyLimit();
    error TimelockNotExpired();
    error WithdrawalAlreadyProcessed();
    error InvalidRequest();
    error TransferFailed();
    error ZeroAddress();
    error InvalidThreshold();
    error InsufficientBalance();
    error NoPendingChange();

    // ========================================================================
    // Modificatori
    // ========================================================================

    modifier onlyOwner() {
        ShieldStorage storage s = _getStorage();
        if (msg.sender != s.owner && msg.sender != address(this)) revert NotOwner();
        _;
    }

    modifier onlyOwnerOrGuardian() {
        ShieldStorage storage s = _getStorage();
        if (msg.sender != s.owner && msg.sender != address(this) && !s.isGuardian[msg.sender]) {
            revert NotOwnerOrGuardian();
        }
        _;
    }

    modifier onlyGuardian() {
        ShieldStorage storage s = _getStorage();
        if (!s.isGuardian[msg.sender]) revert NotGuardian();
        _;
    }

    modifier whenNotPaused() {
        ShieldStorage storage s = _getStorage();
        if (s.paused && block.timestamp < s.pauseExpiry) revert ContractPaused();
        // Auto-unpause se il tempo è scaduto
        if (s.paused && block.timestamp >= s.pauseExpiry) {
            s.paused = false;
        }
        _;
    }

    // ========================================================================
    // Inizializzazione
    // ========================================================================

    /**
     * @notice Inizializza il contratto delegate. Deve essere chiamata una sola volta
     *         dopo la delegation EIP-7702.
     * @param _owner L'indirizzo dell'EOA proprietario (il tuo wallet OKX)
     * @param _dailyLimit Limite giornaliero in USDC (6 decimali, es. 500e6 = 500 USDC)
     * @param _timelockDuration Durata del timelock in secondi (es. 3 days = 259200)
     * @param _guardians Array di indirizzi guardiani
     * @param _guardianThreshold Numero minimo di guardiani per bypass
     */
    function initialize(
        address _owner,
        uint256 _dailyLimit,
        uint256 _timelockDuration,
        address[] calldata _guardians,
        uint256 _guardianThreshold
    ) external {
        ShieldStorage storage s = _getStorage();
        if (s.initialized) revert AlreadyInitialized();
        if (_owner == address(0)) revert ZeroAddress();
        if (_guardianThreshold > _guardians.length) revert InvalidThreshold();

        s.initialized = true;
        s.owner = _owner;
        s.dailyLimit = _dailyLimit;
        s.epochDuration = 1 days;
        s.currentEpochStart = block.timestamp;
        s.timelockDuration = _timelockDuration;
        s.guardianThreshold = _guardianThreshold;

        for (uint256 i = 0; i < _guardians.length; i++) {
            if (_guardians[i] == address(0)) revert ZeroAddress();
            s.guardians.push(_guardians[i]);
            s.isGuardian[_guardians[i]] = true;
            emit GuardianAdded(_guardians[i]);
        }

        emit Initialized(_owner, _dailyLimit, _timelockDuration);
    }

    // ========================================================================
    // HOT SPEND: Spesa giornaliera entro il limite
    // ========================================================================

    /**
     * @notice Invia USDC a un destinatario in whitelist, entro il limite giornaliero.
     * @param _to Indirizzo destinatario (deve essere in whitelist)
     * @param _amount Importo in USDC (6 decimali)
     */
    function hotSpend(address _to, uint256 _amount) external onlyOwner whenNotPaused {
        ShieldStorage storage s = _getStorage();
        if (!s.whitelistedRecipients[_to]) revert RecipientNotWhitelisted();

        _resetEpochIfNeeded(s);

        if (s.spentThisEpoch + _amount > s.dailyLimit) revert ExceedsDailyLimit();

        s.spentThisEpoch += _amount;

        bool success = IERC20(USDC).transfer(_to, _amount);
        if (!success) revert TransferFailed();

        emit HotSpend(_to, _amount, s.dailyLimit - s.spentThisEpoch);
    }

    // ========================================================================
    // COLD VAULT: Prelievi con timelock
    // ========================================================================

    /**
     * @notice Richiede un prelievo dal cold vault. Sarà eseguibile dopo il timelock.
     * @param _to Indirizzo destinatario
     * @param _amount Importo in USDC (6 decimali)
     * @return requestId L'ID della richiesta di prelievo
     */
    function requestWithdrawal(address _to, uint256 _amount) 
        external 
        onlyOwner 
        whenNotPaused 
        returns (uint256 requestId) 
    {
        ShieldStorage storage s = _getStorage();
        if (_to == address(0)) revert ZeroAddress();
        if (_amount == 0) revert InvalidRequest();

        requestId = s.withdrawalCount++;
        uint256 executeAfter = block.timestamp + s.timelockDuration;

        s.withdrawals[requestId] = WithdrawalRequest({
            to: _to,
            amount: _amount,
            executeAfter: executeAfter,
            executed: false,
            cancelled: false
        });

        emit WithdrawalRequested(requestId, _to, _amount, executeAfter);
    }

    /**
     * @notice Esegue un prelievo dopo che il timelock è scaduto.
     * @param _requestId L'ID della richiesta di prelievo
     */
    function executeWithdrawal(uint256 _requestId) external onlyOwner whenNotPaused {
        ShieldStorage storage s = _getStorage();
        WithdrawalRequest storage req = s.withdrawals[_requestId];

        if (req.executed || req.cancelled) revert WithdrawalAlreadyProcessed();
        if (req.amount == 0) revert InvalidRequest();
        if (block.timestamp < req.executeAfter) revert TimelockNotExpired();

        req.executed = true;

        bool success = IERC20(USDC).transfer(req.to, req.amount);
        if (!success) revert TransferFailed();

        emit WithdrawalExecuted(_requestId, req.to, req.amount);
    }

    /**
     * @notice Cancella un prelievo pendente. Può essere chiamata dal proprietario o da un guardiano.
     * @param _requestId L'ID della richiesta di prelievo
     */
    function cancelWithdrawal(uint256 _requestId) external onlyOwnerOrGuardian {
        ShieldStorage storage s = _getStorage();
        WithdrawalRequest storage req = s.withdrawals[_requestId];

        if (req.executed || req.cancelled) revert WithdrawalAlreadyProcessed();
        if (req.amount == 0) revert InvalidRequest();

        req.cancelled = true;

        emit WithdrawalCancelled(_requestId, msg.sender);
    }

    // ========================================================================
    // WHITELIST DESTINATARI: Con timelock per aggiunte
    // ========================================================================

    /**
     * @notice Richiede l'aggiunta di un destinatario alla whitelist. Richiede timelock.
     * @param _recipient Indirizzo da aggiungere
     * @return changeId L'ID della richiesta di modifica
     */
    function requestAddRecipient(address _recipient) 
        external 
        onlyOwner 
        returns (uint256 changeId) 
    {
        ShieldStorage storage s = _getStorage();
        if (_recipient == address(0)) revert ZeroAddress();

        changeId = s.pendingRecipientCount++;
        uint256 executeAfter = block.timestamp + s.timelockDuration;

        s.pendingRecipientAddress[changeId] = _recipient;
        s.pendingRecipients[changeId] = PendingRecipient({
            adding: true,
            executeAfter: executeAfter,
            executed: false
        });

        emit RecipientChangeRequested(changeId, _recipient, true, executeAfter);
    }

    /**
     * @notice Conferma l'aggiunta di un destinatario dopo il timelock.
     * @param _changeId L'ID della richiesta di modifica
     */
    function executeAddRecipient(uint256 _changeId) external onlyOwner {
        ShieldStorage storage s = _getStorage();
        PendingRecipient storage pending = s.pendingRecipients[_changeId];

        if (pending.executed) revert WithdrawalAlreadyProcessed();
        if (block.timestamp < pending.executeAfter) revert TimelockNotExpired();

        pending.executed = true;
        address recipient = s.pendingRecipientAddress[_changeId];
        s.whitelistedRecipients[recipient] = true;

        emit RecipientChangeExecuted(_changeId, recipient, true);
    }

    /**
     * @notice Rimuove immediatamente un destinatario dalla whitelist.
     *         La rimozione è immediata per sicurezza (riduce la superficie di attacco).
     * @param _recipient Indirizzo da rimuovere
     */
    function removeRecipient(address _recipient) external onlyOwner {
        ShieldStorage storage s = _getStorage();
        s.whitelistedRecipients[_recipient] = false;
        emit RecipientRemoved(_recipient);
    }

    // ========================================================================
    // WHITELIST CONTRATTI DeFi
    // ========================================================================

    /**
     * @notice Aggiunge o rimuove un contratto dalla whitelist DeFi.
     *         Permette interazioni con protocolli approvati (es. Uniswap).
     * @param _contract Indirizzo del contratto
     * @param _status true per aggiungere, false per rimuovere
     */
    function setWhitelistedContract(address _contract, bool _status) external onlyOwner {
        ShieldStorage storage s = _getStorage();
        s.whitelistedContracts[_contract] = _status;
        emit ContractWhitelisted(_contract, _status);
    }

    /**
     * @notice Esegue una chiamata a un contratto DeFi in whitelist.
     * @param _target Indirizzo del contratto target
     * @param _data Calldata della funzione da chiamare
     */
    function executeDeFiCall(address _target, bytes calldata _data) 
        external 
        onlyOwner 
        whenNotPaused 
        returns (bytes memory) 
    {
        ShieldStorage storage s = _getStorage();
        if (!s.whitelistedContracts[_target]) revert RecipientNotWhitelisted();

        (bool success, bytes memory result) = _target.call(_data);
        require(success, "DeFi call failed");
        return result;
    }

    // ========================================================================
    // SPENDING LIMIT: Gestione limiti
    // ========================================================================

    /**
     * @notice Richiede un aumento del limite giornaliero. Richiede timelock.
     * @param _newLimit Nuovo limite in USDC (6 decimali)
     */
    function requestLimitIncrease(uint256 _newLimit) external onlyOwner {
        ShieldStorage storage s = _getStorage();
        require(_newLimit > s.dailyLimit, "Use decreaseLimit for lower values");

        s.pendingNewLimit = _newLimit;
        s.pendingLimitExecuteAfter = block.timestamp + s.timelockDuration;
        s.hasPendingLimitChange = true;

        emit LimitChangeRequested(_newLimit, s.pendingLimitExecuteAfter);
    }

    /**
     * @notice Esegue l'aumento del limite dopo il timelock.
     */
    function executeLimitIncrease() external onlyOwner {
        ShieldStorage storage s = _getStorage();
        if (!s.hasPendingLimitChange) revert NoPendingChange();
        if (block.timestamp < s.pendingLimitExecuteAfter) revert TimelockNotExpired();

        uint256 oldLimit = s.dailyLimit;
        s.dailyLimit = s.pendingNewLimit;
        s.hasPendingLimitChange = false;

        emit LimitChangeExecuted(oldLimit, s.pendingNewLimit);
    }

    /**
     * @notice Diminuisce immediatamente il limite giornaliero.
     *         La diminuzione è immediata per sicurezza.
     * @param _newLimit Nuovo limite (deve essere inferiore all'attuale)
     */
    function decreaseLimit(uint256 _newLimit) external onlyOwner {
        ShieldStorage storage s = _getStorage();
        require(_newLimit < s.dailyLimit, "New limit must be lower");
        uint256 oldLimit = s.dailyLimit;
        s.dailyLimit = _newLimit;
        emit LimitDecreased(oldLimit, _newLimit);
    }

    // ========================================================================
    // PAUSA DI EMERGENZA
    // ========================================================================

    /**
     * @notice Mette in pausa il contratto per 24 ore. Può essere chiamata da un guardiano.
     */
    function emergencyPause() external onlyOwnerOrGuardian {
        ShieldStorage storage s = _getStorage();
        s.paused = true;
        s.pauseExpiry = block.timestamp + 24 hours;
        emit Paused(msg.sender, s.pauseExpiry);
    }

    /**
     * @notice Rimuove la pausa. Solo il proprietario può farlo.
     */
    function unpause() external onlyOwner {
        ShieldStorage storage s = _getStorage();
        s.paused = false;
        emit Unpaused(msg.sender);
    }

    // ========================================================================
    // BATCH EXECUTION (ERC-7821 inspired)
    // ========================================================================

    struct Call {
        address target;
        uint256 value;
        bytes data;
    }

    /**
     * @notice Esegue un batch di chiamate. Utile per operazioni atomiche.
     * @param calls Array di chiamate da eseguire
     */
    function executeBatch(Call[] calldata calls) external onlyOwner whenNotPaused {
        for (uint256 i = 0; i < calls.length; i++) {
            (bool success, bytes memory result) = calls[i].target.call{value: calls[i].value}(calls[i].data);
            if (!success) {
                // Bubble up revert reason
                assembly {
                    revert(add(result, 32), mload(result))
                }
            }
        }
    }

    // ========================================================================
    // GUARDIAN MANAGEMENT
    // ========================================================================

    /**
     * @notice Aggiunge un guardiano.
     * @param _guardian Indirizzo del nuovo guardiano
     */
    function addGuardian(address _guardian) external onlyOwner {
        ShieldStorage storage s = _getStorage();
        if (_guardian == address(0)) revert ZeroAddress();
        require(!s.isGuardian[_guardian], "Already guardian");
        
        s.guardians.push(_guardian);
        s.isGuardian[_guardian] = true;
        emit GuardianAdded(_guardian);
    }

    /**
     * @notice Rimuove un guardiano.
     * @param _guardian Indirizzo del guardiano da rimuovere
     */
    function removeGuardian(address _guardian) external onlyOwner {
        ShieldStorage storage s = _getStorage();
        require(s.isGuardian[_guardian], "Not a guardian");
        
        s.isGuardian[_guardian] = false;
        
        // Rimuovi dall'array
        for (uint256 i = 0; i < s.guardians.length; i++) {
            if (s.guardians[i] == _guardian) {
                s.guardians[i] = s.guardians[s.guardians.length - 1];
                s.guardians.pop();
                break;
            }
        }
        emit GuardianRemoved(_guardian);
    }

    // ========================================================================
    // VIEW FUNCTIONS
    // ========================================================================

    function getOwner() external view returns (address) {
        return _getStorage().owner;
    }

    function getDailyLimit() external view returns (uint256) {
        return _getStorage().dailyLimit;
    }

    function getSpentThisEpoch() external view returns (uint256) {
        ShieldStorage storage s = _getStorage();
        if (block.timestamp >= s.currentEpochStart + s.epochDuration) {
            return 0; // Epoca resettata
        }
        return s.spentThisEpoch;
    }

    function getRemainingBudget() external view returns (uint256) {
        ShieldStorage storage s = _getStorage();
        uint256 spent = s.spentThisEpoch;
        if (block.timestamp >= s.currentEpochStart + s.epochDuration) {
            spent = 0;
        }
        return s.dailyLimit > spent ? s.dailyLimit - spent : 0;
    }

    function getTimelockDuration() external view returns (uint256) {
        return _getStorage().timelockDuration;
    }

    function isWhitelistedRecipient(address _recipient) external view returns (bool) {
        return _getStorage().whitelistedRecipients[_recipient];
    }

    function isWhitelistedContract(address _contract) external view returns (bool) {
        return _getStorage().whitelistedContracts[_contract];
    }

    function isPaused() external view returns (bool) {
        ShieldStorage storage s = _getStorage();
        return s.paused && block.timestamp < s.pauseExpiry;
    }

    function isInitialized() external view returns (bool) {
        return _getStorage().initialized;
    }

    function getWithdrawal(uint256 _requestId) external view returns (
        address to,
        uint256 amount,
        uint256 executeAfter,
        bool executed,
        bool cancelled
    ) {
        WithdrawalRequest storage req = _getStorage().withdrawals[_requestId];
        return (req.to, req.amount, req.executeAfter, req.executed, req.cancelled);
    }

    function getGuardians() external view returns (address[] memory) {
        return _getStorage().guardians;
    }

    function getGuardianThreshold() external view returns (uint256) {
        return _getStorage().guardianThreshold;
    }

    function getUSDCBalance() external view returns (uint256) {
        return IERC20(USDC).balanceOf(address(this));
    }

    // ========================================================================
    // RECEIVE ETH (per pagare gas)
    // ========================================================================

    receive() external payable {}

    // ========================================================================
    // Funzioni interne
    // ========================================================================

    function _resetEpochIfNeeded(ShieldStorage storage s) internal {
        if (block.timestamp >= s.currentEpochStart + s.epochDuration) {
            s.currentEpochStart = block.timestamp;
            s.spentThisEpoch = 0;
        }
    }

    function _getStorage() internal pure returns (ShieldStorage storage s) {
        bytes32 slot = STORAGE_SLOT;
        assembly {
            s.slot := slot
        }
    }
}
