# EDGE Pulse — Deployment Reference

**Last updated:** 2026-06-03  
**AWS account:** 082178185739 (edgelabs)  
**Region:** us-east-1

---

## Live URLs

| Surface | URL |
|---|---|
| **API** | https://pded8nvwwe.us-east-1.awsapprunner.com |
| **API docs** | https://pded8nvwwe.us-east-1.awsapprunner.com/docs |
| **Frontend** | https://d1c4u0c5ny4q1v.cloudfront.net |
| **Health check** | https://pded8nvwwe.us-east-1.awsapprunner.com/health |

---

## Architecture

```
GitHub main branch
       │
       ▼ (push triggers CI/CD)
GitHub Actions (.github/workflows/deploy.yml)
       ├── API: Docker build → ECR → App Runner
       └── Frontend: npm build → S3 → CloudFront invalidation

Internet
   ├── CloudFront (E2LDFUSKDEGPP2) → S3 (pulse-frontend-prod-082178185739)
   │     SPA routing: 403/404 → /index.html 200
   └── App Runner (pulse-api) → Aurora Serverless v2 (pulse-aurora-prod)
```

---

## AWS Resources

### Database (Aurora Serverless v2)
| Resource | Value |
|---|---|
| Cluster | `pulse-aurora-prod` |
| Instance | `pulse-aurora-prod-1` |
| Endpoint | `pulse-aurora-prod.cluster-cysni481z2xp.us-east-1.rds.amazonaws.com:5432` |
| Database | `pulse` |
| User | `pulse_admin` |
| Engine | Aurora PostgreSQL 16.6 |
| Scaling | 0.5–8 ACU (serverless) |
| Security group | `sg-0d80dce17431410e4` (pulse-aurora-sg) |

### API (App Runner)
| Resource | Value |
|---|---|
| Service ARN | `arn:aws:apprunner:us-east-1:082178185739:service/pulse-api/78eda37d5f664abfbf3a502304fd676f` |
| ECR image | `082178185739.dkr.ecr.us-east-1.amazonaws.com/pulse-api:latest` |
| CPU / Memory | 1 vCPU / 2 GB |
| Auto-scaling | min 1, max 3 instances |
| Health check | `GET /health` |

### Frontend (S3 + CloudFront)
| Resource | Value |
|---|---|
| S3 bucket | `pulse-frontend-prod-082178185739` |
| CloudFront distribution | `E2LDFUSKDEGPP2` |
| CloudFront domain | `d1c4u0c5ny4q1v.cloudfront.net` |
| Cache strategy | JS/CSS: immutable 1yr · index.html: no-cache |

---

## CI/CD Pipeline

### How it works

Every push to `main` triggers `.github/workflows/deploy.yml`:

1. **`test-api`** — Python unit tests (`pytest -m "not db and not integration"`)
2. **`build-frontend`** — TypeScript check + Vite build
3. **`build-api`** — Docker build for `linux/amd64`, tag with git SHA + `latest`, push to ECR *(only on main, after tests pass)*
4. **`deploy-api`** — `aws apprunner start-deployment` *(waits for build-api)*
5. **`deploy-frontend`** — `aws s3 sync` + CloudFront invalidation *(waits for deploy-api)*

Pull requests run steps 1–2 only (no deploy).

### GitHub Secrets required

| Secret | Description |
|---|---|
| `AWS_ACCESS_KEY_ID` | IAM user `pulse-github-actions` |
| `AWS_SECRET_ACCESS_KEY` | IAM user `pulse-github-actions` |
| `APPRUNNER_SERVICE_ARN` | App Runner service ARN |
| `CLOUDFRONT_DISTRIBUTION_ID` | `E2LDFUSKDEGPP2` |
| `VITE_API_BASE` | API URL for frontend build |

All secrets are already set on the `edgelabsadmin-glitch/rm` repo.

---

## Manual Operations

### Trigger a deployment without a code push
```bash
# From the repo root
aws apprunner start-deployment \
  --service-arn "arn:aws:apprunner:us-east-1:082178185739:service/pulse-api/78eda37d5f664abfbf3a502304fd676f" \
  --region us-east-1
```

### Run database migrations
```bash
cd 03_build
for f in migrations/*.sql; do
  PGPASSWORD='<password>' psql \
    -h pulse-aurora-prod.cluster-cysni481z2xp.us-east-1.rds.amazonaws.com \
    -U pulse_admin -d pulse -f "$f"
done
```

### Force SF account sync
```bash
cd 03_build
python3 -c "
import asyncio
async def run():
    from core.salesforce.sync import pull_and_upsert
    print(await pull_and_upsert(), 'accounts synced')
asyncio.run(run())
"
```

### Update App Runner environment variable
```bash
aws apprunner update-service \
  --service-arn "arn:aws:apprunner:us-east-1:082178185739:service/pulse-api/78eda37d5f664abfbf3a502304fd676f" \
  --source-configuration '{"ImageRepository":{"ImageIdentifier":"082178185739.dkr.ecr.us-east-1.amazonaws.com/pulse-api:latest","ImageConfiguration":{"Port":"8000","RuntimeEnvironmentVariables":{"KEY":"VALUE"}},"ImageRepositoryType":"ECR"}}'
```

### Lock down Aurora security group (post-production hardening)
Once the API is stable, restrict Aurora's security group to App Runner's egress only:
```bash
# Get App Runner egress CIDR from VPC connector or use service-linked SG
# Then update sg-0d80dce17431410e4 to allow 5432 only from that SG
```

---

## Local Development

```bash
# 1. Backend
cd 03_build
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# 2. Frontend (separate terminal)
cd 03_build/front
npm run dev
# → http://localhost:5173 (proxies /api/* to localhost:8000)
```

`.env` must be at `rm-cloned/.env` (the project root). See `.env` for all required vars.

---

## Google OAuth — production setup

The OAuth client (`338112410567-...`) must have `https://pded8nvwwe.us-east-1.awsapprunner.com/auth/google/callback` added as an **Authorized redirect URI** in Google Cloud Console.

The consent screen must be set to **External** with `afnanhashmi11223344@gmail.com` (and any other users) added as test users until the app is verified.
