# Terraform + AWS CLAUDE.md Template

<!-- ABOUT THIS TEMPLATE
  - ~90 lines of content (~640 tokens)
  - Optimized for Terraform + AWS infrastructure projects
  - Covers: terraform commands, module patterns, state, naming, security
  - Copy everything below the "---" line into your project's CLAUDE.md
  - Replace all {PLACEHOLDER} values with your project specifics
  - Delete comment blocks before use to save tokens
-->

---

<!-- COPY BELOW THIS LINE INTO YOUR PROJECT'S CLAUDE.md -->

# {Project Name} — Infrastructure

{One-sentence description. Example: "AWS infrastructure for the Acme SaaS platform."}
IaC: Terraform {1.6+} | Cloud: AWS ({us-east-1})
State backend: {S3 + DynamoDB locking}
Environments: {dev, staging, prod}

## Commands

```bash
# Init and plan (always specify environment)
terraform -chdir=envs/{dev} init
terraform -chdir=envs/{dev} plan -out=plan.tfplan
terraform -chdir=envs/{dev} apply plan.tfplan

# Targeted operations (use sparingly)
terraform plan -target=module.{name}
terraform apply -target=module.{name}

# State inspection
terraform state list
terraform state show module.{name}.aws_instance.{resource}

# Formatting and validation
terraform fmt -recursive
terraform validate
{tflint --recursive}               # Linting

# Cost estimation (optional)
{infracost breakdown --path envs/dev}
```

## Project Structure

```
modules/                            # Reusable Terraform modules
├── networking/                     # VPC, subnets, NAT, security groups
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── README.md
├── compute/                        # EC2, ASG, Launch Templates
├── database/                       # RDS, ElastiCache, DynamoDB
├── storage/                        # S3, EFS
├── iam/                            # IAM roles, policies, instance profiles
└── monitoring/                     # CloudWatch, SNS, alarms
envs/                               # Environment-specific configurations
├── dev/
│   ├── main.tf                     # Module calls with dev values
│   ├── variables.tf                # Variable declarations
│   ├── terraform.tfvars            # Dev-specific values
│   ├── backend.tf                  # S3 backend config for dev
│   └── outputs.tf
├── staging/
└── prod/
```

## Module Patterns

- Every module has: `main.tf`, `variables.tf`, `outputs.tf`
- All variables must have `description` and `type`
- Sensitive variables: mark with `sensitive = true`
- Use `locals` for computed values and repeated expressions
- Module sources: relative paths for local (`../../modules/networking`)
- Pin module versions if using registry: `version = "~> 3.0"`

```hcl
# Standard module call pattern
module "vpc" {
  source = "../../modules/networking"

  environment    = var.environment
  project_name   = var.project_name
  vpc_cidr       = var.vpc_cidr
  azs            = ["us-east-1a", "us-east-1b"]

  tags = local.common_tags
}
```

## State Management

- Backend: S3 bucket with versioning + DynamoDB table for locking
- One state file per environment (dev/staging/prod are isolated)
- Never run `terraform state` write commands without team approval
- Use `terraform import` to bring existing resources under management
- State is source of truth — never modify AWS resources manually in console

## Naming Conventions

- Resources: `{project}-{environment}-{component}-{resource}`
  - Example: `acme-prod-api-alb`, `acme-dev-db-primary`
- Terraform names: `snake_case` for resources, variables, outputs
- Tags (required on all resources):
  - `Project`, `Environment`, `ManagedBy = "terraform"`, `Owner`
- Variables: descriptive names, no abbreviations (`database_instance_class` not `db_cls`)

## Security Rules

- **No hardcoded secrets** — use AWS Secrets Manager or SSM Parameter Store
- **No inline IAM policies** — use `aws_iam_policy` resources with JSON documents
- **Least privilege** — IAM policies grant minimum required permissions
- **No public S3 buckets** unless explicitly justified and documented
- **Encryption at rest** on all storage: S3, RDS, EBS, EFS
- **Security groups**: deny all by default, allow specific CIDRs and ports only
- **No `0.0.0.0/0` ingress** on SSH/RDP — use bastion or SSM Session Manager
- All RDS instances: `publicly_accessible = false`, inside private subnets

## Common Patterns

- Data lookups: use `data` sources for AMIs, AZs, account ID — do not hardcode
- Conditional resources: `count = var.enable_feature ? 1 : 0`
- Multiple instances: `for_each` with maps for named resources
- Dependencies: use `depends_on` only when implicit deps are insufficient
- Outputs: expose only what consuming modules need (IDs, ARNs, endpoints)

## Do Not

- Do not `apply` without reviewing `plan` output first
- Do not modify `.terraform.lock.hcl` manually — run `terraform init -upgrade`
- Do not store `*.tfvars` with secrets in git — use env vars or secrets manager
- Do not edit state files manually — use `terraform state mv/rm` commands
- Do not create resources outside of Terraform for managed infrastructure
- Do not run `terraform destroy` on staging/prod without explicit approval

<!-- END OF TEMPLATE
  Content: ~90 lines (~640 tokens)
  Overhead per 30-turn session: ~19,200 tokens (pre-cache)
  Optimized for: safe infra operations, consistent module structure, security -->
