// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC721 {
    function transferFrom(address from, address to, uint256 tokenId) external;
    function ownerOf(uint256 tokenId) external view returns (address);
    function isApprovedForAll(address owner, address operator) external view returns (bool);
    function getApproved(uint256 tokenId) external view returns (address);
}

interface IERC2981 {
    function royaltyInfo(uint256 tokenId, uint256 salePrice)
        external view returns (address receiver, uint256 amount);
}

interface IERC165 {
    function supportsInterface(bytes4 interfaceId) external view returns (bool);
}

contract NFTMarketplace {
    bytes4 private constant INTERFACE_ID_ERC2981 = 0x2a55205a;
    uint256 public constant MAX_ROYALTY = 1000; // 10%
    uint256 public constant BPS = 10000;

    address public owner;
    uint256 public platformFee = 250; // 2.5%
    uint256 public accumulatedFees;
    bool private _locked;

    struct Listing {
        address seller;
        address nftContract;
        uint256 tokenId;
        uint256 price;
        uint256 expiry;
        bool active;
    }

    struct Bid {
        address bidder;
        uint256 amount;
        uint256 expiry;
        bool active;
    }

    uint256 public listingCount;
    mapping(uint256 => Listing) public listings;
    mapping(uint256 => Bid) public highestBids;
    mapping(address => uint256) public pendingWithdrawals;
    mapping(address => mapping(uint256 => uint256)) public tokenToListing;

    event Listed(uint256 indexed listingId, address indexed seller, address nftContract, uint256 tokenId, uint256 price);
    event Sold(uint256 indexed listingId, address indexed buyer, uint256 price);
    event BidPlaced(uint256 indexed listingId, address indexed bidder, uint256 amount);
    event BidAccepted(uint256 indexed listingId, address indexed bidder, uint256 amount);
    event ListingCancelled(uint256 indexed listingId);
    event BidCancelled(uint256 indexed listingId, address indexed bidder);
    event PriceUpdated(uint256 indexed listingId, uint256 newPrice);

    modifier onlyOwner() { require(msg.sender == owner, "Not owner"); _; }
    modifier noReentrant() { require(!_locked, "Reentrant"); _locked = true; _; _locked = false; }

    constructor() { owner = msg.sender; }

    function list(
        address nftContract,
        uint256 tokenId,
        uint256 price,
        uint256 duration
    ) external returns (uint256) {
        require(price > 0, "Zero price");
        require(duration > 0, "Zero duration");
        IERC721 nft = IERC721(nftContract);
        require(nft.ownerOf(tokenId) == msg.sender, "Not owner");
        require(
            nft.isApprovedForAll(msg.sender, address(this)) ||
            nft.getApproved(tokenId) == address(this),
            "Not approved"
        );
        uint256 id = ++listingCount;
        listings[id] = Listing({
            seller: msg.sender,
            nftContract: nftContract,
            tokenId: tokenId,
            price: price,
            expiry: block.timestamp + duration,
            active: true
        });
        tokenToListing[nftContract][tokenId] = id;
        emit Listed(id, msg.sender, nftContract, tokenId, price);
        return id;
    }

    function buy(uint256 listingId) external payable noReentrant {
        Listing storage l = listings[listingId];
        require(l.active, "Not active");
        require(block.timestamp <= l.expiry, "Expired");
        require(msg.value >= l.price, "Underpaid");
        l.active = false;
        uint256 excess = msg.value - l.price;
        (uint256 royaltyAmount, address royaltyRecipient) = _getRoyalty(l.nftContract, l.tokenId, l.price);
        uint256 fee = (l.price * platformFee) / BPS;
        uint256 sellerProceeds = l.price - fee - royaltyAmount;
        accumulatedFees += fee;
        if (royaltyAmount > 0) pendingWithdrawals[royaltyRecipient] += royaltyAmount;
        pendingWithdrawals[l.seller] += sellerProceeds;
        if (excess > 0) pendingWithdrawals[msg.sender] += excess;
        IERC721(l.nftContract).transferFrom(l.seller, msg.sender, l.tokenId);
        _refundOutbidBidder(listingId);
        emit Sold(listingId, msg.sender, l.price);
    }

    function placeBid(uint256 listingId, uint256 duration) external payable noReentrant {
        Listing storage l = listings[listingId];
        require(l.active, "Not active");
        require(block.timestamp <= l.expiry, "Listing expired");
        require(msg.value > 0, "Zero bid");
        Bid storage current = highestBids[listingId];
        require(msg.value > current.amount, "Bid too low");
        if (current.active && current.amount > 0) {
            pendingWithdrawals[current.bidder] += current.amount;
        }
        highestBids[listingId] = Bid({
            bidder: msg.sender,
            amount: msg.value,
            expiry: block.timestamp + duration,
            active: true
        });
        emit BidPlaced(listingId, msg.sender, msg.value);
    }

    function acceptBid(uint256 listingId) external noReentrant {
        Listing storage l = listings[listingId];
        require(l.active, "Not active");
        require(l.seller == msg.sender, "Not seller");
        Bid storage b = highestBids[listingId];
        require(b.active && b.amount > 0, "No bid");
        require(block.timestamp <= b.expiry, "Bid expired");
        l.active = false;
        b.active = false;
        (uint256 royaltyAmount, address royaltyRecipient) = _getRoyalty(l.nftContract, l.tokenId, b.amount);
        uint256 fee = (b.amount * platformFee) / BPS;
        uint256 sellerProceeds = b.amount - fee - royaltyAmount;
        accumulatedFees += fee;
        if (royaltyAmount > 0) pendingWithdrawals[royaltyRecipient] += royaltyAmount;
        pendingWithdrawals[l.seller] += sellerProceeds;
        IERC721(l.nftContract).transferFrom(l.seller, b.bidder, l.tokenId);
        emit BidAccepted(listingId, b.bidder, b.amount);
    }

    function cancelListing(uint256 listingId) external noReentrant {
        Listing storage l = listings[listingId];
        require(l.active, "Not active");
        require(l.seller == msg.sender || block.timestamp > l.expiry, "Not authorized");
        l.active = false;
        _refundOutbidBidder(listingId);
        emit ListingCancelled(listingId);
    }

    function cancelBid(uint256 listingId) external noReentrant {
        Bid storage b = highestBids[listingId];
        require(b.active && b.bidder == msg.sender, "No bid");
        b.active = false;
        (bool ok,) = msg.sender.call{value: b.amount}("");
        require(ok, "Refund failed");
        emit BidCancelled(listingId, msg.sender);
    }

    function updatePrice(uint256 listingId, uint256 newPrice) external {
        Listing storage l = listings[listingId];
        require(l.active && l.seller == msg.sender, "Not authorized");
        require(newPrice > 0, "Zero price");
        l.price = newPrice;
        emit PriceUpdated(listingId, newPrice);
    }

    function withdraw() external noReentrant {
        uint256 amount = pendingWithdrawals[msg.sender];
        require(amount > 0, "Nothing to withdraw");
        pendingWithdrawals[msg.sender] = 0;
        (bool ok,) = msg.sender.call{value: amount}("");
        require(ok, "Transfer failed");
    }

    function _refundOutbidBidder(uint256 listingId) internal {
        Bid storage b = highestBids[listingId];
        if (b.active && b.amount > 0) {
            b.active = false;
            pendingWithdrawals[b.bidder] += b.amount;
        }
    }

    function _getRoyalty(address nftContract, uint256 tokenId, uint256 price)
        internal view returns (uint256 amount, address recipient)
    {
        try IERC165(nftContract).supportsInterface(INTERFACE_ID_ERC2981) returns (bool supported) {
            if (supported) {
                try IERC2981(nftContract).royaltyInfo(tokenId, price) returns (address r, uint256 a) {
                    if (a <= (price * MAX_ROYALTY) / BPS) return (a, r);
                    return ((price * MAX_ROYALTY) / BPS, r);
                } catch {}
            }
        } catch {}
        return (0, address(0));
    }

    function withdrawFees() external onlyOwner noReentrant {
        uint256 f = accumulatedFees; accumulatedFees = 0;
        (bool ok,) = owner.call{value: f}(""); require(ok, "Failed");
    }
    function setPlatformFee(uint256 fee) external onlyOwner { require(fee <= 500, "Max 5%"); platformFee = fee; }
}