const path = require("path");
const { execSync } = require("child_process");

console.log("Running deployment script via Hardhat...");
try {
  const contractsDir = path.join(__dirname, "../contracts");
  execSync("npx hardhat run scripts/deploy.js --network amoy", {
    cwd: contractsDir,
    stdio: "inherit",
  });
} catch (error) {
  console.error("Deployment failed:", error.message);
  process.exit(1);
}
