# Web3 Infrastructure with SimpleInfra 🌐

## Why SimpleInfra for Web3?

Building Web3 infrastructure is **notoriously complex**:
- Setting up Ethereum nodes takes days
- IPFS configuration is confusing
- Smart contract deployment has 10+ steps
- No single tool handles everything

**SimpleInfra makes it trivial!**

## 🚀 Quick Start: Deploy Ethereum Node

```simpleinfra
server eth:
    host "your-server.com"
    user "ubuntu"

task "Deploy Ethereum" on eth:
    ethereum install client="geth"
    ethereum run type="full" network="mainnet"
    ethereum sync_status
```

Run it:
```bash
si run ethereum.si
```

**That's it!** You now have a full Ethereum node syncing.

---

## 📦 Web3 Modules

### 1. Ethereum Module

**Supported Clients:**
- Geth (Go Ethereum)
- Erigon (Most efficient)
- Nethermind (.NET)
- Besu (Java)

**Node Types:**
- `full` - Full node (recommended)
- `archive` - Archive node (all historical state)
- `light` - Light client (minimal storage)

**Example:**
```simpleinfra
task "Mainnet Archive Node" on server:
    ethereum install client="erigon"
    ethereum run:
        client: "erigon"
        type: "archive"
        network: "mainnet"
        data_dir: "/mnt/4tb/ethereum"

    # Check sync progress
    ethereum sync_status client="erigon"
```

**Other Networks:**
```simpleinfra
# Polygon
ethereum run type="full" network="polygon"

# Arbitrum
ethereum run type="full" network="arbitrum"

# Optimism
ethereum run type="full" network="optimism"

# Goerli testnet
ethereum run type="full" network="goerli"
```

---

### 2. IPFS Module

**Operations:**
- `install` - Install IPFS (Kubo)
- `init` - Initialize repository
- `run` - Run daemon
- `pin` - Pin content
- `publish` - Publish to IPNS

**Example:**
```simpleinfra
task "IPFS Node" on ipfs_server:
    ipfs install
    ipfs init profile="server"  # Optimized for servers
    ipfs run

    # Pin important content
    ipfs pin cid="QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG"

    # Publish to IPNS (mutable pointer)
    ipfs publish cid="QmXyz..."
```

**IPFS Profiles:**
- `server` - Default for servers
- `lowpower` - For Raspberry Pi
- `badgerds` - For large repos

---

### 3. Smart Contract Module

**Frameworks:**
- Foundry (Recommended - fast, written in Rust)
- Hardhat (JavaScript/TypeScript)

**Operations:**
- `install` - Install framework
- `compile` - Compile contracts
- `deploy` - Deploy to blockchain
- `verify` - Verify on Etherscan

**Example:**
```simpleinfra
secret private_key from vault "ethereum/deployer"
secret etherscan_key from env "ETHERSCAN_API_KEY"

task "Deploy NFT Contract" on local:
    # Install Foundry
    contract install framework="foundry"

    # Compile contracts
    contract compile:
        path: "./contracts"
        framework: "foundry"

    # Deploy
    contract deploy:
        contract: "src/MyNFT.sol:MyNFT"
        rpc_url: "https://mainnet.infura.io/v3/YOUR_KEY"
        private_key: secret private_key
        args: "'NFT Collection' 'NFT' 10000"

    # Verify on Etherscan
    contract verify:
        address: "0x..."
        contract: "MyNFT"
        etherscan_key: secret etherscan_key
```

---

### 4. Web3 Stack Module

**Pre-configured Stacks:**

#### `ethereum_full`
Full Ethereum node + IPFS + monitoring
```simpleinfra
task "Deploy Full Stack" on server:
    web3_stack deploy "ethereum_full"
```

Includes:
- Geth full node
- IPFS node
- Prometheus monitoring
- Grafana dashboards

#### `dapp_backend`
Complete dApp backend infrastructure
```simpleinfra
task "Deploy dApp" on server:
    web3_stack deploy "dapp_backend"
```

Includes:
- Ethereum node (Geth)
- IPFS storage
- The Graph indexing node
- PostgreSQL database
- Nginx reverse proxy

#### `nft_platform`
NFT platform infrastructure
```simpleinfra
task "Deploy NFT Platform" on server:
    web3_stack deploy "nft_platform"
```

Includes:
- Ethereum node
- IPFS for metadata storage
- PostgreSQL for off-chain data
- Redis for caching
- API server

