// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract EvidenceRegistry {
    struct Evidence {
        bytes32 evidenceHash;
        string  cid;
        uint256 timestamp;
        address submitter;
    }

    mapping(bytes32 => Evidence) public records;

    event EvidenceRegistered(
        bytes32 indexed evidenceHash,
        string cid,
        uint256 timestamp,
        address indexed submitter
    );

    function registerEvidence(bytes32 evidenceHash, string calldata cid) external {
        require(records[evidenceHash].timestamp == 0, "Already registered");
        records[evidenceHash] = Evidence(evidenceHash, cid, block.timestamp, msg.sender);
        emit EvidenceRegistered(evidenceHash, cid, block.timestamp, msg.sender);
    }

    function verifyEvidence(bytes32 evidenceHash)
        external
        view
        returns (bool exists, string memory cid, uint256 timestamp, address submitter)
    {
        Evidence memory e = records[evidenceHash];
        return (e.timestamp != 0, e.cid, e.timestamp, e.submitter);
    }
}

