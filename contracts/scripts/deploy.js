const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  const EvidenceRegistry = await hre.ethers.getContractFactory("EvidenceRegistry");
  console.log("Deploying EvidenceRegistry to Polygon Amoy...");
  const registry = await EvidenceRegistry.deploy();
  await registry.waitForDeployment();
  const contractAddress = await registry.getAddress();

  console.log("\n==================================================");
  console.log(`EvidenceRegistry deployed successfully!`);
  console.log(`Contract Address: ${contractAddress}`);
  console.log(`PolygonScan Link: https://amoy.polygonscan.com/address/${contractAddress}`);
  console.log("==================================================\n");

  // Save contract ABI to contracts/EvidenceRegistry.abi.json
  const artifactPath = path.join(__dirname, "../artifacts/EvidenceRegistry.sol/EvidenceRegistry.json");
  if (fs.existsSync(artifactPath)) {
    const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
    const abiPath = path.join(__dirname, "../EvidenceRegistry.abi.json");
    fs.writeFileSync(abiPath, JSON.stringify(artifact.abi, null, 2));
    console.log(`Saved contract ABI to ${abiPath}`);
  }

  // Update CONTRACT_ADDRESS in .env if present
  const envPath = path.join(__dirname, "../../.env");
  if (fs.existsSync(envPath)) {
    let envContent = fs.readFileSync(envPath, "utf8");
    if (envContent.includes("CONTRACT_ADDRESS=")) {
      envContent = envContent.replace(/CONTRACT_ADDRESS=.*/, `CONTRACT_ADDRESS=${contractAddress}`);
    } else {
      envContent += `\nCONTRACT_ADDRESS=${contractAddress}\n`;
    }
    fs.writeFileSync(envPath, envContent);
    console.log(`Updated CONTRACT_ADDRESS in .env to ${contractAddress}`);
  }


}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