---

## 🎯 Real-World Examples

### Example 1: Deploy Your Own NFT Marketplace

```simpleinfra
# servers.si
server eth:
    host "eth.yourproject.com"
    user "ubuntu"

server ipfs:
    host "ipfs.yourproject.com"
    user "ubuntu"

server api:
    host "api.yourproject.com"
    user "ubuntu"

# Secrets
secret db_password from vault "production/db"
secret eth_private_key from vault "production/deployer"

# Deploy Ethereum node
task "Setup Ethereum" on eth:
    ethereum install client="geth"
    ethereum run type="full" network="mainnet"
    ensure port 8545 is open

# Deploy IPFS for NFT storage
task "Setup IPFS" on ipfs:
    ipfs install
    ipfs init profile="server"
    ipfs run
    ensure port 5001 is open

# Deploy NFT contract
task "Deploy NFT Contract" on local:
    contract install framework="foundry"
    contract compile path="./contracts"
    contract deploy:
        contract: "src/NFTMarketplace.sol:NFTMarketplace"
        rpc_url: "http://eth.yourproject.com:8545"
        private_key: secret eth_private_key

# Deploy API server
task "Setup API" on api:
    install docker
    install docker-compose

    docker run:
        name: "nft-api"
        image: "yourimage/nft-api:latest"
        ports:
            3000: 3000
        env:
            ETH_RPC: "http://eth.yourproject.com:8545"
            IPFS_API: "http://ipfs.yourproject.com:5001"
            DB_PASSWORD: secret db_password

# Run everything
task "Deploy All" on local:
    run "si run servers.si --task 'Setup Ethereum'"
    run "si run servers.si --task 'Setup IPFS'"
    run "si run servers.si --task 'Deploy NFT Contract'"
    run "si run servers.si --task 'Setup API'"
```

### Example 2: DeFi Protocol Infrastructure

```simpleinfra
task "Deploy DeFi Stack" on defi_server:
    # Ethereum node for on-chain data
    ethereum install client="erigon"
    ethereum run type="archive" network="mainnet"

    # The Graph for indexing
    docker run:
        name: "graph-node"
        image: "graphprotocol/graph-node:latest"
        ports:
            8000: 8000
            8020: 8020
        env:
            postgres_host: "localhost"
            ethereum: "mainnet:http://localhost:8545"

    # Deploy price oracle contract
    contract deploy:
        contract: "src/PriceOracle.sol:PriceOracle"
        rpc_url: "http://localhost:8545"
        private_key: secret deployer_key

    # Deploy liquidity pool contract
    contract deploy:
        contract: "src/LiquidityPool.sol:LiquidityPool"
        rpc_url: "http://localhost:8545"
        private_key: secret deployer_key
```

### Example 3: Polygon Validator Node

```simpleinfra
task "Deploy Polygon Validator" on polygon_server:
    # Install dependencies
    install build-essential
    install git

    # Install Heimdall (Polygon consensus layer)
    git clone "https://github.com/maticnetwork/heimdall" to "/opt/heimdall"
    run "cd /opt/heimdall && make install"

    # Install Bor (Polygon execution layer)
    git clone "https://github.com/maticnetwork/bor" to "/opt/bor"
    run "cd /opt/bor && make bor"

    # Configure and start
    run "heimdalld init"
    run "bor init --datadir /var/lib/bor genesis.json"

    start service heimdalld
    start service bor

    # Setup monitoring
    install prometheus
    copy "polygon-prometheus.yml" to "/etc/prometheus/prometheus.yml"
    start service prometheus
```

### Example 4: IPFS Pinning Service

```simpleinfra
task "Deploy IPFS Cluster" on ipfs_cluster:
    # Install IPFS
    ipfs install
    ipfs init profile="server"

    # Install IPFS Cluster
    run "wget https://dist.ipfs.tech/ipfs-cluster-service/v1.0.5/ipfs-cluster-service_v1.0.5_linux-amd64.tar.gz"
    run "tar xvzf ipfs-cluster-service_v1.0.5_linux-amd64.tar.gz"
    run "mv ipfs-cluster-service/ipfs-cluster-service /usr/local/bin/"

    # Initialize cluster
    run "ipfs-cluster-service init"

    # Start services
    ipfs run
    run "ipfs-cluster-service daemon &"

    # Pin important content
    ipfs pin cid="QmYourContent..."
```

