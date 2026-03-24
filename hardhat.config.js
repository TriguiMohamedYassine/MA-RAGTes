require("@nomicfoundation/hardhat-toolbox");
require("solidity-coverage");

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: "0.8.24",
  paths: {
    sources: process.env.HARDHAT_SOURCES_PATH || "./contracts",
  },
  mocha: {
    reporter: "mochawesome",
    reporterOptions: {
      reportDir: "mochawesome-report",
      reportFilename: "mochawesome",
      quiet: true,
      json: true,
      html: false,
    },
  },
};
