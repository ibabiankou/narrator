# Graceful shutdown of the cluster

## 1. Cordon all nodes
```bash 
kubectl cordon $(kubectl get nodes -o name)
```

## 2. Drain all nodes in reversed order. If PDB prevents draining.
### Important: add --disable-eviction flag to ignore PDBs.
```bash
kubectl drain nask3s --ignore-daemonsets --delete-emptydir-data
kubectl drain node14 --ignore-daemonsets --delete-emptydir-data
kubectl drain node13 --ignore-daemonsets --delete-emptydir-data
kubectl drain node12 --ignore-daemonsets --delete-emptydir-data
kubectl drain node11 --ignore-daemonsets --delete-emptydir-data
```

## 3. Startup plan:
1. Start all nodes
2. Uncordon worker nodes (can even do simultaneously)
3. Uncordon master node.

## Side effects of shutting down the cluster:
- DNS will be down. No domain name resolution.
- LDAP does not seem to have persistent storage. So all LDAP entries have to be re-created.
