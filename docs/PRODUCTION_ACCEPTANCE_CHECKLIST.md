# WeiTesting 生产验收收口清单

更新时间：2026-05-21

## 已完成

- 真实数据试运行看板已上线。
- 已接入真实需求、测试用例、缺陷数据。
- 支持维度切换、柱状图/列表展示、TopN 展示。
- 支持试运行验收结论自动生成。
- 支持验收报告生成、复制、下载。
- 支持验收报告快照归档、历史查看、复制、下载。
- 支持验收汇报稿自动生成、复制、下载。
- 生产服务已部署到 `https://app.evanshine.me` 和 `https://api.evanshine.me`。
- 已补本地一键验证脚本：`scripts/verify-local.ps1`。
- 本地全量后端验证默认跳过真实数据库 E2E，避免缺少本机 PostgreSQL 时误报；需要 E2E 时显式加 `-IncludeE2E`。
- 已补生产公开健康检查脚本：`scripts/check-production.ps1`。
- 已补 PostgreSQL 生产备份脚本：`scripts/backup-production-postgres.sh`。
- 已补 PostgreSQL 备份可读性验证脚本：`scripts/verify-production-backup.sh`。
- 已补 PostgreSQL 备份 systemd timer：`ops/systemd/weitesting-postgres-backup.*`。
- 已补 GitHub Actions CI：`.github/workflows/ci.yml`。
- GitHub Actions 后端作业已包含 PostgreSQL 服务，并运行真实数据库 E2E。
- Oracle 生产服务器已启用 `weitesting-postgres-backup.timer`，首次备份成功生成在 `/opt/weitesting/backups/postgres/`。
- 默认关闭开发用身份头旁路，`X-User-Id` / `X-Tenant-Id` 只有显式开启 `AUTH_HEADER_IMPERSONATION_ENABLED=true` 时可用。

## 交付前必须确认

- 业务方确认当前 P0 缺陷处理状态。
- 如果 P0 缺陷已修复或降级，在平台更新缺陷状态后重新生成验收报告快照。
- 重新生成“验收汇报稿”，以最新快照作为最终验收附件。
- 泄露过或临时使用过的外部 Token 完成轮换。
- Jira / 禅道 / Jenkins / 钉钉至少各跑一次真实闭环，并保留记录。
- Jenkins 生产入口完成域名、HTTPS、访问控制和备份。
- 数据库备份需要定期抽查恢复演练，至少执行一次 `scripts/verify-production-backup.sh` 并保存记录。

## 本地验收命令

```powershell
.\scripts\verify-local.ps1
```

完整后端测试：

```powershell
.\scripts\verify-local.ps1 -FullBackend
```

包含真实数据库后端 E2E 和前端 E2E：

```powershell
.\scripts\verify-local.ps1 -IncludeE2E
```

`-IncludeE2E` 前需本机 PostgreSQL 可连接，默认测试库连接串为：

```text
postgresql+asyncpg://postgres:123456@localhost:5432/ai_test_e2e
```

## 生产公开检查

```powershell
.\scripts\check-production.ps1
```

## 数据库备份

服务器上执行：

```bash
sudo install -m 0755 scripts/backup-production-postgres.sh /usr/local/bin/weitesting-backup-postgres
sudo BACKUP_DIR=/opt/weitesting/backups/postgres /usr/local/bin/weitesting-backup-postgres
```

已提供 systemd timer，默认每天 UTC 02:15 执行：

```bash
sudo systemctl status weitesting-postgres-backup.timer
sudo systemctl list-timers --all | grep weitesting-postgres-backup
```

备份可读性验证：

```bash
sudo /usr/local/bin/weitesting-verify-backup
```

指定备份文件验证：

```bash
sudo /usr/local/bin/weitesting-verify-backup /opt/weitesting/backups/postgres/weitesting-YYYYMMDDTHHMMSSZ.dump.gz
```

如果不用 systemd timer，也可以改用 crontab：

```cron
15 2 * * * BACKUP_DIR=/opt/weitesting/backups/postgres RETENTION_DAYS=14 /usr/local/bin/weitesting-backup-postgres >> /var/log/weitesting-backup.log 2>&1
```

## 当前验收口径

当前平台自动评估结论是“建议暂缓”，原因是数据中仍存在 P0 缺陷和风险提示。平台能力已具备交付演示条件，但最终业务验收应以 P0 缺陷闭环后的新快照为准。