---

## 🔐 Security Best Practices

### 1. Use Vault for Secrets

```simpleinfra
# NEVER hardcode private keys!
secret eth_private_key from vault "ethereum/mainnet/deployer"
secret infura_key from vault "infura/api_key"
secret etherscan_key from vault "etherscan/api_key"

task "Deploy Securely" on local:
    contract deploy:
        private_key: secret eth_private_key  # Vault-backed
        rpc_url: "https://mainnet.infura.io/v3/{infura_key}"
```

### 2. Enable Firewall

```simpleinfra
task "Secure Node" on eth_node:
    # Only allow specific ports
    ensure port 8545 is closed  # RPC (internal only)
    ensure port 30303 is open   # P2P (public)

    # Use SSH tunnel for RPC access
    run "ufw allow 22"
    run "ufw enable"
```

### 3. Use HTTPS for RPC

```simpleinfra
task "Setup Nginx Proxy" on eth_node:
    install nginx
    install certbot

    template "nginx-eth-rpc.conf" to "/etc/nginx/sites-enabled/eth-rpc"

    # Get SSL certificate
    run "certbot --nginx -d rpc.yourdomain.com"

    restart service nginx
```

---

## 📊 Monitoring Your Web3 Infrastructure

```simpleinfra
task "Setup Monitoring" on eth_node:
    # Install Prometheus
    install prometheus

    # Configure to scrape Geth metrics
    template "prometheus-geth.yml" to "/etc/prometheus/prometheus.yml"

    start service prometheus

    # Install Grafana
    install grafana

    # Import pre-built Ethereum dashboard
    run "grafana-cli plugins install grafana-ethereum-datasource"
    copy "dashboards/ethereum.json" to "/var/lib/grafana/dashboards/"

    start service grafana-server

    # Setup alerts
    template "alerts.yml" to "/etc/prometheus/alerts.yml"
    restart service prometheus
```

---

## 💰 Cost Comparison

### Running Your Own Node vs. Infura/Alchemy

| Resource | Self-Hosted | Infura (100K req/day) | Annual Savings |
|----------|-------------|----------------------|----------------|
| Server | $50/month | $225/month | **$2,100** |
| Storage | Included | Included | $0 |
| Bandwidth | Included | Pay per request | **$1,000+** |
| **Total** | **$600/year** | **$2,700/year** | **$2,100/year** |

**SimpleInfra makes self-hosting trivial!**

---

## 🎓 Learning Path

1. **Start Simple:** Deploy a testnet node
   ```bash
   si run examples/ethereum_testnet.si
   ```

2. **Add IPFS:** Set up decentralized storage
   ```bash
   si run examples/ipfs_node.si
   ```

3. **Deploy Contracts:** Use Foundry to deploy
   ```bash
   si run examples/contract_deploy.si
   ```

4. **Full Stack:** Deploy complete dApp infrastructure
   ```bash
   si run examples/web3_complete.si
   ```

---

## 🚀 Production Checklist

- [ ] Use vault for all secrets
- [ ] Enable firewall (only necessary ports)
- [ ] Set up SSL/TLS for RPC endpoints
- [ ] Configure backup strategy for blockchain data
- [ ] Enable monitoring (Prometheus + Grafana)
- [ ] Set up alerting (PagerDuty, Slack)
- [ ] Document recovery procedures
- [ ] Test disaster recovery
- [ ] Enable audit logging
- [ ] Regular security updates

---

## 📚 Additional Resources

- **Ethereum Node Guide:** https://ethereum.org/en/developers/docs/nodes-and-clients/
- **IPFS Documentation:** https://docs.ipfs.tech/
- **Foundry Book:** https://book.getfoundry.sh/
- **The Graph Docs:** https://thegraph.com/docs/
- **Polygon Validators:** https://wiki.polygon.technology/

---

## 🎯 Summary

With SimpleInfra, you can:

✅ Deploy Ethereum nodes in **2 lines of code**
✅ Set up IPFS storage in **3 lines**
✅ Deploy smart contracts in **5 lines**
✅ Launch complete Web3 infrastructure in **minutes**

**No more weeks of configuration!**

Compare to traditional approach:
- **Traditional:** 3-5 days to set up Ethereum node
- **SimpleInfra:** 5 minutes ⚡

**Web3 infrastructure has never been this simple!** 🌐
